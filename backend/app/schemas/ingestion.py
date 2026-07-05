from pydantic import BaseModel, Field
import uuid

class CanonicalIngestionRequest(BaseModel):
    advisor_id: uuid.UUID = Field(..., description="The unique ID of the advisor associated with this call")
    source_type: str = Field(..., description="Ingestion source: MANUAL_UPLOAD, TELEPHONY, DIALER, CRM_IMPORT, FILE_IMPORT")
    source_reference: str | None = Field(None, description="External reference/ID for idempotency check")
    audio_file_path: str = Field(..., description="Resolved local path to the audio file on disk")
