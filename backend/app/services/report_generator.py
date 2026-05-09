import json
from datetime import datetime
from typing import Optional

from jinja2 import Template
from sqlalchemy.orm import Session

from app.models.case import Case, CaseEvent, AnalystNote, RiskScore, ReportDraft
from app.models.event import RawEvent
from app.models.user import User


REPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  body { font-family: Arial, sans-serif; max-width: 900px; margin: 40px auto; color: #1a1a1a; }
  h1 { color: #1a1a1a; border-bottom: 2px solid #dc2626; padding-bottom: 8px; }
  h2 { color: #374151; border-left: 4px solid #dc2626; padding-left: 12px; margin-top: 32px; }
  .meta { background: #f9fafb; padding: 16px; border-radius: 6px; margin-bottom: 24px; }
  .meta table { width: 100%; border-collapse: collapse; }
  .meta td { padding: 4px 8px; }
  .meta td:first-child { font-weight: bold; width: 180px; color: #6b7280; }
  .severity-critical { color: #dc2626; font-weight: bold; }
  .severity-high { color: #ea580c; font-weight: bold; }
  .severity-medium { color: #ca8a04; font-weight: bold; }
  .severity-low { color: #16a34a; font-weight: bold; }
  .section { margin-bottom: 24px; }
  .content { background: #fff; padding: 16px; border: 1px solid #e5e7eb; border-radius: 6px; }
  .watermark { color: #dc2626; font-size: 11px; text-align: center; margin-top: 40px; padding-top: 16px; border-top: 1px solid #e5e7eb; }
  .indicator { display: inline-block; background: #fef3c7; border: 1px solid #fcd34d; padding: 2px 10px; border-radius: 12px; margin: 2px; font-size: 13px; }
  pre { background: #f3f4f6; padding: 12px; border-radius: 4px; white-space: pre-wrap; }
</style>
</head>
<body>
<h1>Insider Risk Investigation Report</h1>
<div class="meta">
  <table>
    <tr><td>Case Number</td><td>{{ case.case_number }}</td></tr>
    <tr><td>Subject</td><td>{{ user.display_name }} ({{ user.email }})</td></tr>
    <tr><td>Department</td><td>{{ user.department }}</td></tr>
    <tr><td>Severity</td><td><span class="severity-{{ case.severity }}">{{ case.severity | upper }}</span></td></tr>
    <tr><td>Risk Score</td><td>{{ "%.1f"|format(case.risk_score) }} / 100</td></tr>
    <tr><td>Status</td><td>{{ case.status }}</td></tr>
    <tr><td>Case Period</td><td>{{ case.case_period_start }} → {{ case.case_period_end }}</td></tr>
    <tr><td>Report Generated</td><td>{{ generated_at }}</td></tr>
    <tr><td>Prepared By</td><td>{{ report.created_by }}</td></tr>
    {% if report.approved_by %}<tr><td>Approved By</td><td>{{ report.approved_by }}</td></tr>{% endif %}
  </table>
</div>

{% if key_indicators %}
<div class="section">
<h2>Key Indicators</h2>
<div class="content">
{% for ind in key_indicators %}<span class="indicator">{{ ind }}</span>{% endfor %}
</div>
</div>
{% endif %}

<div class="section">
<h2>Initial Assessment</h2>
<div class="content"><pre>{{ report.initial_assessment or "No assessment recorded." }}</pre></div>
</div>

<div class="section">
<h2>Risk Analysis</h2>
<div class="content"><pre>{{ report.risk_analysis or "No analysis recorded." }}</pre></div>
</div>

<div class="section">
<h2>Evidence Summary</h2>
<div class="content"><pre>{{ report.evidence_summary or "No evidence summary recorded." }}</pre></div>
</div>

<div class="section">
<h2>Recommended Next Steps</h2>
<div class="content"><pre>{{ report.recommended_actions or "No recommendations recorded." }}</pre></div>
</div>

<div class="section">
<h2>Final Case Summary</h2>
<div class="content"><pre>{{ report.final_summary or "Pending analyst review." }}</pre></div>
</div>

<div class="watermark">
CONFIDENTIAL — FOR AUTHORIZED SECURITY PERSONNEL ONLY<br>
This document contains sensitive information. Unauthorized disclosure is prohibited.<br>
Generated: {{ generated_at }} | Case: {{ case.case_number }}
</div>
</body>
</html>"""


class ReportGenerator:

    def __init__(self, db: Session):
        self.db = db

    def generate_draft(self, case: Case) -> dict:
        user = self.db.query(User).filter(User.id == case.subject_user_id).first()
        events = self._get_case_events(case.id)
        score = self.db.query(RiskScore).filter(
            RiskScore.user_id == case.subject_user_id
        ).order_by(RiskScore.calculated_at.desc()).first()

        indicators = json.loads(case.key_indicators) if case.key_indicators else []

        initial = self._build_initial_assessment(case, user, score)
        risk = self._build_risk_analysis(case, score, indicators)
        evidence = self._build_evidence_summary(events)
        actions = self._build_recommended_actions(case, indicators)
        summary = f"Case {case.case_number} opened {case.created_at.strftime('%Y-%m-%d')}. Subject: {user.display_name if user else 'Unknown'}. Severity: {case.severity.upper()}. Pending analyst review and sign-off."

        return {
            "initial_assessment": initial,
            "key_indicators": "\n".join(f"• {i}" for i in indicators),
            "risk_analysis": risk,
            "evidence_summary": evidence,
            "recommended_actions": actions,
            "final_summary": summary,
        }

    def render_html(self, report: ReportDraft) -> str:
        case = self.db.query(Case).filter(Case.id == report.case_id).first()
        user = self.db.query(User).filter(User.id == case.subject_user_id).first() if case else None
        indicators = json.loads(case.key_indicators) if case and case.key_indicators else []

        tmpl = Template(REPORT_TEMPLATE)
        return tmpl.render(
            report=report,
            case=case,
            user=user,
            key_indicators=indicators,
            generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        )

    def _get_case_events(self, case_id: str) -> list[RawEvent]:
        ce_ids = [
            r[0] for r in self.db.query(CaseEvent.raw_event_id)
            .filter(CaseEvent.case_id == case_id).all()
        ]
        if not ce_ids:
            return []
        return self.db.query(RawEvent).filter(
            RawEvent.id.in_(ce_ids)
        ).order_by(RawEvent.event_timestamp).all()

    def _build_initial_assessment(self, case: Case, user: Optional[User], score: Optional[RiskScore]) -> str:
        lines = [
            f"Subject: {user.display_name if user else 'Unknown'} ({user.email if user else ''})",
            f"Department: {user.department if user else 'N/A'} | Location: {user.location if user else 'N/A'}",
        ]
        if user:
            if user.is_pending_resign:
                lines.append(f"⚠ Employee has submitted resignation. Last day: {user.termination_date}")
            if user.is_on_pip:
                lines.append("⚠ Employee is currently on a Performance Improvement Plan (PIP)")
            if user.hr_risk_flag:
                lines.append(f"⚠ HR Note: {user.hr_risk_flag}")
        if score:
            lines.append(f"\nRisk Score: {score.total_score}/100 ({score.severity.upper()})")
            lines.append(f"Data Exfiltration: {score.score_data_exfil:.1f}/30")
            lines.append(f"Access Anomaly: {score.score_access_anomaly:.1f}/25")
            lines.append(f"HR Context: {score.score_hr_context:.1f}/15")
        return "\n".join(lines)

    def _build_risk_analysis(self, case: Case, score: Optional[RiskScore], indicators: list[str]) -> str:
        lines = [f"Overall Risk: {case.severity.upper()} (Score: {case.risk_score:.1f}/100)"]
        if score and score.triggered_rules:
            rules = json.loads(score.triggered_rules)
            lines.append(f"Triggered Rules: {', '.join(rules)}")
        if score and score.score_breakdown:
            bd = json.loads(score.score_breakdown)
            if bd.get("multiplier", 1) > 1:
                lines.append(f"Composite multiplier applied: ×{bd['multiplier']:.2f} (multi-signal escalation)")
        lines.append("\nRisk Factors:")
        for ind in indicators:
            lines.append(f"  • {ind}")
        return "\n".join(lines)

    def _build_evidence_summary(self, events: list[RawEvent]) -> str:
        if not events:
            return "No evidence events linked to this case."
        by_source: dict[str, int] = {}
        by_category: dict[str, int] = {}
        for ev in events:
            by_source[ev.data_source_type] = by_source.get(ev.data_source_type, 0) + 1
            by_category[ev.event_category] = by_category.get(ev.event_category, 0) + 1
        lines = [f"Total Events: {len(events)}"]
        lines.append("\nBy Source:")
        for src, cnt in sorted(by_source.items(), key=lambda x: -x[1]):
            lines.append(f"  • {src}: {cnt} event(s)")
        lines.append("\nBy Category:")
        for cat, cnt in sorted(by_category.items(), key=lambda x: -x[1]):
            lines.append(f"  • {cat}: {cnt} event(s)")
        if events:
            lines.append(f"\nEarliest Event: {events[0].event_timestamp}")
            lines.append(f"Latest Event:   {events[-1].event_timestamp}")
        return "\n".join(lines)

    def _build_recommended_actions(self, case: Case, indicators: list[str]) -> str:
        actions = ["[ ] Analyst review and verification of all linked evidence"]
        if any("resignation" in i.lower() or "resign" in i.lower() for i in indicators):
            actions.append("[ ] Coordinate with HR to review offboarding checklist")
            actions.append("[ ] Verify access revocation schedule")
        if any("cloud" in i.lower() or "usb" in i.lower() for i in indicators):
            actions.append("[ ] Confirm whether transferred data was recovered or remains at risk")
            actions.append("[ ] Review DLP policy coverage and gap analysis")
        if any("email" in i.lower() for i in indicators):
            actions.append("[ ] Preserve email evidence and export for legal hold")
        if case.severity in ("critical", "high"):
            actions.append("[ ] Escalate to Legal / HR Business Partner")
            actions.append("[ ] Consider immediate access suspension pending investigation")
        actions.append("[ ] Document final disposition and close case with sign-off")
        return "\n".join(actions)
