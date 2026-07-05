from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.database.database import get_db
from app.schemas.transcript_builder import TranscriptBuildResponse
from app.services.transcript_service import TranscriptService

router = APIRouter()

@router.post(
    "/transcripts/{call_id}/build",
    response_model=TranscriptBuildResponse,
    status_code=status.HTTP_200_OK,
    summary="Build structured conversation transcript",
    description="Loads all transcript segments, validates timestamps, chronologically merges identical speaker turns, and outputs a JSON artifact.",
    responses={
        200: {"model": TranscriptBuildResponse, "description": "Structured transcript successfully built"},
        400: {"description": "Invalid segment timestamps, negative values, or missing transcript entries"},
        404: {"description": "Call or job not found"},
        500: {"description": "Filesystem write failure, database error, or generic runtime failure"}
    }
)
async def build_call_transcript(
    call_id: UUID,
    db: Session = Depends(get_db)
):
    service = TranscriptService(db)
    result = await service.build_transcript(call_id)
    return TranscriptBuildResponse(
        success=True,
        message="Structured transcript built successfully.",
        call_id=result["call_id"],
        segments=result["segments_count"],
        processing_status="Ready For PII Redaction"
    )
