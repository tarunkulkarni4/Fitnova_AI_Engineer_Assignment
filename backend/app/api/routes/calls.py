from fastapi import APIRouter, Depends, File, Form, UploadFile, status, BackgroundTasks
from sqlalchemy.orm import Session
from uuid import UUID

from app.database.database import get_db
from app.schemas.call import UploadResponse
from app.services.upload_service import UploadService

router = APIRouter()

@router.post(
    "/calls/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload call audio",
    description="Ingests call audio files (.wav, .mp3, .m4a, max 50MB) and records database entry.",
    responses={
        201: {"model": UploadResponse, "description": "Call uploaded and metadata saved successfully"},
        400: {"description": "Format mismatch or invalid parameters"},
        404: {"description": "Advisor not found"},
        413: {"description": "File too large (exceeds 50MB)"},
        500: {"description": "Database or filesystem failure"}
    }
)
async def upload_call(
    audio: UploadFile = File(..., description="The audio file to upload (.wav, .mp3, .m4a)"),
    advisor_id: UUID = Form(..., description="The ID of the advisor handling this call"),
    source_type: str = Form(..., description="The source of call ingestion (e.g. Folder, Twilio, REST API)"),
    db: Session = Depends(get_db)
):
    service = UploadService(db)
    new_call = await service.upload_audio(
        audio=audio,
        advisor_id=advisor_id,
        source_type=source_type
    )
    return UploadResponse(
        success=True,
        message="Audio uploaded successfully.",
        call_id=new_call.id,
        processing_status=new_call.processing_status.value
    )

@router.post(
    "/ingestion/telephony",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest call from external telephony source (Adapter)",
    description="Proves source normalization by receiving an external call ID and audio reference."
)
async def ingest_telephony(
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(..., description="The audio file to upload"),
    advisor_id: UUID = Form(...),
    external_call_id: str = Form(...),
    vendor: str = Form(..., alias="source", description="Source/Vendor (e.g., FITNOVA_DIALER)"),
    db: Session = Depends(get_db)
):
    from fastapi import HTTPException
    from app.services.upload_service import UploadService
    from app.api.routes.pipeline import _run_pipeline_background

    service = UploadService(db)
    
    try:
        new_call = await service.upload_audio(
            audio=audio,
            advisor_id=advisor_id,
            source_type=vendor,
            source_reference=external_call_id
        )
    except HTTPException as e:
        if e.status_code == status.HTTP_409_CONFLICT:
            # Re-raise the idempotency error so the UI handles it properly
            raise e
        raise

    background_tasks.add_task(_run_pipeline_background, new_call.id)

    return UploadResponse(
        success=True,
        message="Call ingested via telephony adapter successfully.",
        call_id=new_call.id,
        processing_status=new_call.processing_status.value
    )
