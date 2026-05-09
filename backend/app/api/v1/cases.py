import json
import uuid
from datetime import datetime
from typing import Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.config import settings
from app.models.case import Case, CaseEvent, AnalystNote
from app.models.user import User
from app.models.event import RawEvent
from app.schemas.common import PaginatedResponse, StandardResponse
from app.middleware.audit import write_audit_log

router = APIRouter(prefix="/cases", tags=["Cases"])


class CaseItem(BaseModel):
    id: str
    case_number: str
    title: str
    subject_user_email: str
    subject_user_name: str
    department: Optional[str]
    severity: str
    risk_score: float
    status: str
    assigned_to: Optional[str]
    case_type: str
    key_indicators: list[str]
    auto_created: bool
    event_count: int
    note_count: int
    case_period_start: Optional[datetime]
    case_period_end: Optional[datetime]
    created_at: datetime


class TimelineItem(BaseModel):
    event_id: str
    event_timestamp: datetime
    event_category: str
    event_type: str
    source: str
    summary: str
    severity_original: Optional[str]
    relevance: str
    object_name: Optional[str]
    destination_detail: Optional[str]
    action_result: Optional[str]


class NoteItem(BaseModel):
    id: str
    note_type: str
    content: str
    created_by: str
    created_at: datetime
    is_confidential: bool


class CreateCaseRequest(BaseModel):
    title: str
    subject_user_id: str
    case_type: str = "anomaly"
    severity: str = "medium"
    analyst: str = settings.DEFAULT_ANALYST


class UpdateStatusRequest(BaseModel):
    status: str
    analyst: str = settings.DEFAULT_ANALYST
    reason: Optional[str] = None


class AddEventRequest(BaseModel):
    raw_event_id: str
    relevance: Literal["primary", "supporting", "contextual", "exculpatory"] = "supporting"
    notes: Optional[str] = None
    analyst: str = settings.DEFAULT_ANALYST


class AddNoteRequest(BaseModel):
    content: str
    note_type: str = "general"
    is_confidential: bool = False
    analyst: str = settings.DEFAULT_ANALYST


VALID_TRANSITIONS = {
    "open":           ["investigating", "closed_cleared"],
    "investigating":  ["pending_review", "escalated", "closed_confirmed", "closed_cleared", "closed_inconclusive"],
    "pending_review": ["investigating", "escalated", "closed_confirmed", "closed_cleared", "closed_inconclusive"],
    "escalated":      ["closed_confirmed", "closed_inconclusive"],
}


def _to_item(case: Case, db: Session) -> CaseItem:
    user = db.query(User).filter(User.id == case.subject_user_id).first()
    ev_count = db.query(CaseEvent).filter(CaseEvent.case_id == case.id).count()
    nt_count = db.query(AnalystNote).filter(AnalystNote.case_id == case.id).count()
    indicators = json.loads(case.key_indicators) if case.key_indicators else []
    return CaseItem(
        id=case.id, case_number=case.case_number, title=case.title,
        subject_user_email=user.email if user else "",
        subject_user_name=user.display_name if user else "",
        department=user.department if user else None,
        severity=case.severity, risk_score=case.risk_score,
        status=case.status, assigned_to=case.assigned_to,
        case_type=case.case_type, key_indicators=indicators,
        auto_created=case.auto_created, event_count=ev_count,
        note_count=nt_count,
        case_period_start=case.case_period_start,
        case_period_end=case.case_period_end,
        created_at=case.created_at,
    )


