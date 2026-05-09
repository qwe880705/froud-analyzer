from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import date, datetime

from app.core.database import get_db
from app.core.config import settings
from app.models.user import User
from app.models.event import RawEvent
from app.models.case import Case
from app.schemas.common import PaginatedResponse, StandardResponse
from app.middleware.audit import write_audit_log

router = APIRouter(prefix="/users", tags=["Users"])


class UserItem(BaseModel):
    id: str
    employee_id: str
    display_name: str
    email: str
    department: Optional[str]
    job_title: Optional[str]
    location: Optional[str]
    employment_status: str
    hire_date: Optional[date]
    termination_date: Optional[date]
    is_on_pip: bool
    is_pending_resign: bool
    is_pending_transfer: bool
    hr_risk_flag: Optional[str]

    class Config:
        from_attributes = True


@router.get("", response_model=PaginatedResponse[UserItem])
def list_users(
    page: int = 1, page_size: int = 25,
    department: Optional[str] = Query(None),
    employment_status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(User)
    if department:        q = q.filter(User.department == department)
    if employment_status: q = q.filter(User.employment_status == employment_status)
    total = q.count()
    items = q.order_by(User.display_name).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    return PaginatedResponse(
        items=items, total=total, page=page, page_size=page_size,
        has_next=total > page * page_size,
    )


@router.get("/{user_id}", response_model=StandardResponse[UserItem])
def get_user(
    user_id: str,
    analyst: str = settings.DEFAULT_ANALYST,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(
        (User.id == user_id) | (User.email == user_id)
    ).first()
    if not user:
        raise HTTPException(404, "User not found")
    write_audit_log(db, actor=analyst, action="user.profile.view",
                    resource_type="user", resource_id=user.id)
    return StandardResponse(success=True, data=user)


@router.get("/{user_id}/cases", response_model=StandardResponse[list[dict]])
def get_user_cases(user_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        (User.id == user_id) | (User.email == user_id)
    ).first()
    if not user:
        raise HTTPException(404, "User not found")
    cases = db.query(Case).filter(
        Case.subject_user_id == user.id
    ).order_by(Case.created_at.desc()).all()
    return StandardResponse(success=True, data=[{
        "id": c.id, "case_number": c.case_number, "title": c.title,
        "severity": c.severity, "status": c.status,
        "risk_score": c.risk_score, "created_at": c.created_at.isoformat(),
    } for c in cases])


@router.get("/{user_id}/events", response_model=StandardResponse[list[dict]])
def get_user_events(
    user_id: str,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(
        (User.id == user_id) | (User.email == user_id)
    ).first()
    if not user:
        raise HTTPException(404, "User not found")
    events = db.query(RawEvent).filter(
        RawEvent.user_id == user.id
    ).order_by(RawEvent.event_timestamp.desc()).limit(limit).all()
    return StandardResponse(success=True, data=[{
        "id": e.id, "event_category": e.event_category,
        "event_type": e.event_type, "event_timestamp": e.event_timestamp.isoformat(),
        "source": e.data_source_type, "action_result": e.action_result,
        "object_name": e.object_name, "destination_detail": e.destination_detail,
        "severity_original": e.severity_original,
    } for e in events])
