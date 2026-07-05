import os
import uuid
from loguru import logger
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.advisor import Advisor
from app.models.call import Call, ProcessingStatus
from app.models.job import ProcessingJob
from app.schemas.ingestion import CanonicalIngestionRequest

class IngestionService:
    """
    Service responsible for normalizing call ingestion across multiple sources
    (manual upload, telephony, dialer, CRM/file imports) and enforcing idempotency constraints.
    """
    def __init__(self, db: Session) -> None:
        self.db = db

    def ingest_call(self, request: CanonicalIngestionRequest) -> Call:
        # 1. Idempotency Check: only when source_reference is provided/non-null
        if request.source_reference:
            existing_call = (
                self.db.query(Call)
                .filter(
                    Call.source_type == request.source_type,
                    Call.source_reference == request.source_reference
                )
                .first()
            )
            if existing_call:
                logger.warning(
                    f"Idempotency hit! Call already ingested. "
                    f"source_type={request.source_type}, source_reference={request.source_reference}, "
                    f"Existing Call ID: {existing_call.id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Duplicate call detected: Call already ingested with this source and reference."
                )

        # 2. Validate Advisor Existence
        advisor = self.db.query(Advisor).filter(Advisor.id == request.advisor_id).first()
        if not advisor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Advisor with ID {request.advisor_id} not found."
            )

        # 3. Create Call record
        new_call = Call(
            advisor_id=request.advisor_id,
            source_type=request.source_type,
            source_reference=request.source_reference,
            audio_file=request.audio_file_path,
            processing_status=ProcessingStatus.UPLOADED
        )
        self.db.add(new_call)

        try:
            self.db.flush()  # Extract the call ID
            new_job = ProcessingJob(
                call_id=new_call.id,
                stage="Upload",
                status=ProcessingStatus.UPLOADED,
                retry_count=0
            )
            self.db.add(new_job)
            self.db.commit()
            self.db.refresh(new_call)
        except Exception as e:
            self.db.rollback()
            logger.exception(f"Failed to persist normalized ingested call: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database operation failed during ingestion."
            )

        logger.info(
            f"Successfully normalized and ingested call. Call ID: {new_call.id}, "
            f"Source: {new_call.source_type}, Reference: {new_call.source_reference}"
        )
        return new_call
