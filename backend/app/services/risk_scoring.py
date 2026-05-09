import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

from app.models.case import RiskScore
from app.models.event import RawEvent
from app.models.user import User
from app.services.risk_rules_config import (
    DIMENSION_CAPS, PERSONAL_CLOUD_SERVICES, PERSONAL_EMAIL_DOMAINS,
    SEVERITY_THRESHOLDS,
)


@dataclass
class RuleResult:
    rule_id: str
    triggered: bool
    score: float
    evidence: str


@dataclass
class DimensionResult:
    dimension: str
    raw_score: float
    capped_score: float
    rules: list[RuleResult]


@dataclass
class ScoringResult:
    user_id: str
    total_score: float
    severity: str
    dimension_results: dict[str, DimensionResult]
    composite_multipliers_applied: list[str]
    triggered_rules: list[str]
    score_breakdown: dict
    event_window_start: datetime
    event_window_end: datetime
    event_count: int
    calculated_at: datetime = field(default_factory=datetime.utcnow)


class RiskScoringEngine:

    def __init__(self, db: Session):
        self.db = db

    def score_user(
        self,
        user_id: str,
        window_days: int = 14,
        calculated_by: str = "system",
        case_id: Optional[str] = None,
    ) -> ScoringResult:
        window_end = datetime.utcnow()
        window_start = window_end - timedelta(days=window_days)

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        events_df = self._load_user_events(user_id, window_start, window_end)

        d1 = self._score_d1(events_df)
        d2 = self._score_d2(events_df)
        d3 = self._score_d3(events_df)
        d4 = self._score_d4(user, window_end)
        d5 = self._score_d5(events_df)

        dims = {"D1": d1, "D2": d2, "D3": d3, "D4": d4, "D5": d5}
        raw_total = sum(d.capped_score for d in dims.values())
        triggered = [
            r.rule_id for d in dims.values() for r in d.rules if r.triggered
        ]

        multiplier, applied_cms = self._composite_multiplier(triggered, events_df)
        final = min(100.0, round(raw_total * multiplier, 1))
        severity = self._severity(final)

        result = ScoringResult(
            user_id=user_id,
            total_score=final,
            severity=severity,
            dimension_results=dims,
            composite_multipliers_applied=applied_cms,
            triggered_rules=triggered,
            score_breakdown={
                "D1": d1.capped_score, "D2": d2.capped_score,
                "D3": d3.capped_score, "D4": d4.capped_score,
                "D5": d5.capped_score, "raw_total": raw_total,
                "multiplier": multiplier, "final": final,
            },
            event_window_start=window_start,
            event_window_end=window_end,
            event_count=len(events_df),
        )
        self._persist(result, calculated_by, case_id)
        return result

    # ── D1: Data Exfiltration ─────────────────────────────────────────

    def _score_d1(self, events: pd.DataFrame) -> DimensionResult:
        rules, total = [], 0.0

        r01 = events[
            (events["event_category"] == "cloud_upload") &
            (events["destination_type"].isin(PERSONAL_CLOUD_SERVICES)) &
            (events["action_result"].str.lower() == "blocked")
        ] if not events.empty else pd.DataFrame()
        s = min(8.0 * len(r01), 15.0)
        rules.append(RuleResult("R01", len(r01) > 0, s, f"{len(r01)} blocked personal cloud upload(s)"))
        total += s

        r02 = events[
            (events["event_category"] == "cloud_upload") &
            (events["destination_type"].isin(PERSONAL_CLOUD_SERVICES)) &
            (events["action_result"].str.lower() != "blocked")
        ] if not events.empty else pd.DataFrame()
        s = min(5.0 * len(r02), 12.0)
        rules.append(RuleResult("R02", len(r02) > 0, s, f"{len(r02)} allowed personal cloud upload(s)"))
        total += s

        r03 = events[
            (events["event_category"] == "usb_transfer") &
            (events["action_result"].str.lower() == "blocked")
        ] if not events.empty else pd.DataFrame()
        s = min(7.0 * len(r03), 12.0)
        rules.append(RuleResult("R03", len(r03) > 0, s, f"{len(r03)} blocked USB transfer(s)"))
        total += s

        r05 = events[
            (events["event_category"].isin(["email_send", "email_forward"])) &
            (events["destination_detail"].fillna("").apply(
                lambda x: any(d in x for d in PERSONAL_EMAIL_DOMAINS)
            ))
        ] if not events.empty else pd.DataFrame()
        s = min(8.0 * len(r05), 15.0)
        rules.append(RuleResult("R05", len(r05) > 0, s, f"{len(r05)} email(s) to personal address"))
        total += s

        r07 = events[
            events["sensitivity_label"].fillna("").str.contains("Highly Confidential", case=False)
        ] if not events.empty else pd.DataFrame()
        s = min(3.0 * len(r07), 10.0)
        rules.append(RuleResult("R07", len(r07) > 0, s, f"{len(r07)} Highly Confidential event(s)"))
        total += s

        capped = min(total, DIMENSION_CAPS["D1"])
        return DimensionResult("D1", total, capped, rules)

    # ── D2: Access Anomaly ────────────────────────────────────────────

    def _score_d2(self, events: pd.DataFrame) -> DimensionResult:
        rules, total = [], 0.0
        logins = events[events["event_category"] == "login"].copy() if not events.empty else pd.DataFrame()

        if not logins.empty:
            logins["hour"] = pd.to_datetime(logins["event_timestamp"]).dt.hour
            offhour = logins[
                (logins["hour"] >= 0) & (logins["hour"] < 6) &
                (logins["action_result"].fillna("").str.lower() == "success")
            ]
            s = min(10.0 * len(offhour), 10.0)
        else:
            offhour = pd.DataFrame()
            s = 0.0
        rules.append(RuleResult("R09", len(offhour) > 0, s, f"{len(offhour)} off-hours login(s)"))
        total += s

        brute = 0
        if not logins.empty:
            logins_sorted = logins.sort_values("event_timestamp")
            prev_fail = 0
            for _, row in logins_sorted.iterrows():
                result = str(row.get("action_result", "")).lower()
                if result == "failure":
                    prev_fail += 1
                elif result == "success" and prev_fail >= 2:
                    brute += 1
                    prev_fail = 0
                else:
                    prev_fail = 0
        s = min(7.0 * brute, 7.0)
        rules.append(RuleResult("R11", brute > 0, s, f"{brute} brute-force pattern(s)"))
        total += s

        high_risk = logins[
            logins["severity_original"].fillna("").str.lower().isin(["high", "medium"])
        ] if not logins.empty else pd.DataFrame()
        s = 8.0 if len(high_risk) > 0 else 0.0
        rules.append(RuleResult("R12", len(high_risk) > 0, s, f"{len(high_risk)} high-risk login flag(s)"))
        total += s

        capped = min(total, DIMENSION_CAPS["D2"])
        return DimensionResult("D2", total, capped, rules)

    # ── D3: Behavioral Baseline (simplified for MVP) ──────────────────

    def _score_d3(self, events: pd.DataFrame) -> DimensionResult:
        rules, total = [], 0.0
        if events.empty:
            return DimensionResult("D3", 0.0, 0.0, rules)

        ev = events.copy()
        ev["date"] = pd.to_datetime(ev["event_timestamp"]).dt.date
        daily = ev.groupby("date").size()
        avg_daily = daily.mean()

        s = 8.0 if avg_daily >= 10 else (4.0 if avg_daily >= 5 else 0.0)
        rules.append(RuleResult("R15", s > 0, s, f"Avg {avg_daily:.1f} events/day"))
        total += s

        upload = ev[ev["event_category"].isin(["cloud_upload", "file_upload"])]
        daily_mb = (upload.groupby("date")["object_size_bytes"].sum() / 1_048_576).mean() if not upload.empty else 0
        s = 8.0 if daily_mb >= 50 else (4.0 if daily_mb >= 10 else 0.0)
        rules.append(RuleResult("R16", s > 0, s, f"Avg {daily_mb:.1f} MB/day upload"))
        total += s

        capped = min(total, DIMENSION_CAPS["D3"])
        return DimensionResult("D3", total, capped, rules)

    # ── D4: HR Context ────────────────────────────────────────────────

    def _score_d4(self, user: User, ref: datetime) -> DimensionResult:
        rules, total = [], 0.0

        s = 10.0 if user.is_pending_resign else 0.0
        rules.append(RuleResult("R19", bool(user.is_pending_resign), s, "Pending resignation"))
        total += s

        s = 0.0
        if user.termination_date:
            days = (user.termination_date - ref.date()).days
            s = 8.0 if 0 <= days <= 30 else (4.0 if 0 <= days <= 60 else 0.0)
        rules.append(RuleResult("R20", s > 0, s, f"Termination: {user.termination_date}"))
        total += s

        s = 7.0 if user.is_on_pip else 0.0
        rules.append(RuleResult("R21", bool(user.is_on_pip), s, "On PIP"))
        total += s

        s = 4.0 if user.is_pending_transfer else 0.0
        rules.append(RuleResult("R22", bool(user.is_pending_transfer), s, "Pending transfer"))
        total += s

        s = 3.0 if (user.hr_risk_flag and user.hr_risk_flag.strip()) else 0.0
        rules.append(RuleResult("R23", s > 0, s, user.hr_risk_flag or ""))
        total += s

        capped = min(total, DIMENSION_CAPS["D4"])
        return DimensionResult("D4", total, capped, rules)

    # ── D5: Temporal Pattern ──────────────────────────────────────────

    def _score_d5(self, events: pd.DataFrame) -> DimensionResult:
        rules, total = [], 0.0
        if events.empty:
            return DimensionResult("D5", 0.0, 0.0, rules)

        ev = events.copy()
        ev["ts"] = pd.to_datetime(ev["event_timestamp"])
        ev["is_weekend"] = ev["ts"].dt.dayofweek >= 5

        weekend = ev[ev["is_weekend"]]
        weekday = ev[~ev["is_weekend"]]
        we_avg = len(weekend) / max(weekend["ts"].dt.date.nunique(), 1) if not weekend.empty else 0
        wd_avg = len(weekday) / max(weekday["ts"].dt.date.nunique(), 1) if not weekday.empty else 0

        s = 3.0 if (we_avg > wd_avg * 0.5 and we_avg > 2) else 0.0
        rules.append(RuleResult("R26", s > 0, s, f"Weekend avg {we_avg:.1f} vs weekday {wd_avg:.1f}"))
        total += s

        # Cluster: 5+ events in 30-min window
        max_cluster = 0
        ev_sorted = ev.sort_values("ts")
        for ts in ev_sorted["ts"]:
            window = ev_sorted[
                (ev_sorted["ts"] >= ts) &
                (ev_sorted["ts"] <= ts + timedelta(minutes=30))
            ]
            max_cluster = max(max_cluster, len(window))

        s = 5.0 if max_cluster >= 5 else 0.0
        rules.append(RuleResult("R24", s > 0, s, f"Max {max_cluster} events in 30-min window"))
        total += s

        capped = min(total, DIMENSION_CAPS["D5"])
        return DimensionResult("D5", total, capped, rules)

    # ── Helpers ───────────────────────────────────────────────────────

    def _composite_multiplier(self, triggered: list[str], events: pd.DataFrame):
        mult, applied = 1.0, []
        d1 = {"R01", "R02", "R03", "R05"}
        d4 = {"R19", "R20", "R21"}

        if len(d1 & set(triggered)) >= 2:
            mult *= 1.3
            applied.append("CM01: DLP blocked but continued attempts")
        if (d1 & set(triggered)) and (d4 & set(triggered)):
            mult *= 1.2
            applied.append("CM04: HR risk + exfiltration signal")
        if "R09" in triggered and not events.empty:
            sens = events[
                events["sensitivity_label"].fillna("").str.contains("Confidential", case=False)
            ]
            if not sens.empty:
                mult *= 1.15
                applied.append("CM03: After-hours + sensitive data")
        return mult, applied

    def _severity(self, score: float) -> str:
        if score >= 80: return "critical"
        if score >= 60: return "high"
        if score >= 40: return "medium"
        return "low"

    def _load_user_events(self, user_id: str, start: datetime, end: datetime) -> pd.DataFrame:
        rows = self.db.query(RawEvent).filter(
            RawEvent.user_id == user_id,
            RawEvent.event_timestamp >= start,
            RawEvent.event_timestamp <= end,
        ).all()
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame([{
            "id": e.id,
            "event_category": e.event_category,
            "event_timestamp": e.event_timestamp,
            "action_result": e.action_result or "",
            "destination_type": e.destination_type or "",
            "destination_detail": e.destination_detail or "",
            "object_size_bytes": e.object_size_bytes or 0,
            "sensitivity_label": e.sensitivity_label or "",
            "severity_original": e.severity_original or "",
            "raw_data": e.raw_data or "{}",
        } for e in rows])

    def _persist(self, result: ScoringResult, calculated_by: str, case_id: Optional[str]):
        score = RiskScore(
            id=str(uuid.uuid4()),
            user_id=result.user_id,
            total_score=result.total_score,
            severity=result.severity,
            score_data_exfil=result.dimension_results["D1"].capped_score,
            score_access_anomaly=result.dimension_results["D2"].capped_score,
            score_behavior_dev=result.dimension_results["D3"].capped_score,
            score_hr_context=result.dimension_results["D4"].capped_score,
            score_temporal=result.dimension_results["D5"].capped_score,
            score_breakdown=json.dumps(result.score_breakdown),
            triggered_rules=json.dumps(result.triggered_rules),
            event_window_start=result.event_window_start,
            event_window_end=result.event_window_end,
            event_count=result.event_count,
            calculated_by=calculated_by,
            case_id=case_id,
        )
        self.db.add(score)
        self.db.commit()
