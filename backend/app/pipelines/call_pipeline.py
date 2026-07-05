"""
Call Processing Pipeline Orchestrator.

Connects all six completed processing stages into a single, resumable,
idempotent workflow.  The pipeline never duplicates any stage logic — it
exclusively calls each service's existing public method and manages the
durable state machine driven by the database.
"""
import uuid
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Coroutine, Any

from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models.call import Call, ProcessingStatus
from app.models.job import ProcessingJob
from app.models.score import CallScore

from app.services.audio_processing_service import AudioProcessingService
from app.ai.transcription.whisper_service import WhisperService
from app.ai.diarization.diarization_service import DiarizationService
from app.services.transcript_service import TranscriptService
from app.ai.pii.pii_redaction_service import PIIRedactionService
from app.ai.analysis.analysis_service import AnalysisService

CANCELLED_CALLS = set()


# ---------------------------------------------------------------------------
# Centralized Stage Registry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PipelineStage:
    """
    Immutable descriptor for a single pipeline stage.

    stage_name          - human-readable name; must match the value each
                          service writes to ProcessingJob.stage at the
                          start of its processing (this is the durable
                          resume anchor).
    expected_start_status - the Call.processing_status the call must carry
                            before this stage is eligible to run.
    success_status      - the Call.processing_status written after this
                          stage completes successfully.
    """
    stage_name: str
    expected_start_status: ProcessingStatus
    success_status: ProcessingStatus


# Ordered list — do NOT reorder.
STAGE_REGISTRY: list[PipelineStage] = [
    PipelineStage(
        stage_name="Audio Processing",
        expected_start_status=ProcessingStatus.UPLOADED,
        success_status=ProcessingStatus.READY_FOR_TRANSCRIPTION,
    ),
    PipelineStage(
        stage_name="Transcription",
        expected_start_status=ProcessingStatus.READY_FOR_TRANSCRIPTION,
        success_status=ProcessingStatus.READY_FOR_DIARIZATION,
    ),
    PipelineStage(
        stage_name="Speaker Diarization",
        expected_start_status=ProcessingStatus.READY_FOR_DIARIZATION,
        success_status=ProcessingStatus.READY_FOR_TRANSCRIPT_MERGE,
    ),
    PipelineStage(
        stage_name="Transcript Building",
        expected_start_status=ProcessingStatus.READY_FOR_TRANSCRIPT_MERGE,
        success_status=ProcessingStatus.READY_FOR_PII_REDACTION,
    ),
    PipelineStage(
        stage_name="PII Redaction",
        expected_start_status=ProcessingStatus.READY_FOR_PII_REDACTION,
        success_status=ProcessingStatus.READY_FOR_AI_ANALYSIS,
    ),
    PipelineStage(
        stage_name="AI Analysis",
        expected_start_status=ProcessingStatus.READY_FOR_AI_ANALYSIS,
        success_status=ProcessingStatus.COMPLETED,
    ),
]

# Index for O(1) look-up by stage_name
_STAGE_BY_NAME: dict[str, PipelineStage] = {s.stage_name: s for s in STAGE_REGISTRY}

# Ordered set of statuses that mean "this stage and all before it are done"
_STATUS_ORDER: list[ProcessingStatus] = [s.expected_start_status for s in STAGE_REGISTRY] + [ProcessingStatus.COMPLETED]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _status_index(status_val: ProcessingStatus) -> int:
    """Return the position of a ProcessingStatus in the pipeline order."""
    try:
        return _STATUS_ORDER.index(status_val)
    except ValueError:
        return -1


# ---------------------------------------------------------------------------
# CallPipeline
# ---------------------------------------------------------------------------

