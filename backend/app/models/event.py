from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Text, event as sa_event
from sqlalchemy.exc import StatementError
from app.core.database import Base


class DataSource(Base):
    __tablename__ = "data_sources"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    source_type = Column(String, nullable=False)
    description = Column(Text)
    field_mapping = Column(Text)
    is_active = Column(String, default="1")
    created_at = Column(DateTime, default=datetime.utcnow)


class IngestionBatch(Base):
    __tablename__ = "ingestion_batches"

    id = Column(String, primary_key=True)
    data_source_id = Column(String)
    data_source_type = Column(String, nullable=False)
    imported_by = Column(String, nullable=False)
    import_method = Column(String, nullable=False, default="csv_upload")
    filename = Column(String)
    file_hash = Column(String)
    record_count = Column(Integer)
    success_count = Column(Integer)
    error_count = Column(Integer)
    status = Column(String, nullable=False, default="processing")
    error_log = Column(Text)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)


class RawEvent(Base):
    __tablename__ = "raw_events"

    id = Column(String, primary_key=True)
    ingestion_batch_id = Column(String, nullable=False)
    original_event_id = Column(String)
    data_source_type = Column(String, nullable=False)
    user_id = Column(String)
    user_email = Column(String)
    user_display_name = Column(String)
    device_id = Column(String)
    device_name = Column(String)
    event_category = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    severity_original = Column(String)
    event_timestamp = Column(DateTime, nullable=False)
    event_timezone = Column(String, default="UTC")
    ingested_at = Column(DateTime, default=datetime.utcnow)
    source_ip = Column(String)
    destination_ip = Column(String)
    location_country = Column(String)
    location_city = Column(String)
    action = Column(String)
    action_result = Column(String)
    object_name = Column(String)
    object_path = Column(Text)
    object_size_bytes = Column(Integer)
    object_count = Column(Integer)
    destination_type = Column(String)
    destination_detail = Column(Text)
    policy_name = Column(String)
    policy_rule = Column(String)
    sensitivity_label = Column(String)
    raw_data = Column(Text)
    event_hash = Column(String, nullable=False)
