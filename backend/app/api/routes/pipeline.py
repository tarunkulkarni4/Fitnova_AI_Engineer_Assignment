"""
Pipeline API routes.

POST /pipeline/{call_id}/run
    Returns HTTP 202 immediately and schedules the pipeline as a
    FastAPI BackgroundTask.  Poll GET /pipeline/{call_id}/status for progress.

GET /pipeline/{call_id}/status
    Derives per-stage status from existing DB fields — safe to poll frequently.

Blocking work note:
    CallPipeline.run is declared async but internally calls CPU-blocking
    synchronous code (whisper.model.transcribe, pyannote Pipeline.__call__).
    Awaiting it directly on FastAPI's event loop freezes the server for the
    duration of transcription + diarization (several minutes on CPU).

    Fix: the BackgroundTask runs _run_pipeline_sync (a plain sync function)
    via asyncio.to_thread, which executes it in the default ThreadPoolExecutor.
    Inside that thread we call asyncio.run(pipeline.run(...)) so the async
    coroutine gets its own isolated event loop — completely separate from the
    main Uvicorn event loop, which stays free to serve status-poll requests.

    Session safety: each background run creates its own SessionLocal() and
    closes it in a finally block — the request-scoped session is never reused.

Architecture note (production):
    This BackgroundTask + thread approach is appropriate for this local
    take-home / demo deployment with a single Uvicorn worker.
    For production with multiple workers or long CPU jobs use a durable
    queue/worker such as Celery + Redis, RQ, or a managed job queue
    (AWS SQS + Lambda, GCP Cloud Tasks) so work survives worker restarts.
"""

import asyncio
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.orm import Session

from app.database.database import SessionLocal, get_db
from app.models.call import Call, ProcessingStatus
from app.models.job import ProcessingJob
from app.models.score import CallScore
from app.pipelines.call_pipeline import CallPipeline, STAGE_REGISTRY, CANCELLED_CALLS
from app.schemas.pipeline import (
    PipelineStartedResponse,
    PipelineStageStatus,
    PipelineStatusResponse,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Ordered stage names (single source of truth from the registry)
# ---------------------------------------------------------------------------

_ORDERED_STAGE_NAMES: list[str] = [s.stage_name for s in STAGE_REGISTRY]

# Map: ProcessingStatus → how many stages are fully Completed
_STAGES_COMPLETED_AT: dict[ProcessingStatus, int] = {
    ProcessingStatus.UPLOADED: 0,
    ProcessingStatus.QUEUED: 0,
    ProcessingStatus.READY_FOR_TRANSCRIPTION: 1,   # Audio Processing done
    ProcessingStatus.READY_FOR_DIARIZATION: 2,      # + Transcription done
    ProcessingStatus.READY_FOR_TRANSCRIPT_MERGE: 3, # + Diarization done
    ProcessingStatus.READY_FOR_PII_REDACTION: 4,    # + Transcript Building done
    ProcessingStatus.READY_FOR_AI_ANALYSIS: 5,      # + PII Redaction done
    ProcessingStatus.COMPLETED: 6,                  # all done
    ProcessingStatus.PROCESSING: 0,                 # resolved dynamically
    ProcessingStatus.FAILED: 0,                     # resolved dynamically
}


# ---------------------------------------------------------------------------
# Synchronous pipeline runner (called from a thread pool)
# ---------------------------------------------------------------------------

def _run_pipeline_sync(call_id: UUID) -> None:
    """
    Plain synchronous function that creates its own event loop and database
    session, runs the full CallPipeline, then tears both down.

    Why a sync function + asyncio.run?
    CallPipeline.run is async, but its stages call CPU-blocking code
    (whisper.model.transcribe, pyannote pipeline.__call__) without yielding
    to the event loop.  Running this coroutine directly on FastAPI's event
    loop would block ALL other requests (including status polls) for several
    minutes.  By executing it via asyncio.to_thread → asyncio.run, it gets
    its own isolated thread + event loop, leaving the main loop free.
    """
    logger.info(f"[BgTask] Thread execution started for call {call_id}")
    db = SessionLocal()
    try:
        logger.info(f"[BgTask] Instantiating CallPipeline and running...")
        asyncio.run(CallPipeline(db).run(call_id))
        logger.info(f"[BgTask] CallPipeline run completed successfully.")
    except HTTPException as exc:
        logger.warning(
            f"[BgTask] Pipeline for call {call_id} ended with "
            f"HTTP {exc.status_code}: {exc.detail}"
        )
    except Exception as exc:
        logger.exception(
            f"[BgTask] Unexpected error in pipeline for call {call_id}: {exc}"
        )
    finally:
        db.close()
        logger.info(f"[BgTask] DB session closed for call {call_id}")


async def _run_pipeline_background(call_id: UUID) -> None:
    """
    BackgroundTask entry point.
    Offloads _run_pipeline_sync to the default ThreadPoolExecutor via
    asyncio.to_thread so the FastAPI event loop is never blocked.
    """
    logger.info(f"[BgTask] BackgroundTask triggered for call {call_id}. Dispatching to thread pool...")
    await asyncio.to_thread(_run_pipeline_sync, call_id)
    logger.info(f"[BgTask] BackgroundTask dispatch completed for call {call_id}.")


# ---------------------------------------------------------------------------
# POST /pipeline/{call_id}/run  →  202 Accepted
# ---------------------------------------------------------------------------

@router.post(
    "/pipeline/{call_id}/run",
    response_model=PipelineStartedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start the full call processing pipeline (async)",
    description=(
        "Schedules all six processing stages as a background task and returns "
        "HTTP 202 immediately.  Poll GET /pipeline/{call_id}/status for live progress.  "
        "If the pipeline is already actively processing, returns 202 with "
        "pipeline_status='already_processing' and does NOT start a duplicate run.  "
        "If a previous run failed, the background task resumes from the failed stage."
    ),
    responses={
        202: {"model": PipelineStartedResponse, "description": "Pipeline accepted or already processing"},
        400: {"description": "Missing audio file or malformed call record"},
        404: {"description": "Call or ProcessingJob not found"},
    },
)
async def run_pipeline(
    call_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> PipelineStartedResponse:
    # --- Guard: call must exist ---
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call with ID {call_id} not found.",
        )

    if not call.audio_file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Call record has no uploaded audio file path.",
        )

    # --- Guard: duplicate execution prevention ---
    if call.processing_status == ProcessingStatus.PROCESSING:
        logger.info(f"[Route] Pipeline already processing for call {call_id} — rejecting duplicate start.")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pipeline is already actively running for this call. Poll /status for live updates.",
        )

    # --- Schedule background pipeline ---
    CANCELLED_CALLS.discard(call_id)
    background_tasks.add_task(_run_pipeline_background, call_id)
    logger.info(f"[Route] Pipeline background task scheduled for call {call_id}.")

    return PipelineStartedResponse(
        call_id=call_id,
        pipeline_status="accepted",
        message="Pipeline started. Poll GET /pipeline/{call_id}/status for live progress.",
    )


