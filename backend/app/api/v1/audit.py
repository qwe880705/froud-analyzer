from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.audit import AuditLog
from app.schemas.common import PaginatedResponse, StandardResponse

router = APIRouter(prefix="/audit", tags=["Audit"])


class AuditItem(dict):
    pass


@router.get("/logs", response_model=PaginatedResponse[dict])
def list_logs(
    page: int = 1, page_size: int = 50,
    actor: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(AuditLog)
    if actor:         q = q.filter(AuditLog.actor == actor)
    if action:        q = q.filter(AuditLog.action == action)
    if resource_type: q = q.filter(AuditLog.resource_type == resource_type)
    total = q.count()
    items = q.order_by(AuditLog.occurred_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    return PaginatedResponse(
        items=[{
            "id": l.id, "actor": l.actor, "action": l.action,
            "resource_type": l.resource_type, "resource_id": l.resource_id,
            "occurred_at": l.occurred_at.isoformat(),
            "details": l.details,
        } for l in items],
        total=total, page=page, page_size=page_size,
        has_next=total > page * page_size,
    )


@router.get("/verify", response_model=StandardResponse[dict])
def verify_chain(db: Session = Depends(get_db)):
    import hashlib
    logs = db.query(AuditLog).order_by(AuditLog.sequence_num).all()
    broken = []
    prev_hash = "GENESIS"
    for log in logs:
        if log.prev_hash != prev_hash:
            broken.append({"id": log.id, "sequence": log.sequence_num})
        prev_hash = log.entry_hash
    return StandardResponse(success=True, data={
        "total_entries": len(logs),
        "chain_intact": len(broken) == 0,
        "broken_entries": broken,
    })
