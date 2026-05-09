import hashlib
import io
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.core.config import settings
from app.schemas.common import StandardResponse, PaginatedResponse
from app.services.ingestion import IngestionService, IngestionResult
from app.middleware.audit import write_audit_log
from app.models.event import IngestionBatch

router = APIRouter(prefix="/ingest", tags=["Ingestion"])


class BatchSummary(BaseModel):
    id: str
    data_source_type: str
    filename: Optional[str]
    status: str
    record_count: Optional[int]
    success_count: Optional[int]
    error_count: Optional[int]
    imported_by: str
    started_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


@router.post("/csv", response_model=StandardResponse[IngestionResult])
async def ingest_csv(
    file: UploadFile = File(...),
    source_type: str = Form(...),
    analyst: str = Form(default=settings.DEFAULT_ANALYST),
    db: Session = Depends(get_db),
):
    content = await file.read()
    if len(content) > settings.MAX_CSV_SIZE_MB * 1_048_576:
        raise HTTPException(413, f"File exceeds {settings.MAX_CSV_SIZE_MB}MB limit")

    file_hash = hashlib.sha256(content).hexdigest()
    service = IngestionService(db)
    result = await service.ingest_csv(
        content=io.BytesIO(content),
        source_type=source_type,
        filename=file.filename,
        file_hash=file_hash,
        imported_by=analyst,
    )
    write_audit_log(
        db, actor=analyst, action="data.import.complete",
        resource_type="ingestion_batch", resource_id=result.batch_id,
        details={"source_type": source_type, "success": result.success_count},
    )
    return StandardResponse(success=True, data=result)


@router.get("/batches", response_model=PaginatedResponse[BatchSummary])
def list_batches(
    page: int = 1, page_size: int = 20,
    source_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(IngestionBatch)
    if source_type:
        q = q.filter(IngestionBatch.data_source_type == source_type)
    total = q.count()
    items = q.order_by(IngestionBatch.started_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    return PaginatedResponse(
        items=items, total=total, page=page,
        page_size=page_size, has_next=total > page * page_size,
    )
