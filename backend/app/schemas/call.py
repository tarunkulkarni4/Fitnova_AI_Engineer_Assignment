from pydantic import BaseModel, Field
import uuid

class UploadResponse(BaseModel):
    success: bool = Field(..., description="Indicates whether the upload succeeded")
    message: str = Field(..., description="Informative status message")
    call_id: uuid.UUID = Field(..., description="The unique ID of the generated call record")
    processing_status: str = Field(..., description="The initial status of call processing")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "Audio uploaded successfully.",
                "call_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
                "processing_status": "Uploaded"
            }
        }
    }
