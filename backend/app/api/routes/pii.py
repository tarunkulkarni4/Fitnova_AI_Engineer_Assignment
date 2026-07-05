from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.database.database import get_db
from app.schemas.pii import PIIRedactionResponse
from app.ai.pii.pii_redaction_service import PIIRedactionService

router = APIRouter()

@router.post(
    "/pii/{call_id}/redact",
    response_model=PIIRedactionResponse,
    status_code=status.HTTP_200_OK,
    summary="Redact PII from structured transcript",
    description="Loads the structured conversation JSON, replaces phone, email, card, Aadhaar, PAN, and UPI identifiers with placeholders, and outputs a redacted transcript JSON.",
    responses={
        200: {"model": PIIRedactionResponse, "description": "Transcript PII successfully redacted"},
        400: {"description": "Structured transcript JSON missing, corrupt, or has invalid schema"},
        404: {"description": "Call or job not found"},
        500: {"description": "Filesystem write failure, database error, or generic runtime failure"}
    }
)
async def redact_call_transcript(
    call_id: UUID,
    db: Session = Depends(get_db)
):
    service = PIIRedactionService(db)
    result = await service.redact_transcript(call_id)
    return PIIRedactionResponse(
        success=True,
        message="PII redaction completed successfully.",
        call_id=result["call_id"],
        redactions=result["redactions"],
        processing_status="Ready For AI Analysis"
    )
