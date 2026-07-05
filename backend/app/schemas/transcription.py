from pydantic import BaseModel, Field

class TranscriptionResponse(BaseModel):
    success: bool = Field(..., description="Indicates whether transcription succeeded")
    message: str = Field(..., description="Status description message")
    language: str = Field(..., description="The detected language of the call (e.g. 'en')")
    segments: int = Field(..., description="Number of transcription segments generated")
    processing_status: str = Field(..., description="The updated status of call processing")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "Transcription completed successfully.",
                "language": "en",
                "segments": 42,
                "processing_status": "Ready For Diarization"
            }
        }
    }
