from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.database.database import get_db
from app.schemas.diarization import DiarizationResponse
from app.ai.diarization.diarization_service import DiarizationService

router = APIRouter()

@router.post(
    "/diarization/{call_id}",
    response_model=DiarizationResponse,
    status_code=status.HTTP_200_OK,
    summary="Diarize speakers in processed WAV file",
    description="Invokes speaker diarization, maps identified speaker turns to Advisor/Customer roles, and updates database transcript rows.",
    responses={
        200: {"model": DiarizationResponse, "description": "Call successfully diarized"},
        400: {"description": "Invalid format, missing processed file, missing transcripts, or mapping errors"},
        404: {"description": "Call or job not found"},
        500: {"description": "Diarization model load failure, database error, or generic runtime failure"}
    }
)
async def diarize_call_audio(
    call_id: UUID,
    db: Session = Depends(get_db)
):
    service = DiarizationService(db)
    result = await service.diarize_call(call_id)
    return DiarizationResponse(
        success=True,
        message="Speaker diarization completed successfully.",
        speakers_detected=result["speakers_detected"],
        processing_status="Ready For Transcript Merge"
    )
