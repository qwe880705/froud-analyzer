from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from app.core.database import Base


class Case(Base):
    __tablename__ = "cases"

    id = Column(String, primary_key=True)
    case_number = Column(String, nullable=False, unique=True)
    title = Column(String, nullable=False)
    subject_user_id = Column(String, nullable=False)
    case_type = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    risk_score = Column(Float, nullable=False, default=0)
    status = Column(String, nullable=False, default="open")
    case_period_start = Column(DateTime)
    case_period_end = Column(DateTime)
    assigned_to = Column(String)
    assigned_at = Column(DateTime)
    auto_created = Column(Boolean, default=False)
    auto_create_reason = Column(Text)
    key_indicators = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime)
    closed_by = Column(String)


class CaseEvent(Base):
    __tablename__ = "case_events"

    id = Column(String, primary_key=True)
    case_id = Column(String, nullable=False)
    raw_event_id = Column(String, nullable=False)
    relevance = Column(String, default="supporting")
    added_by = Column(String, nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)


class AnalystNote(Base):
    __tablename__ = "analyst_notes"

    id = Column(String, primary_key=True)
    case_id = Column(String)
    alert_id = Column(String)
    user_id = Column(String)
    note_type = Column(String, default="general")
    content = Column(Text, nullable=False)
    referenced_event_ids = Column(Text)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_confidential = Column(Boolean, default=False)


class RiskScore(Base):
    __tablename__ = "risk_scores"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    total_score = Column(Float, nullable=False)
    severity = Column(String, nullable=False)
    score_data_exfil = Column(Float, default=0)
    score_access_anomaly = Column(Float, default=0)
    score_behavior_dev = Column(Float, default=0)
    score_hr_context = Column(Float, default=0)
    score_temporal = Column(Float, default=0)
    score_breakdown = Column(Text)
    triggered_rules = Column(Text)
    event_window_start = Column(DateTime)
    event_window_end = Column(DateTime)
    event_count = Column(Integer)
    calculated_at = Column(DateTime, default=datetime.utcnow)
    calculated_by = Column(String, default="system")
    calculation_version = Column(String, default="1.0")
    case_id = Column(String)


class ReportDraft(Base):
    __tablename__ = "report_drafts"

    id = Column(String, primary_key=True)
    case_id = Column(String, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    initial_assessment = Column(Text)
    key_indicators = Column(Text)
    risk_analysis = Column(Text)
    evidence_summary = Column(Text)
    recommended_actions = Column(Text)
    final_summary = Column(Text)
    status = Column(String, nullable=False, default="draft")
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    submitted_for_review_at = Column(DateTime)
    reviewed_by = Column(String)
    reviewed_at = Column(DateTime)
    review_comments = Column(Text)
    approved_by = Column(String)
    approved_at = Column(DateTime)
    exported_at = Column(DateTime)
    export_format = Column(String)
