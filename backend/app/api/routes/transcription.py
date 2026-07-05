from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.database.database import get_db
from app.schemas.transcription import TranscriptionResponse
from app.ai.transcription.whisper_service import WhisperService

router = APIRouter()

@router.post(
    "/transcription/{call_id}",
    response_model=TranscriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Transcribe processed audio call",
    description="Invokes OpenAI Whisper model to transcribe the call's processed WAV file and stores transcription segments.",
    responses={
        200: {"model": TranscriptionResponse, "description": "Call successfully transcribed"},
        400: {"description": "Invalid format, missing processed file, or transcription errors"},
        404: {"description": "Call or job not found"},
        500: {"description": "Whisper engine load failure, database error, or generic runtime failure"}
    }
)
async def transcribe_call_audio(
    call_id: UUID,
    db: Session = Depends(get_db)
):
    service = WhisperService(db)
    result = await service.transcribe_call(call_id)
    return TranscriptionResponse(
        success=True,
        message="Transcription completed successfully.",
        language=result["language"],
        segments=result["segments_count"],
        processing_status="Ready For Diarization"
    )
