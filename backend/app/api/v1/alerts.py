from datetime import datetime
from typing import Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.config import settings
from app.models.alert import Alert
from app.models.user import User
from app.schemas.common import PaginatedResponse, StandardResponse
from app.middleware.audit import write_audit_log

router = APIRouter(prefix="/alerts", tags=["Alerts"])


class AlertItem(BaseModel):
    id: str
    user_email: str
    user_display_name: str
    department: Optional[str]
    alert_type: str
    title: str
    description: Optional[str]
    severity: str
    risk_score: float
    status: str
    alert_timestamp: datetime
    detected_at: datetime
    case_id: Optional[str]
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]
    dismiss_reason: Optional[str]


class UpdateStatusRequest(BaseModel):
    status: Literal["reviewing", "dismissed", "escalated"]
    dismiss_reason: Optional[str] = None
    analyst: str = settings.DEFAULT_ANALYST


class EscalateRequest(BaseModel):
    analyst: str = settings.DEFAULT_ANALYST
    case_title: Optional[str] = None
    notes: Optional[str] = None


def _alert_to_item(alert: Alert, db: Session) -> AlertItem:
    user = db.query(User).filter(User.id == alert.user_id).first()
    return AlertItem(
        id=alert.id, alert_type=alert.alert_type, title=alert.title,
        description=alert.description, severity=alert.severity,
        risk_score=alert.risk_score, status=alert.status,
        alert_timestamp=alert.alert_timestamp, detected_at=alert.detected_at,
        case_id=alert.case_id, reviewed_by=alert.reviewed_by,
        reviewed_at=alert.reviewed_at, dismiss_reason=alert.dismiss_reason,
        user_email=user.email if user else "",
        user_display_name=user.display_name if user else "",
        department=user.department if user else None,
    )


@router.get("", response_model=PaginatedResponse[AlertItem])
def list_alerts(
    page: int = 1, page_size: int = 25,
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Alert).join(User, Alert.user_id == User.id)
    if status:     q = q.filter(Alert.status == status)
    if severity:   q = q.filter(Alert.severity == severity)
    if user_id:    q = q.filter(Alert.user_id == user_id)
    if department: q = q.filter(User.department == department)
    total = q.count()
    items = q.order_by(Alert.detected_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    return PaginatedResponse(
        items=[_alert_to_item(a, db) for a in items],
        total=total, page=page, page_size=page_size,
        has_next=total > page * page_size,
    )


@router.get("/{alert_id}", response_model=StandardResponse[AlertItem])
def get_alert(
    alert_id: str,
    analyst: str = settings.DEFAULT_ANALYST,
    db: Session = Depends(get_db),
):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(404, "Alert not found")
    write_audit_log(db, actor=analyst, action="alert.view",
                    resource_type="alert", resource_id=alert_id)
    return StandardResponse(success=True, data=_alert_to_item(alert, db))


@router.patch("/{alert_id}/status", response_model=StandardResponse[AlertItem])
def update_status(
    alert_id: str,
    body: UpdateStatusRequest,
    db: Session = Depends(get_db),
):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(404, "Alert not found")
    old = alert.status
    alert.status = body.status
    alert.reviewed_by = body.analyst
    alert.reviewed_at = datetime.utcnow()
    if body.dismiss_reason:
        alert.dismiss_reason = body.dismiss_reason
    db.commit()
    write_audit_log(db, actor=body.analyst, action="alert.status.change",
                    resource_type="alert", resource_id=alert_id,
                    details={"from": old, "to": body.status})
    return StandardResponse(success=True, data=_alert_to_item(alert, db))


@router.post("/{alert_id}/escalate", response_model=StandardResponse[dict])
def escalate(
    alert_id: str,
    body: EscalateRequest,
    db: Session = Depends(get_db),
):
    from app.services.case_correlation import CaseCorrelationService
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(404, "Alert not found")
    if alert.status == "escalated":
        raise HTTPException(409, "Already escalated")
    service = CaseCorrelationService(db)
    case = service.create_case_from_alert(
        alert=alert, analyst=body.analyst,
        title_override=body.case_title, initial_note=body.notes,
    )
    write_audit_log(db, actor=body.analyst, action="case.create",
                    resource_type="case", resource_id=case.id,
                    details={"source_alert_id": alert_id})
    return StandardResponse(
        success=True,
        data={"case_id": case.id, "case_number": case.case_number},
        message=f"Escalated to {case.case_number}",
    )
