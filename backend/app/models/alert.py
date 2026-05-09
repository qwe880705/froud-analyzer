from datetime import datetime
from sqlalchemy import Column, DateTime, Float, String, Text
from app.core.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    trigger_event_id = Column(String)
    alert_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    risk_score = Column(Float, nullable=False, default=0)
    severity = Column(String, nullable=False)
    status = Column(String, nullable=False, default="new")
    case_id = Column(String)
    alert_timestamp = Column(DateTime, nullable=False)
    detected_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime)
    reviewed_by = Column(String)
    dismiss_reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
