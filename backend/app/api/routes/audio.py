from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.database.database import get_db
from app.schemas.audio import ProcessAudioResponse
from app.services.audio_processing_service import AudioProcessingService

router = APIRouter()

@router.post(
    "/audio/process/{call_id}",
    response_model=ProcessAudioResponse,
    status_code=status.HTTP_200_OK,
    summary="Process call audio file",
    description="Loads the call audio, validates it, extracts metadata, converts it to 16kHz mono WAV, normalizes volume, and saves it.",
    responses={
        200: {"model": ProcessAudioResponse, "description": "Call audio successfully processed"},
        400: {"description": "Invalid format or corrupted file"},
        404: {"description": "Call or job not found"},
        500: {"description": "Filesystem write or database operation failure"}
    }
)
async def process_call_audio(
    call_id: UUID,
    db: Session = Depends(get_db)
):
    service = AudioProcessingService(db)
    metadata = await service.process_audio(call_id)
    return ProcessAudioResponse(
        success=True,
        message="Audio processed successfully.",
        metadata=metadata
    )