@router.get("", response_model=PaginatedResponse[CaseItem])
def list_cases(
    page: int = 1, page_size: int = 20,
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Case).join(User, Case.subject_user_id == User.id)
    if status:     q = q.filter(Case.status == status)
    if severity:   q = q.filter(Case.severity == severity)
    if department: q = q.filter(User.department == department)
    total = q.count()
    items = q.order_by(Case.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    return PaginatedResponse(
        items=[_to_item(c, db) for c in items],
        total=total, page=page, page_size=page_size,
        has_next=total > page * page_size,
    )


@router.post("", response_model=StandardResponse[CaseItem])
def create_case(body: CreateCaseRequest, db: Session = Depends(get_db)):
    from app.services.case_correlation import CaseCorrelationService
    svc = CaseCorrelationService(db)
    case = svc.create_case_manual(body)
    write_audit_log(db, actor=body.analyst, action="case.create",
                    resource_type="case", resource_id=case.id)
    return StandardResponse(success=True, data=_to_item(case, db))


@router.get("/{case_id}", response_model=StandardResponse[CaseItem])
def get_case(
    case_id: str,
    analyst: str = settings.DEFAULT_ANALYST,
    db: Session = Depends(get_db),
):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    write_audit_log(db, actor=analyst, action="case.view",
                    resource_type="case", resource_id=case_id)
    return StandardResponse(success=True, data=_to_item(case, db))


@router.patch("/{case_id}/status", response_model=StandardResponse[dict])
def update_status(
    case_id: str, body: UpdateStatusRequest, db: Session = Depends(get_db)
):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    allowed = VALID_TRANSITIONS.get(case.status, [])
    if body.status not in allowed:
        raise HTTPException(400, f"Cannot transition '{case.status}' → '{body.status}'. Allowed: {allowed}")
    old = case.status
    case.status = body.status
    case.updated_at = datetime.utcnow()
    if body.status.startswith("closed"):
        case.closed_at = datetime.utcnow()
        case.closed_by = body.analyst
    db.commit()
    write_audit_log(db, actor=body.analyst, action="case.status.change",
                    resource_type="case", resource_id=case_id,
                    details={"from": old, "to": body.status})
    return StandardResponse(success=True, message=f"Status → {body.status}")


@router.post("/{case_id}/events", response_model=StandardResponse[dict])
def add_event(
    case_id: str, body: AddEventRequest, db: Session = Depends(get_db)
):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    event = db.query(RawEvent).filter(RawEvent.id == body.raw_event_id).first()
    if not event:
        raise HTTPException(404, "Event not found")
    exists = db.query(CaseEvent).filter(
        CaseEvent.case_id == case_id,
        CaseEvent.raw_event_id == body.raw_event_id,
    ).first()
    if exists:
        raise HTTPException(409, "Event already linked")
    ce = CaseEvent(
        id=str(uuid.uuid4()), case_id=case_id,
        raw_event_id=body.raw_event_id, relevance=body.relevance,
        added_by=body.analyst, notes=body.notes,
    )
    db.add(ce)
    case.updated_at = datetime.utcnow()
    db.commit()
    write_audit_log(db, actor=body.analyst, action="case.event.add",
                    resource_type="case", resource_id=case_id,
                    details={"event_id": body.raw_event_id})
    return StandardResponse(success=True, message="Event linked")


@router.post("/{case_id}/notes", response_model=StandardResponse[dict])
def add_note(
    case_id: str, body: AddNoteRequest, db: Session = Depends(get_db)
):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    note = AnalystNote(
        id=str(uuid.uuid4()), case_id=case_id,
        note_type=body.note_type, content=body.content,
        created_by=body.analyst, is_confidential=body.is_confidential,
    )
    db.add(note)
    db.commit()
    write_audit_log(db, actor=body.analyst, action="note.create",
                    resource_type="case", resource_id=case_id)
    return StandardResponse(success=True, message="Note added")


@router.get("/{case_id}/notes", response_model=StandardResponse[list[NoteItem]])
def get_notes(case_id: str, db: Session = Depends(get_db)):
    notes = db.query(AnalystNote).filter(
        AnalystNote.case_id == case_id
    ).order_by(AnalystNote.created_at.asc()).all()
    return StandardResponse(success=True, data=[
        NoteItem(id=n.id, note_type=n.note_type, content=n.content,
                 created_by=n.created_by, created_at=n.created_at,
                 is_confidential=n.is_confidential)
        for n in notes
    ])


@router.get("/{case_id}/timeline", response_model=StandardResponse[list[TimelineItem]])
def get_timeline(
    case_id: str,
    analyst: str = settings.DEFAULT_ANALYST,
    db: Session = Depends(get_db),
):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    ces = db.query(CaseEvent).filter(CaseEvent.case_id == case_id).all()
    rel_map = {ce.raw_event_id: ce.relevance for ce in ces}
    events = db.query(RawEvent).filter(
        RawEvent.id.in_(list(rel_map.keys()))
    ).order_by(RawEvent.event_timestamp).all()

    def summary(e: RawEvent) -> str:
        m = {
            "cloud_upload":  f"Uploaded '{e.object_name}' to {e.destination_detail}",
            "usb_transfer":  f"Copied {e.object_count or 1} file(s) to USB ({e.destination_detail})",
            "email_send":    f"Email sent to {e.destination_detail}: {e.object_name}",
            "email_forward": f"Email forwarded to {e.destination_detail}: {e.object_name}",
            "login":         f"Login from {e.location_city} — {e.action_result}",
            "file_download": f"Downloaded '{e.object_name}'",
            "web_browsing":  f"Visited {e.destination_detail}",
            "data_exfiltration": f"Exfiltration alert: {e.object_name}",
        }
        return m.get(e.event_category, f"{e.event_type}: {e.object_name or e.destination_detail or ''}")

    return StandardResponse(success=True, data=[
        TimelineItem(
            event_id=e.id,
            event_timestamp=e.event_timestamp,
            event_category=e.event_category,
            event_type=e.event_type,
            source=e.data_source_type,
            summary=summary(e),
            severity_original=e.severity_original,
            relevance=rel_map.get(e.id, "supporting"),
            object_name=e.object_name,
            destination_detail=e.destination_detail,
            action_result=e.action_result,
        )
        for e in events
    ])
