from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Text
from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(String, primary_key=True)
    sequence_num = Column(Integer, autoincrement=True)
    actor = Column(String, nullable=False)
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    resource_id = Column(String)
    details = Column(Text)
    ip_address = Column(String)
    user_agent = Column(String)
    occurred_at = Column(DateTime, default=datetime.utcnow)
    prev_hash = Column(String)
    entry_hash = Column(String, nullable=False)
