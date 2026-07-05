from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid

class CallInput(BaseModel):
    source_type: str = Field(..., description="The ingestion source name (e.g. Folder, Twilio, REST)")
    source_reference: str = Field(..., description="Unique reference identifier from the source (e.g. filename, twilio SID)")
    advisor_id: uuid.UUID = Field(..., description="The ID of the advisor handling the call")
    audio_path: str = Field(..., description="Path or location of the audio file")
    metadata: dict = Field(default_factory=dict, description="Generic dictionary for format-specific metadata")
    received_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="The datetime when the call was received/loaded"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "source_type": "Twilio",
                "source_reference": "RE123456789",
                "advisor_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
                "audio_path": "https://api.twilio.com/2010-04-01/Accounts/AC123/Recordings/RE123",
                "metadata": {"recording_duration": "120"},
                "received_at": "2026-07-03T04:00:00Z"
            }
        }
    }
