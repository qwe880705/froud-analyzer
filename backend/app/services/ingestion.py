import hashlib
import io
import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

from app.models.event import IngestionBatch, RawEvent
from app.models.user import User


@dataclass
class IngestionResult:
    batch_id: str
    status: str
    record_count: int
    success_count: int
    error_count: int
    errors: list[str]
    alerts_created: int = 0
    cases_created: int = 0


# Maps source CSV column names → RawEvent fields
SOURCE_MAPPINGS = {
    "hr_system": {
        "employee_id": "employee_id",
        "display_name": "display_name",
        "email": "email",
        "department": "department",
        "job_title": "job_title",
        "location": "location",
        "employment_status": "employment_status",
        "hire_date": "hire_date",
        "termination_date": "termination_date",
        "is_on_pip": "is_on_pip",
        "is_pending_transfer": "is_pending_transfer",
        "is_pending_resign": "is_pending_resign",
        "hr_risk_flag": "hr_risk_flag",
    },
    "purview_dlp": {
        "EventDateTime": "event_timestamp",
        "UserEmail": "user_email",
        "UserDisplayName": "user_display_name",
        "DeviceId": "device_id",
        "DeviceName": "device_name",
        "PolicyName": "policy_name",
        "PolicyRule": "policy_rule",
        "SensitivityLabel": "sensitivity_label",
        "ActivityType": "_event_type",
        "ObjectName": "object_name",
        "ObjectPath": "object_path",
        "ObjectSize": "object_size_bytes",
        "Destination": "destination_detail",
        "DestinationType": "destination_type",
        "ActionTaken": "action_result",
        "Location": "location_city",
        "IPAddress": "source_ip",
        "EventId": "original_event_id",
    },
    "entra_id": {
        "EventDateTime": "event_timestamp",
        "UserEmail": "user_email",
        "UserDisplayName": "user_display_name",
        "DeviceName": "device_name",
        "LoginResult": "action_result",
        "IPAddress": "source_ip",
        "Country": "location_country",
        "City": "location_city",
        "RiskLevel": "severity_original",
        "EventId": "original_event_id",
    },
    "defender_endpoint": {
        "EventDateTime": "event_timestamp",
        "UserEmail": "user_email",
        "DeviceId": "device_id",
        "DeviceName": "device_name",
        "EventType": "_event_type",
        "FilePath": "object_path",
        "FileName": "object_name",
        "FileSize": "object_size_bytes",
        "ActionType": "action_result",
        "AlertSeverity": "severity_original",
        "EventId": "original_event_id",
    },
    "proxy_web": {
        "EventDateTime": "event_timestamp",
        "UserEmail": "user_email",
        "DeviceId": "device_id",
        "SourceIP": "source_ip",
        "DestinationDomain": "destination_detail",
        "DestinationURL": "object_path",
        "BytesSent": "object_size_bytes",
        "ActionTaken": "action_result",
        "EventId": "original_event_id",
    },
    "email_log": {
        "EventDateTime": "event_timestamp",
        "SenderEmail": "user_email",
        "RecipientEmails": "destination_detail",
        "RecipientDomains": "_recipient_domains",
        "Subject": "object_name",
        "TotalAttachmentSize": "object_size_bytes",
        "MessageId": "original_event_id",
        "EventId": "original_event_id",
    },
    "usb_file_transfer": {
        "EventDateTime": "event_timestamp",
        "UserEmail": "user_email",
        "DeviceId": "device_id",
        "DeviceName": "device_name",
        "USBDeviceName": "destination_detail",
        "FileCount": "object_count",
        "TotalSizeBytes": "object_size_bytes",
        "ActionTaken": "action_result",
        "EventId": "original_event_id",
    },
    "cloud_upload": {
        "EventDateTime": "event_timestamp",
        "UserEmail": "user_email",
        "DeviceId": "device_id",
        "SourceIP": "source_ip",
        "CloudService": "destination_type",
        "FileName": "object_name",
        "FileSize": "object_size_bytes",
        "SensitivityLabel": "sensitivity_label",
        "IsPersonalAccount": "_is_personal",
        "ActionTaken": "action_result",
        "EventId": "original_event_id",
    },
    "sentinel": {
        "EventDateTime": "event_timestamp",
        "AlertName": "event_type",
        "Severity": "severity_original",
        "UserEmail": "user_email",
        "DeviceId": "device_id",
        "SourceIP": "source_ip",
        "TacticName": "_tactic",
        "Description": "object_name",
        "AlertId": "original_event_id",
    },
}