class CallPipeline:
    """
    Orchestrates the six-stage call processing pipeline.

    Responsibilities:
      - Atomic DB-level pipeline claim (prevents concurrent execution)
      - Resume from the exact failed stage recorded in ProcessingJob.stage
      - Skip already-completed stages
      - Stop immediately on any stage failure
      - Preserve all successful upstream work
      - Observability: log every stage with timing
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def run(self, call_id: uuid.UUID) -> dict:
        """
        Execute (or resume) the full pipeline for the given call.

        Returns a dict with keys:
            call_id, stages_completed, resumed_from, overall_score,
            issue_tags_count, already_completed
        """
        # 1. Validate call exists
        call = self.db.query(Call).filter(Call.id == call_id).first()
        if not call:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Call with ID {call_id} not found.",
            )

        # 2. Validate uploaded audio file is set
        if not call.audio_file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Call record has no uploaded audio file path.",
            )

        # 3. Short-circuit: already fully completed
        if call.processing_status == ProcessingStatus.COMPLETED:
            logger.info(f"Pipeline skipped — call {call_id} is already Completed.")
            score_row = self.db.query(CallScore).filter(CallScore.call_id == call_id).first()
            return {
                "call_id": call_id,
                "stages_completed": [s.stage_name for s in STAGE_REGISTRY],
                "resumed_from": None,
                "overall_score": score_row.overall_score if score_row else None,
                "issue_tags_count": None,
                "already_completed": True,
            }

        # 4. Atomic DB-level pipeline claim
        #    Uses a conditional UPDATE so two simultaneous requests cannot
        #    both proceed.  Only the request that writes the row "wins".
        result = self.db.execute(
            update(Call)
            .where(
                Call.id == call_id,
                Call.processing_status.notin_([
                    ProcessingStatus.PROCESSING,
                    ProcessingStatus.COMPLETED,
                ])
            )
            .values(processing_status=ProcessingStatus.PROCESSING)
            .execution_options(synchronize_session=False)
        )
        self.db.flush()

        if result.rowcount == 0:
            # Re-read to distinguish 409 vs. already-completed edge case
            current_status = (
                self.db.query(Call.processing_status)
                .filter(Call.id == call_id)
                .scalar()
            )
            if current_status == ProcessingStatus.COMPLETED:
                score_row = self.db.query(CallScore).filter(CallScore.call_id == call_id).first()
                return {
                    "call_id": call_id,
                    "stages_completed": [s.stage_name for s in STAGE_REGISTRY],
                    "resumed_from": None,
                    "overall_score": score_row.overall_score if score_row else None,
                    "issue_tags_count": None,
                    "already_completed": True,
                }
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Pipeline is already running for this call. Please wait and retry.",
            )

        # Refresh the in-memory object after the bulk UPDATE
        self.db.refresh(call)

        if call_id in CANCELLED_CALLS or call.processing_status == ProcessingStatus.CANCELLED:
            logger.info(f"Pipeline skipped — call {call_id} is Cancelled.")
            call.processing_status = ProcessingStatus.CANCELLED
            job = self.db.query(ProcessingJob).filter(ProcessingJob.call_id == call_id).first()
            if job:
                job.status = ProcessingStatus.CANCELLED
                job.error_message = "Processing cancelled by user."
            self.db.commit()
            return {
                "call_id": call_id,
                "stages_completed": [],
                "resumed_from": None,
                "overall_score": None,
                "issue_tags_count": None,
                "already_completed": False,
                "cancelled": True
            }

        # 5. Fetch ProcessingJob
        job = self.db.query(ProcessingJob).filter(ProcessingJob.call_id == call_id).first()
        if not job:
            # Roll back the Processing claim so the call doesn't get stuck
            call.processing_status = ProcessingStatus.FAILED
            self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ProcessingJob for Call {call_id} not found.",
            )

        # 6. Determine resume point
        resume_stage_name: str | None = None
        start_index: int = 0

        if call.processing_status == ProcessingStatus.FAILED or job.status == ProcessingStatus.FAILED:
            # Durable resume anchor: ProcessingJob.stage written at start of the failing stage
            failing_stage_name = job.stage
            if not failing_stage_name or failing_stage_name not in _STAGE_BY_NAME:
                # Cannot safely resume — fail with a clear internal error
                job.status = ProcessingStatus.FAILED
                job.error_message = (
                    f"Cannot resume pipeline: ProcessingJob.stage '{failing_stage_name}' "
                    "does not match any registered stage."
                )
                self.db.commit()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Pipeline resume failed: unrecognized stage recorded in job. Manual intervention required.",
                )

            resume_stage = _STAGE_BY_NAME[failing_stage_name]
            resume_stage_name = resume_stage.stage_name
            start_index = STAGE_REGISTRY.index(resume_stage)

            # Reset Call.processing_status to the stage's expected_start_status
            call.processing_status = resume_stage.expected_start_status
            self.db.commit()
            logger.info(
                f"Pipeline resuming for call {call_id} from stage '{resume_stage_name}' "
                f"(reset status to '{resume_stage.expected_start_status.value}')"
            )
        else:
            # Fresh run (or partial-run recovery from a non-Failed state).
            # call.processing_status has already been set to PROCESSING by the
            # atomic claim above, so we cannot use it directly.
            # job.status still reflects the state *before* the claim.
            pre_claim_status = job.status
            pre_claim_idx = _status_index(pre_claim_status)

            start_index = 0
            for idx, stage in enumerate(STAGE_REGISTRY):
                # A stage is already done if its expected_start_status comes
                # strictly before the pre-claim status in the pipeline order.
                if _status_index(stage.expected_start_status) < pre_claim_idx:
                    start_index = idx + 1
                else:
                    break

        logger.info(
            f"Pipeline starting for call {call_id} — "
            f"stages to run: {[s.stage_name for s in STAGE_REGISTRY[start_index:]]}"
        )

        # 7. Execute stages in order
        stages_completed: list[str] = [s.stage_name for s in STAGE_REGISTRY[:start_index]]
        analysis_result: dict | None = None

        for stage in STAGE_REGISTRY[start_index:]:
            # Check cooperative cancellation before starting stage
            self.db.refresh(call)
            if call_id in CANCELLED_CALLS or call.processing_status == ProcessingStatus.CANCELLED:
                logger.info(f"[Pipeline] [{call_id}] Cancellation detected before stage '{stage.stage_name}'. Stopping.")
                call.processing_status = ProcessingStatus.CANCELLED
                job.status = ProcessingStatus.CANCELLED
                job.error_message = "Processing cancelled by user."
                self.db.commit()
                break

            stage_start = time.perf_counter()
            logger.info(f"[Pipeline] [{call_id}] Starting stage: {stage.stage_name}")

            try:
                service_result = await self._invoke_stage(stage, call_id)
                duration_ms = (time.perf_counter() - stage_start) * 1000
                logger.info(
                    f"[Pipeline] [{call_id}] Stage '{stage.stage_name}' succeeded "
                    f"in {duration_ms:.1f}ms"
                )
                stages_completed.append(stage.stage_name)

                if stage.stage_name == "AI Analysis":
                    analysis_result = service_result

                # Check cooperative cancellation after stage finishes
                if call_id in CANCELLED_CALLS:
                    logger.info(f"[Pipeline] [{call_id}] Cancellation detected after stage '{stage.stage_name}' finished. Stopping.")
                    call.processing_status = ProcessingStatus.CANCELLED
                    job.status = ProcessingStatus.CANCELLED
                    job.error_message = "Processing cancelled by user."
                    self.db.commit()
                    break

            except HTTPException as exc:
                duration_ms = (time.perf_counter() - stage_start) * 1000
                logger.error(
                    f"[Pipeline] [{call_id}] Stage '{stage.stage_name}' FAILED "
                    f"in {duration_ms:.1f}ms — {exc.detail}"
                )
                # Increment retry_count so callers can track how many times
                # a stage has failed. Individual service _handle_failure methods
                # do not increment this — the orchestrator owns it.
                try:
                    job.retry_count = (job.retry_count or 0) + 1
                    self.db.commit()
                except Exception:
                    self.db.rollback()
                    logger.warning(f"[Pipeline] [{call_id}] Failed to increment retry_count.")
                # The service's _handle_failure has already updated the DB.
                # Propagate the HTTP error so the API layer can respond correctly.
                raise HTTPException(
                    status_code=exc.status_code,
                    detail=f"Pipeline failed at stage '{stage.stage_name}': {exc.detail}",
                )

        # 8. Collect final scores
        self.db.refresh(call)
        score_row = self.db.query(CallScore).filter(CallScore.call_id == call_id).first()
        overall_score: float | None = None
        issue_tags_count: int | None = None

        if analysis_result:
            overall_score = analysis_result.get("overall_score")
            issue_tags_count = analysis_result.get("issue_tags_count")
        elif score_row:
            overall_score = float(score_row.overall_score) if score_row.overall_score is not None else None

        logger.info(
            f"[Pipeline] [{call_id}] Pipeline COMPLETED — "
            f"stages={stages_completed}, score={overall_score}"
        )

        return {
            "call_id": call_id,
            "stages_completed": stages_completed,
            "resumed_from": resume_stage_name,
            "overall_score": overall_score,
            "issue_tags_count": issue_tags_count,
            "already_completed": False,
        }

    # ------------------------------------------------------------------
    # Stage invocation dispatch
    # ------------------------------------------------------------------

    async def _invoke_stage(self, stage: PipelineStage, call_id: uuid.UUID) -> dict:
        """
        Instantiate the correct service and call its primary method.
        All services accept only `call_id` and `db` — no logic is duplicated here.
        """
        if stage.stage_name == "Audio Processing":
            return await AudioProcessingService(self.db).process_audio(call_id)

        elif stage.stage_name == "Transcription":
            return await WhisperService(self.db).transcribe_call(call_id)

        elif stage.stage_name == "Speaker Diarization":
            return await DiarizationService(self.db).diarize_call(call_id)

        elif stage.stage_name == "Transcript Building":
            return await TranscriptService(self.db).build_transcript(call_id)

        elif stage.stage_name == "PII Redaction":
            return await PIIRedactionService(self.db).redact_transcript(call_id)

        elif stage.stage_name == "AI Analysis":
            return await AnalysisService(self.db).analyze_call(call_id)

        else:
            raise RuntimeError(f"No service binding for stage '{stage.stage_name}'")
