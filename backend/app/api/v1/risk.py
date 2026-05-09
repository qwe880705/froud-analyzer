from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.config import settings
from app.services.risk_scoring import RiskScoringEngine
from app.models.case import RiskScore
from app.models.user import User
from app.models.alert import Alert
from app.models.event import RawEvent
from app.models.case import Case
from app.schemas.common import StandardResponse
from app.middleware.audit import write_audit_log

router = APIRouter(prefix="/risk", tags=["Risk"])


@router.post("/score/{user_id}", response_model=StandardResponse[dict])
def trigger_score(
    user_id: str,
    window_days: int = settings.DEFAULT_SCORING_WINDOW_DAYS,
    analyst: str = settings.DEFAULT_ANALYST,
    case_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    engine = RiskScoringEngine(db)
    try:
        result = engine.score_user(user_id, window_days, analyst, case_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    write_audit_log(db, actor=analyst, action="risk.score.recalculate",
                    resource_type="user", resource_id=user_id,
                    details={"score": result.total_score, "severity": result.severity})
    return StandardResponse(success=True, data={
        "user_id": user_id,
        "total_score": result.total_score,
        "severity": result.severity,
        "triggered_rules": result.triggered_rules,
        "composite_multipliers": result.composite_multipliers_applied,
        "event_count": result.event_count,
        "breakdown": result.score_breakdown,
        "calculated_at": result.calculated_at.isoformat(),
    })


@router.get("/scores/{user_id}", response_model=StandardResponse[list[dict]])
def get_scores(user_id: str, limit: int = 10, db: Session = Depends(get_db)):
    scores = db.query(RiskScore).filter(
        RiskScore.user_id == user_id
    ).order_by(RiskScore.calculated_at.desc()).limit(limit).all()
    return StandardResponse(success=True, data=[{
        "id": s.id, "total_score": s.total_score, "severity": s.severity,
        "score_data_exfil": s.score_data_exfil,
        "score_access_anomaly": s.score_access_anomaly,
        "score_behavior_dev": s.score_behavior_dev,
        "score_hr_context": s.score_hr_context,
        "score_temporal": s.score_temporal,
        "event_count": s.event_count,
        "calculated_at": s.calculated_at.isoformat(),
        "calculated_by": s.calculated_by,
    } for s in scores])


@router.post("/score-all", response_model=StandardResponse[dict])
def score_all(analyst: str = settings.DEFAULT_ANALYST, db: Session = Depends(get_db)):
    users = db.query(User).filter(User.employment_status == "active").all()
    engine = RiskScoringEngine(db)
    scored, errors, high_risk = 0, [], []
    for user in users:
        try:
            result = engine.score_user(user.id)
            scored += 1
            if result.severity in ("high", "critical"):
                high_risk.append({"email": user.email, "score": result.total_score, "severity": result.severity})
        except Exception as e:
            errors.append({"user_id": user.id, "error": str(e)})
    write_audit_log(db, actor=analyst, action="risk.score.calculate",
                    resource_type="system", details={"scored": scored})
    return StandardResponse(success=True, data={"scored": scored, "high_risk": high_risk, "errors": errors})


@router.get("/dashboard", response_model=StandardResponse[dict])
def dashboard(db: Session = Depends(get_db)):
    from sqlalchemy import func
    from datetime import date

    today = datetime.combine(date.today(), datetime.min.time())
    active_users = db.query(User).filter(User.employment_status == "active").count()
    critical_cases = db.query(Case).filter(
        Case.severity == "critical", ~Case.status.like("closed%")
    ).count()
    high_cases = db.query(Case).filter(
        Case.severity == "high", ~Case.status.like("closed%")
    ).count()
    open_alerts = db.query(Alert).filter(Alert.status.in_(["new", "reviewing"])).count()
    alerts_today = db.query(Alert).filter(Alert.detected_at >= today).count()
    avg_score = db.query(func.avg(RiskScore.total_score)).scalar() or 0

    # Top 5 risky users by latest score
    all_scores = db.query(RiskScore).order_by(RiskScore.calculated_at.desc()).all()
    seen, top = set(), []
    for s in all_scores:
        if s.user_id not in seen:
            seen.add(s.user_id)
            u = db.query(User).filter(User.id == s.user_id).first()
            top.append({"user_id": s.user_id, "email": u.email if u else "",
                        "display_name": u.display_name if u else "",
                        "score": s.total_score, "severity": s.severity})
        if len(top) >= 5:
            break

    alerts_by_sev = dict(db.query(Alert.severity, func.count(Alert.id)).group_by(Alert.severity).all())
    events_by_src = dict(db.query(RawEvent.data_source_type, func.count(RawEvent.id)).group_by(RawEvent.data_source_type).all())
    cases_by_status = dict(db.query(Case.status, func.count(Case.id)).group_by(Case.status).all())

    recent = db.query(Alert).order_by(Alert.detected_at.desc()).limit(5).all()

    return StandardResponse(success=True, data={
        "total_users_active": active_users,
        "critical_cases": critical_cases,
        "high_cases": high_cases,
        "open_alerts": open_alerts,
        "alerts_today": alerts_today,
        "avg_risk_score": round(float(avg_score), 1),
        "top_risky_users": top,
        "alerts_by_severity": alerts_by_sev,
        "events_by_source": events_by_src,
        "cases_by_status": cases_by_status,
        "recent_alerts": [{"id": a.id, "title": a.title, "severity": a.severity,
                           "detected_at": a.detected_at.isoformat()} for a in recent],
    })
