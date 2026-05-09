import hashlib
import json
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.models.audit import AuditLog


def write_audit_log(
    db: Session,
    actor: str,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    last = db.query(AuditLog).order_by(AuditLog.sequence_num.desc()).first()
    prev_hash = last.entry_hash if last else "GENESIS"

    now = datetime.utcnow().isoformat()
    payload = f"{actor}|{action}|{resource_type}|{resource_id}|{now}|{prev_hash}"
    entry_hash = hashlib.sha256(payload.encode()).hexdigest()

    log = AuditLog(
        id=str(uuid.uuid4()),
        actor=actor,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=json.dumps(details) if details else None,
        ip_address=ip_address,
        occurred_at=datetime.utcnow(),
        prev_hash=prev_hash,
        entry_hash=entry_hash,
    )
    db.add(log)
    db.commit()
    return log
