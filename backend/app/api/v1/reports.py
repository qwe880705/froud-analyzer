import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.config import settings
from app.models.case import Case, ReportDraft
from app.schemas.common import StandardResponse
from app.middleware.audit import write_audit_log
from app.services.report_generator import ReportGenerator

router = APIRouter(prefix="/reports", tags=["Reports"])


class ReportContent(BaseModel):
    initial_assessment: Optional[str] = None
    key_indicators: Optional[str] = None
    risk_analysis: Optional[str] = None
    evidence_summary: Optional[str] = None
    recommended_actions: Optional[str] = None
    final_summary: Optional[str] = None
    analyst: str = settings.DEFAULT_ANALYST


@router.get("/{case_id}", response_model=StandardResponse[dict])
def get_report(
    case_id: str,
    analyst: str = settings.DEFAULT_ANALYST,
    db: Session = Depends(get_db),
):
    report = db.query(ReportDraft).filter(
        ReportDraft.case_id == case_id
    ).order_by(ReportDraft.version.desc()).first()
    if not report:
        raise HTTPException(404, "No report found")
    write_audit_log(db, actor=analyst, action="report.draft.view",
                    resource_type="report", resource_id=report.id)
    return StandardResponse(success=True, data={
        "id": report.id, "version": report.version, "status": report.status,
        "initial_assessment": report.initial_assessment,
        "key_indicators": report.key_indicators,
        "risk_analysis": report.risk_analysis,
        "evidence_summary": report.evidence_summary,
        "recommended_actions": report.recommended_actions,
        "final_summary": report.final_summary,
        "created_by": report.created_by,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "approved_by": report.approved_by,
        "approved_at": report.approved_at.isoformat() if report.approved_at else None,
    })


@router.post("/{case_id}", response_model=StandardResponse[dict])
def create_report(case_id: str, body: ReportContent, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    last = db.query(ReportDraft).filter(
        ReportDraft.case_id == case_id
    ).order_by(ReportDraft.version.desc()).first()
    version = (last.version + 1) if last else 1

    gen = ReportGenerator(db)
    auto = gen.generate_draft(case)

    report = ReportDraft(
        id=str(uuid.uuid4()), case_id=case_id, version=version,
        initial_assessment=body.initial_assessment or auto["initial_assessment"],
        key_indicators=body.key_indicators or auto["key_indicators"],
        risk_analysis=body.risk_analysis or auto["risk_analysis"],
        evidence_summary=body.evidence_summary or auto["evidence_summary"],
        recommended_actions=body.recommended_actions or auto["recommended_actions"],
        final_summary=body.final_summary or auto["final_summary"],
        status="draft", created_by=body.analyst,
    )
    db.add(report)
    db.commit()
    write_audit_log(db, actor=body.analyst, action="report.draft.create",
                    resource_type="report", resource_id=report.id)
    return StandardResponse(success=True,
                            data={"report_id": report.id, "version": version},
                            message="Report draft created")


@router.patch("/{case_id}", response_model=StandardResponse[dict])
def update_report(case_id: str, body: ReportContent, db: Session = Depends(get_db)):
    report = db.query(ReportDraft).filter(
        ReportDraft.case_id == case_id, ReportDraft.status == "draft"
    ).order_by(ReportDraft.version.desc()).first()
    if not report:
        raise HTTPException(404, "No draft report found")
    if body.initial_assessment is not None: report.initial_assessment = body.initial_assessment
    if body.key_indicators is not None:     report.key_indicators = body.key_indicators
    if body.risk_analysis is not None:      report.risk_analysis = body.risk_analysis
    if body.evidence_summary is not None:   report.evidence_summary = body.evidence_summary
    if body.recommended_actions is not None: report.recommended_actions = body.recommended_actions
    if body.final_summary is not None:      report.final_summary = body.final_summary
    db.commit()
    write_audit_log(db, actor=body.analyst, action="report.draft.edit",
                    resource_type="report", resource_id=report.id)
    return StandardResponse(success=True, message="Report updated")


@router.post("/{case_id}/submit", response_model=StandardResponse[dict])
def submit(case_id: str, analyst: str = settings.DEFAULT_ANALYST, db: Session = Depends(get_db)):
    report = db.query(ReportDraft).filter(
        ReportDraft.case_id == case_id, ReportDraft.status == "draft"
    ).order_by(ReportDraft.version.desc()).first()
    if not report:
        raise HTTPException(404, "No draft report found")
    report.status = "pending_review"
    report.submitted_for_review_at = datetime.utcnow()
    db.commit()
    write_audit_log(db, actor=analyst, action="report.submit_review",
                    resource_type="report", resource_id=report.id)
    return StandardResponse(success=True, message="Submitted for review")


@router.post("/{case_id}/approve", response_model=StandardResponse[dict])
def approve(case_id: str, analyst: str = settings.DEFAULT_ANALYST, db: Session = Depends(get_db)):
    report = db.query(ReportDraft).filter(
        ReportDraft.case_id == case_id, ReportDraft.status == "pending_review"
    ).order_by(ReportDraft.version.desc()).first()
    if not report:
        raise HTTPException(404, "No report pending review")
    report.status = "approved"
    report.approved_by = analyst
    report.approved_at = datetime.utcnow()
    db.commit()
    write_audit_log(db, actor=analyst, action="report.approve",
                    resource_type="report", resource_id=report.id)
    return StandardResponse(success=True, message="Report approved")


@router.get("/{case_id}/export", response_class=HTMLResponse)
def export(case_id: str, analyst: str = settings.DEFAULT_ANALYST, db: Session = Depends(get_db)):
    report = db.query(ReportDraft).filter(
        ReportDraft.case_id == case_id, ReportDraft.status == "approved"
    ).order_by(ReportDraft.version.desc()).first()
    if not report:
        raise HTTPException(403, "Only approved reports can be exported")
    gen = ReportGenerator(db)
    html = gen.render_html(report)
    report.exported_at = datetime.utcnow()
    report.export_format = "html"
    db.commit()
    write_audit_log(db, actor=analyst, action="report.export",
                    resource_type="report", resource_id=report.id)
    return HTMLResponse(content=html)