# ---------------------------------------------------------------------------
# GET /pipeline/{call_id}/status
# ---------------------------------------------------------------------------

@router.get(
    "/pipeline/{call_id}/status",
    response_model=PipelineStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get live pipeline stage status",
    description=(
        "Returns per-stage status derived from Call.processing_status and "
        "ProcessingJob fields.  Safe to poll frequently; read-only.  "
        "Stages before a failed stage are always shown as Completed.  "
        "Stages after a failed stage are always shown as Waiting.  "
        "A successful retry clears stale failure data from the status response."
    ),
    responses={
        200: {"model": PipelineStatusResponse},
        404: {"description": "Call or ProcessingJob not found"},
    },
)
async def get_pipeline_status(
    call_id: UUID,
    db: Session = Depends(get_db),
) -> PipelineStatusResponse:
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call with ID {call_id} not found.",
        )

    job = db.query(ProcessingJob).filter(ProcessingJob.call_id == call_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ProcessingJob for call {call_id} not found.",
        )

    ps = call.processing_status
    n_stages = len(_ORDERED_STAGE_NAMES)

    if ps == ProcessingStatus.CANCELLED or job.status == ProcessingStatus.CANCELLED:
        pipeline_status = "cancelled"
        cancelled_stage = job.stage or "Audio Processing"
        found_cancelled = False
        stages = []
        for name in _ORDERED_STAGE_NAMES:
            if name == cancelled_stage:
                stages.append(PipelineStageStatus(stage=name, status="Cancelled", error="Processing cancelled by user."))
                found_cancelled = True
            elif not found_cancelled:
                stages.append(PipelineStageStatus(stage=name, status="Completed", error=None))
            else:
                stages.append(PipelineStageStatus(stage=name, status="Waiting", error=None))
        
        return PipelineStatusResponse(
            call_id=call_id,
            pipeline_status=pipeline_status,
            current_stage=cancelled_stage,
            stages=stages,
            overall_score=None,
            issue_tags_count=None,
            error_message="Processing cancelled by user.",
        )

    if ps == ProcessingStatus.COMPLETED:
        # All stages Completed — ignore any stale job data
        pipeline_status = "completed"
        stages = [
            PipelineStageStatus(stage=name, status="Completed", error=None)
            for name in _ORDERED_STAGE_NAMES
        ]
        score_row = db.query(CallScore).filter(CallScore.call_id == call_id).first()
        overall_score = float(score_row.overall_score) if score_row and score_row.overall_score is not None else None
        return PipelineStatusResponse(
            call_id=call_id,
            pipeline_status=pipeline_status,
            current_stage=None,
            stages=stages,
            overall_score=overall_score,
            issue_tags_count=None,
            error_message=None,
        )

    if ps == ProcessingStatus.PROCESSING:
        # Actively running — only the current job.stage is Processing
        pipeline_status = "processing"
        current_stage = job.stage  # written by each service at start
        stages = []
        found_current = False
        for name in _ORDERED_STAGE_NAMES:
            if name == current_stage:
                stages.append(PipelineStageStatus(stage=name, status="Processing", error=None))
                found_current = True
            elif not found_current:
                stages.append(PipelineStageStatus(stage=name, status="Completed", error=None))
            else:
                stages.append(PipelineStageStatus(stage=name, status="Waiting", error=None))
        return PipelineStatusResponse(
            call_id=call_id,
            pipeline_status=pipeline_status,
            current_stage=current_stage,
            stages=stages,
            overall_score=None,
            issue_tags_count=None,
            error_message=None,
        )

    if ps == ProcessingStatus.FAILED or job.status == ProcessingStatus.FAILED:
        # Genuinely failed — derive which stages are Completed vs Failed vs Waiting
        pipeline_status = "failed"
        failed_stage = job.stage  # the service wrote this at the start of its run
        error_message = job.error_message
        stages = []
        found_failed = False
        for name in _ORDERED_STAGE_NAMES:
            if name == failed_stage:
                stages.append(PipelineStageStatus(stage=name, status="Failed", error=error_message))
                found_failed = True
            elif not found_failed:
                stages.append(PipelineStageStatus(stage=name, status="Completed", error=None))
            else:
                stages.append(PipelineStageStatus(stage=name, status="Waiting", error=None))
        return PipelineStatusResponse(
            call_id=call_id,
            pipeline_status=pipeline_status,
            current_stage=failed_stage,
            stages=stages,
            overall_score=None,
            issue_tags_count=None,
            error_message=error_message,
        )

    # All other statuses (UPLOADED, QUEUED, READY_FOR_*) indicate stages
    # completed up to the recorded checkpoint — pipeline hasn't started yet
    # or is between stages.
    n_completed = _STAGES_COMPLETED_AT.get(ps, 0)
    pipeline_status = "pending" if n_completed == 0 else "processing"
    stages = []
    for idx, name in enumerate(_ORDERED_STAGE_NAMES):
        if idx < n_completed:
            stages.append(PipelineStageStatus(stage=name, status="Completed", error=None))
        else:
            stages.append(PipelineStageStatus(stage=name, status="Waiting", error=None))

    return PipelineStatusResponse(
        call_id=call_id,
        pipeline_status=pipeline_status,
        current_stage=None,
        stages=stages,
        overall_score=None,
        issue_tags_count=None,
        error_message=None,
    )


@router.post(
    "/pipeline/{call_id}/cancel",
    status_code=status.HTTP_200_OK,
    summary="Cancel active call pipeline execution"
)
async def cancel_pipeline(
    call_id: UUID,
    db: Session = Depends(get_db)
):
    # Guard: call must exist
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call with ID {call_id} not found."
        )

    # Check current status
    if call.processing_status in [ProcessingStatus.COMPLETED, ProcessingStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel a call that is already {call.processing_status.value}."
        )

    # Flag in memory for cooperative cancellation in active loop
    CANCELLED_CALLS.add(call_id)

    # Update call status in database
    call.processing_status = ProcessingStatus.CANCELLED
    
    # Update job status in database
    job = db.query(ProcessingJob).filter(ProcessingJob.call_id == call_id).first()
    if job:
        job.status = ProcessingStatus.CANCELLED
        job.error_message = "Processing cancelled by user."

    db.commit()
    logger.info(f"[Route] Cancelled pipeline execution for call {call_id}.")
    return {"success": True, "message": "Pipeline cancelled successfully."}
