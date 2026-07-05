from pydantic import BaseModel, Field
import uuid

class TranscriptSegmentResponse(BaseModel):
    speaker: str = Field(..., description="The speaker role (e.g. Advisor, Customer, SPEAKER_XX)")
    start_time: float = Field(..., description="The segment start offset in seconds")
    end_time: float = Field(..., description="The segment end offset in seconds")
    text: str = Field(..., description="The segment transcribed text")
    confidence: float | None = Field(None, description="The confidence score of the segment text")

    model_config = {
        "json_schema_extra": {
            "example": {
                "speaker": "Advisor",
                "start_time": 0.0,
                "end_time": 8.2,
                "text": "Welcome to FitNova coaching! My name is John.",
                "confidence": 0.94
            }
        }
    }

class StructuredTranscriptResponse(BaseModel):
    call_id: uuid.UUID = Field(..., description="Unique ID of the call")
    language: str | None = Field(None, description="The detected language code (e.g. 'en')")
    duration: int = Field(..., description="The call duration in seconds")
    segments: list[TranscriptSegmentResponse] = Field(..., description="Chronological list of speaker turns")

    model_config = {
        "json_schema_extra": {
            "example": {
                "call_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
                "language": "en",
                "duration": 312,
                "segments": [
                    {
                        "speaker": "Advisor",
                        "start_time": 0.0,
                        "end_time": 8.2,
                        "text": "Welcome to FitNova...",
                        "confidence": 0.94
                    }
                ]
            }
        }
    }

class TranscriptBuildResponse(BaseModel):
    success: bool = Field(..., description="Indicates whether structured transcript build succeeded")
    message: str = Field(..., description="Status description message")
    call_id: uuid.UUID = Field(..., description="Unique ID of the call")
    segments: int = Field(..., description="Number of merged speaker turns generated")
    processing_status: str = Field(..., description="The updated status of call processing")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "Structured transcript built successfully.",
                "call_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
                "segments": 24,
                "processing_status": "Ready For PII Redaction"
            }
        }
    }
