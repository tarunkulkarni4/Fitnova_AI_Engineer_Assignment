from pydantic import BaseModel, Field
import uuid

class PIIRedactionStats(BaseModel):
    phone: int = Field(..., description="Number of phone numbers redacted")
    email: int = Field(..., description="Number of email addresses redacted")
    card: int = Field(..., description="Number of credit/debit card numbers redacted")
    aadhaar: int = Field(..., description="Number of Aadhaar numbers redacted")
    pan: int = Field(..., description="Number of PAN identifiers redacted")
    upi: int = Field(..., description="Number of UPI IDs redacted")
    total: int = Field(..., description="Total number of redacted items")

class PIIRedactionResponse(BaseModel):
    success: bool = Field(..., description="Indicates whether PII redaction succeeded")
    message: str = Field(..., description="Status description message")
    call_id: uuid.UUID = Field(..., description="Unique ID of the call")
    redactions: PIIRedactionStats = Field(..., description="PII redaction counts details")
    processing_status: str = Field(..., description="The updated status of call processing")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "PII redaction completed successfully.",
                "call_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
                "redactions": {
                    "phone": 2,
                    "email": 1,
                    "card": 0,
                    "aadhaar": 0,
                    "pan": 0,
                    "upi": 1,
                    "total": 4
                },
                "processing_status": "Ready For AI Analysis"
            }
        }
    }