EVENT_CATEGORY_MAP = {
    # purview_dlp ActivityType
    "FileUploadedToCloud": "cloud_upload",
    "FileCopiedToRemovableMedia": "usb_transfer",
    "EmailSentExternal": "email_send",
    "FileDownloaded": "file_download",
    "FileAccessed": "file_access",
    # entra_id
    "Success": "login",
    "Failure": "login",
    # defender
    "FileCreated": "file_access",
    "FileCopied": "file_download",
    "RemovableMediaMount": "usb_transfer",
    "NetworkConnection": "web_browsing",
    "ProcessCreated": "other",
    # sentinel
    "Anomalous sign-in activity": "login",
    "Multiple failed sign-in attempts": "login",
    "Data exfiltration to cloud storage": "data_exfiltration",
    "After-hours data access and USB transfer": "usb_transfer",
    "Sensitive file copy to removable media": "usb_transfer",
}

SOURCE_CATEGORY_DEFAULTS = {
    "purview_dlp": "policy_violation",
    "entra_id": "login",
    "defender_endpoint": "file_access",
    "proxy_web": "web_browsing",
    "email_log": "email_send",
    "usb_file_transfer": "usb_transfer",
    "cloud_upload": "cloud_upload",
    "sentinel": "policy_violation",
}


class IngestionService:

    def __init__(self, db: Session):
        self.db = db

    async def ingest_csv(
        self,
        content: io.BytesIO,
        source_type: str,
        filename: Optional[str],
        file_hash: str,
        imported_by: str,
    ) -> IngestionResult:
        batch_id = str(uuid.uuid4())
        batch = IngestionBatch(
            id=batch_id,
            data_source_type=source_type,
            imported_by=imported_by,
            import_method="csv_upload",
            filename=filename,
            file_hash=file_hash,
            status="processing",
        )
        self.db.add(batch)
        self.db.commit()

        try:
            df = pd.read_csv(content)
            record_count = len(df)
            errors = []

            if source_type == "hr_system":
                success, errs = self._ingest_hr(df)
            else:
                success, errs = self._ingest_events(df, source_type, batch_id)

            errors.extend(errs)
            batch.record_count = record_count
            batch.success_count = success
            batch.error_count = len(errors)
            batch.status = "completed" if len(errors) == 0 else "partial"
            batch.completed_at = datetime.utcnow()
            batch.error_log = json.dumps(errors[:50])
            self.db.commit()

            alerts_created = 0
            cases_created = 0
            if source_type != "hr_system":
                alerts_created, cases_created = self._run_post_ingest_scoring(batch_id)

            return IngestionResult(
                batch_id=batch_id,
                status=batch.status,
                record_count=record_count,
                success_count=success,
                error_count=len(errors),
                errors=errors[:10],
                alerts_created=alerts_created,
                cases_created=cases_created,
            )
        except Exception as e:
            batch.status = "failed"
            batch.error_log = str(e)
            batch.completed_at = datetime.utcnow()
            self.db.commit()
            raise

    def _ingest_hr(self, df: pd.DataFrame) -> tuple[int, list[str]]:
        success, errors = 0, []
        for _, row in df.iterrows():
            try:
                email = str(row.get("email", "")).strip()
                if not email:
                    errors.append("Row missing email")
                    continue

                existing = self.db.query(User).filter(User.email == email).first()
                emp_id = str(row.get("employee_id", "")).strip()

                def parse_bool(v):
                    return str(v).upper() in ("TRUE", "1", "YES")

                def parse_date(v):
                    if pd.isna(v) or str(v).strip() == "":
                        return None
                    try:
                        return pd.to_datetime(v).date()
                    except Exception:
                        return None

                if existing:
                    existing.display_name = str(row.get("display_name", existing.display_name))
                    existing.department = str(row.get("department", "")) or None
                    existing.job_title = str(row.get("job_title", "")) or None
                    existing.location = str(row.get("location", "")) or None
                    existing.employment_status = str(row.get("employment_status", "active"))
                    existing.hire_date = parse_date(row.get("hire_date"))
                    existing.termination_date = parse_date(row.get("termination_date"))
                    existing.is_on_pip = parse_bool(row.get("is_on_pip", False))
                    existing.is_pending_transfer = parse_bool(row.get("is_pending_transfer", False))
                    existing.is_pending_resign = parse_bool(row.get("is_pending_resign", False))
                    existing.hr_risk_flag = str(row.get("hr_risk_flag", "")) or None
                    existing.updated_at = datetime.utcnow()
                else:
                    user = User(
                        id=str(uuid.uuid4()),
                        employee_id=emp_id or str(uuid.uuid4())[:8],
                        display_name=str(row.get("display_name", email)),
                        email=email,
                        department=str(row.get("department", "")) or None,
                        job_title=str(row.get("job_title", "")) or None,
                        location=str(row.get("location", "")) or None,
                        employment_status=str(row.get("employment_status", "active")),
                        hire_date=parse_date(row.get("hire_date")),
                        termination_date=parse_date(row.get("termination_date")),
                        is_on_pip=parse_bool(row.get("is_on_pip", False)),
                        is_pending_transfer=parse_bool(row.get("is_pending_transfer", False)),
                        is_pending_resign=parse_bool(row.get("is_pending_resign", False)),
                        hr_risk_flag=str(row.get("hr_risk_flag", "")) or None,
                    )
                    self.db.add(user)
                self.db.commit()
                success += 1
            except Exception as e:
                errors.append(str(e))
        return success, errors

    def _ingest_events(
        self, df: pd.DataFrame, source_type: str, batch_id: str
    ) -> tuple[int, list[str]]:
        success, errors = 0, []
        mapping = SOURCE_MAPPINGS.get(source_type, {})
        default_category = SOURCE_CATEGORY_DEFAULTS.get(source_type, "other")

        for _, row in df.iterrows():
            try:
                row_dict = row.to_dict()

                # Resolve user
                email_col = next((k for k, v in mapping.items() if v == "user_email"), None)
                user_email = str(row_dict.get(email_col, "")).strip() if email_col else ""
                user_id = None
                if user_email:
                    u = self.db.query(User).filter(User.email == user_email).first()
                    if u:
                        user_id = u.id

                # Resolve timestamp
                ts_col = next((k for k, v in mapping.items() if v == "event_timestamp"), None)
                raw_ts = row_dict.get(ts_col, "") if ts_col else ""
                try:
                    event_ts = pd.to_datetime(raw_ts)
                    if event_ts.tzinfo is not None:
                        event_ts = event_ts.tz_convert("UTC").tz_localize(None)
                except Exception:
                    event_ts = datetime.utcnow()

                # Resolve event category
                type_col = next((k for k, v in mapping.items() if v == "_event_type"), None)
                raw_type = str(row_dict.get(type_col, "")) if type_col else ""
                event_category = EVENT_CATEGORY_MAP.get(raw_type, default_category)

                # Handle special cases
                if source_type == "entra_id":
                    event_category = "login"
                    raw_type = "Login"
                elif source_type == "email_log":
                    event_category = "email_send"
                    raw_type = "EmailSent"
                    # Check if personal email
                    domains = str(row_dict.get("RecipientDomains", ""))
                    if any(d in domains for d in PERSONAL_EMAIL_DOMAINS):
                        event_category = "email_forward"
                elif source_type == "cloud_upload":
                    is_personal = str(row_dict.get("IsPersonalAccount", "")).upper() in ("TRUE", "1")
                    svc = str(row_dict.get("CloudService", ""))
                    if is_personal:
                        if "Google" in svc:
                            row_dict["destination_type"] = "GoogleDrive"
                        elif "Dropbox" in svc:
                            row_dict["destination_type"] = "Dropbox"
                        elif "OneDrive" in svc or "Microsoft" in svc:
                            row_dict["destination_type"] = "PersonalOneDrive"

                # Build normalized fields
                fields: dict = {}
                for csv_col, db_col in mapping.items():
                    if db_col.startswith("_"):
                        continue
                    val = row_dict.get(csv_col)
                    if val is not None and not (isinstance(val, float) and pd.isna(val)):
                        fields[db_col] = val

                # Override destination_type from row_dict if set above
                if "destination_type" in row_dict:
                    fields["destination_type"] = row_dict["destination_type"]

                raw_json = json.dumps({k: str(v) for k, v in row_dict.items()})
                event_hash = hashlib.sha256(raw_json.encode()).hexdigest()

                event = RawEvent(
                    id=str(uuid.uuid4()),
                    ingestion_batch_id=batch_id,
                    original_event_id=str(fields.get("original_event_id", "")),
                    data_source_type=source_type,
                    user_id=user_id,
                    user_email=user_email,
                    user_display_name=str(fields.get("user_display_name", "")),
                    device_id=str(fields.get("device_id", "")) or None,
                    device_name=str(fields.get("device_name", "")) or None,
                    event_category=event_category,
                    event_type=raw_type or source_type,
                    severity_original=str(fields.get("severity_original", "")) or None,
                    event_timestamp=event_ts,
                    source_ip=str(fields.get("source_ip", "")) or None,
                    location_country=str(fields.get("location_country", "")) or None,
                    location_city=str(fields.get("location_city", "")) or None,
                    action_result=str(fields.get("action_result", "")) or None,
                    object_name=str(fields.get("object_name", "")) or None,
                    object_path=str(fields.get("object_path", "")) or None,
                    object_size_bytes=int(fields["object_size_bytes"]) if fields.get("object_size_bytes") else None,
                    object_count=int(fields["object_count"]) if fields.get("object_count") else None,
                    destination_type=str(fields.get("destination_type", "")) or None,
                    destination_detail=str(fields.get("destination_detail", "")) or None,
                    policy_name=str(fields.get("policy_name", "")) or None,
                    policy_rule=str(fields.get("policy_rule", "")) or None,
                    sensitivity_label=str(fields.get("sensitivity_label", "")) or None,
                    raw_data=raw_json,
                    event_hash=event_hash,
                )
                self.db.add(event)
                self.db.commit()
                success += 1
            except Exception as e:
                errors.append(f"Row error: {e}")
                self.db.rollback()
        return success, errors

    def _run_post_ingest_scoring(self, batch_id: str) -> tuple[int, int]:
        """After ingestion, score affected users and auto-create alerts/cases."""
        from app.services.risk_scoring import RiskScoringEngine
        from app.services.case_correlation import CaseCorrelationService
        from app.core.config import settings

        affected_user_ids = [
            r[0] for r in self.db.query(RawEvent.user_id)
            .filter(RawEvent.ingestion_batch_id == batch_id, RawEvent.user_id.isnot(None))
            .distinct().all()
        ]

        engine = RiskScoringEngine(self.db)
        corr = CaseCorrelationService(self.db)
        alerts_created = cases_created = 0

        for uid in affected_user_ids:
            try:
                result = engine.score_user(uid)
                if result.total_score >= settings.ALERT_AUTO_CREATE_THRESHOLD:
                    a = corr.create_alert_from_score(result)
                    if a:
                        alerts_created += 1
                if result.total_score >= settings.CASE_AUTO_CREATE_THRESHOLD:
                    c = corr.auto_create_case(result)
                    if c:
                        cases_created += 1
            except Exception:
                pass

        return alerts_created, cases_created
