from pydantic import BaseModel, Field

class DiarizationResponse(BaseModel):
    success: bool = Field(..., description="Indicates whether speaker diarization succeeded")
    message: str = Field(..., description="Status description message")
    speakers_detected: int = Field(..., description="Number of unique speakers identified in the audio")
    processing_status: str = Field(..., description="The updated status of call processing")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "Speaker diarization completed successfully.",
                "speakers_detected": 2,
                "processing_status": "Ready For Transcript Merge"
            }
        }
    }
