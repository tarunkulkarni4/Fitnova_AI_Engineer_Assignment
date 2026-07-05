import os
import uuid
from pathlib import Path
from loguru import logger
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session

from app.models.advisor import Advisor
from app.models.call import Call, ProcessingStatus
from app.models.job import ProcessingJob

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a"}
ALLOWED_MIME_TYPES = {
    "audio/wav", "audio/x-wav", "audio/wave", "audio/x-pn-wav",
    "audio/mpeg", "audio/mp3", "audio/x-mpeg-3",
    "audio/mp4", "audio/x-m4a", "audio/m4a"
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
CHUNK_SIZE = 1024 * 1024  # 1 MB

class UploadService:
    """
    Service responsible for handling call audio file uploads, executing checks,
    saving files safely, and recording database metadata.
    """
    def __init__(self, db: Session) -> None:
        self.db = db

    async def upload_audio(
        self,
        audio: UploadFile,
        advisor_id: uuid.UUID,
        source_type: str,
        source_reference: str | None = None
    ) -> Call:
        # 1. Validate File Extension
        file_extension = Path(audio.filename).suffix.lower() if audio.filename else ""
        if file_extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '{file_extension}'. Only .wav, .mp3, and .m4a are allowed."
            )

        # 2. Validate MIME Type
        mime_type = audio.content_type.lower() if audio.content_type else ""
        if mime_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid MIME type '{mime_type}'. Must be a valid audio stream."
            )

        # 3. Validate Advisor ID
        advisor = self.db.query(Advisor).filter(Advisor.id == advisor_id).first()
        if not advisor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Advisor with ID {advisor_id} not found."
            )

        # 4. Initialize storage path
        storage_dir = Path("app/storage/audio")
        try:
            storage_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.exception(f"Failed to create storage directory: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Storage initialization failed."
            )

        unique_filename = f"{uuid.uuid4().hex}{file_extension}"
        dest_path = storage_dir / unique_filename
        db_path = str(dest_path.resolve())

        # 5. Stream and validate file size on the fly
        total_size = 0
        try:
            with open(dest_path, "wb") as buffer:
                while chunk := await audio.read(CHUNK_SIZE):
                    total_size += len(chunk)
                    if total_size > MAX_FILE_SIZE:
                        buffer.close()
                        if dest_path.exists():
                            os.remove(dest_path)
                        raise HTTPException(
                            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                            detail="File size exceeds the maximum limit of 50 MB."
                        )
                    buffer.write(chunk)
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            if dest_path.exists():
                os.remove(dest_path)
            logger.exception(f"File write failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"File storage failed: {str(e)}"
            )

        # 6. Database Ingestion via IngestionService
        from app.services.ingestion_service import IngestionService
        from app.schemas.ingestion import CanonicalIngestionRequest

        req = CanonicalIngestionRequest(
            advisor_id=advisor_id,
            source_type=source_type,
            source_reference=source_reference,
            audio_file_path=db_path
        )

        try:
            ingestion_service = IngestionService(self.db)
            new_call = ingestion_service.ingest_call(req)
        except Exception as e:
            # Clean up stored file to avoid orphaned storage files
            if dest_path.exists():
                os.remove(dest_path)
            if isinstance(e, HTTPException):
                raise e
            logger.exception(f"Database ingestion transaction failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database operation failed. File upload discarded."
            )

        logger.info(f"Successfully processed audio upload. Call ID: {new_call.id}, File: {new_call.audio_file}")
        return new_call
