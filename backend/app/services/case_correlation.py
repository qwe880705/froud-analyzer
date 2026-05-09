import json
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.case import AnalystNote, Case, CaseEvent
from app.models.event import RawEvent
from app.models.user import User
from app.services.risk_scoring import ScoringResult


class CaseCorrelationService:

    def __init__(self, db: Session):
        self.db = db

    def create_alert_from_score(self, result: ScoringResult) -> Optional[Alert]:
        user = self.db.query(User).filter(User.id == result.user_id).first()
        if not user:
            return None

        existing = self.db.query(Alert).filter(
            Alert.user_id == result.user_id,
            Alert.status.in_(["new", "reviewing"]),
        ).first()
        if existing:
            existing.risk_score = result.total_score
            existing.severity = result.severity
            self.db.commit()
            return None

        triggered_summary = ", ".join(result.triggered_rules[:5])
        alert = Alert(
            id=str(uuid.uuid4()),
            user_id=result.user_id,
            alert_type="risk_score_threshold",
            title=f"Risk threshold exceeded: {user.display_name}",
            description=f"Score: {result.total_score}/100. Rules triggered: {triggered_summary}",
            risk_score=result.total_score,
            severity=result.severity,
            status="new",
            alert_timestamp=datetime.utcnow(),
        )
        self.db.add(alert)
        self.db.commit()
        return alert

    def auto_create_case(self, result: ScoringResult) -> Optional[Case]:
        user = self.db.query(User).filter(User.id == result.user_id).first()
        if not user:
            return None

        existing = self.db.query(Case).filter(
            Case.subject_user_id == result.user_id,
            Case.status.notin_(["closed_confirmed", "closed_cleared", "closed_inconclusive"]),
        ).first()
        if existing:
            existing.risk_score = max(existing.risk_score, result.total_score)
            existing.severity = result.severity
            existing.updated_at = datetime.utcnow()
            self.db.commit()
            return None

        case_number = self._next_case_number()
        indicators = self._build_indicators(result, user)

        recent_events = self.db.query(RawEvent).filter(
            RawEvent.user_id == result.user_id,
            RawEvent.event_timestamp >= result.event_window_start,
        ).order_by(RawEvent.event_timestamp).all()

        case = Case(
            id=str(uuid.uuid4()),
            case_number=case_number,
            title=f"Insider Risk Investigation: {user.display_name}",
            subject_user_id=result.user_id,
            case_type=self._infer_case_type(result),
            severity=result.severity,
            risk_score=result.total_score,
            status="open",
            case_period_start=result.event_window_start,
            case_period_end=result.event_window_end,
            auto_created=True,
            auto_create_reason=f"Risk score {result.total_score} exceeded threshold. Rules: {', '.join(result.triggered_rules[:3])}",
            key_indicators=json.dumps(indicators),
        )
        self.db.add(case)
        self.db.flush()

        for ev in recent_events[:50]:
            ce = CaseEvent(
                id=str(uuid.uuid4()),
                case_id=case.id,
                raw_event_id=ev.id,
                relevance="supporting",
                added_by="system",
            )
            self.db.add(ce)

        # Link alert if exists
        alert = self.db.query(Alert).filter(
            Alert.user_id == result.user_id,
            Alert.status.in_(["new", "reviewing"]),
        ).first()
        if alert:
            alert.case_id = case.id
            alert.status = "escalated"

        self.db.commit()
        return case

    def create_case_from_alert(
        self,
        alert: Alert,
        analyst: str,
        title_override: Optional[str] = None,
        initial_note: Optional[str] = None,
    ) -> Case:
        user = self.db.query(User).filter(User.id == alert.user_id).first()
        case_number = self._next_case_number()

        case = Case(
            id=str(uuid.uuid4()),
            case_number=case_number,
            title=title_override or f"Investigation: {alert.title}",
            subject_user_id=alert.user_id,
            case_type="alert_escalation",
            severity=alert.severity,
            risk_score=alert.risk_score,
            status="open",
            assigned_to=analyst,
            assigned_at=datetime.utcnow(),
            auto_created=False,
            key_indicators=json.dumps([alert.title]),
        )
        self.db.add(case)
        self.db.flush()

        alert.case_id = case.id
        alert.status = "escalated"

        if initial_note:
            note = AnalystNote(
                id=str(uuid.uuid4()),
                case_id=case.id,
                note_type="general",
                content=initial_note,
                created_by=analyst,
            )
            self.db.add(note)

        self.db.commit()
        return case

    def create_case_manual(self, body) -> Case:
        case_number = self._next_case_number()
        case = Case(
            id=str(uuid.uuid4()),
            case_number=case_number,
            title=body.title,
            subject_user_id=body.subject_user_id,
            case_type=body.case_type,
            severity=body.severity,
            risk_score=0,
            status="open",
            assigned_to=body.analyst,
            assigned_at=datetime.utcnow(),
            auto_created=False,
            key_indicators=json.dumps([]),
        )
        self.db.add(case)
        self.db.commit()
        return case

    def _next_case_number(self) -> str:
        year = datetime.utcnow().year
        count = self.db.query(Case).count() + 1
        return f"CASE-{year}-{count:04d}"

    def _infer_case_type(self, result: ScoringResult) -> str:
        rules = set(result.triggered_rules)
        if rules & {"R01", "R02", "R03", "R05"}:
            return "data_exfiltration"
        if rules & {"R09", "R11", "R12"}:
            return "access_anomaly"
        if rules & {"R19", "R20", "R21"}:
            return "hr_risk"
        return "anomaly"

    def _build_indicators(self, result: ScoringResult, user: User) -> list[str]:
        indicators = []
        rules = set(result.triggered_rules)
        if "R19" in rules or "R20" in rules:
            indicators.append(f"Pending resignation (last day: {user.termination_date})")
        if "R21" in rules:
            indicators.append("Employee on Performance Improvement Plan")
        if "R01" in rules or "R02" in rules:
            indicators.append("Uploads to personal cloud storage detected")
        if "R03" in rules:
            indicators.append("USB transfer of sensitive files attempted")
        if "R05" in rules:
            indicators.append("Sensitive files emailed to personal address")
        if "R09" in rules:
            indicators.append("After-hours system access")
        if "R11" in rules:
            indicators.append("Multiple failed login attempts followed by success")
        return indicators[:6]
