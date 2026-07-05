import uuid
from typing import Literal
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Legacy / existing schema (kept for any code that may reference it)
# ---------------------------------------------------------------------------

class PipelineStageResult(BaseModel):
    stage: str = Field(..., description="Stage name")
    status: Literal["completed", "skipped", "failed"] = Field(..., description="Outcome of this stage in the current run")
    duration_ms: float = Field(..., description="Wall-clock time taken by this stage in milliseconds")
    error: str | None = Field(None, description="Sanitized error message if the stage failed")


class PipelineResponse(BaseModel):
    success: bool = Field(..., description="Whether the pipeline completed successfully")
    message: str = Field(..., description="Human-readable result message")
    call_id: uuid.UUID = Field(..., description="Call identifier")
    stages_completed: list[str] = Field(default_factory=list, description="Ordered list of stage names that reached success state")
    resumed_from: str | None = Field(None, description="Stage name from which execution resumed; null on clean first run")
    overall_score: float | None = Field(None, description="Weighted quality score from AI Analysis (present when Completed)")
    issue_tags_count: int | None = Field(None, description="Number of validated issue tags (present when Completed)")
    processing_status: str = Field(..., description="Final call processing status")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "Call processing pipeline completed successfully.",
                "call_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
                "stages_completed": [
                    "Audio Processing",
                    "Transcription",
                    "Speaker Diarization",
                    "Transcript Building",
                    "PII Redaction",
                    "AI Analysis"
                ],
                "resumed_from": None,
                "overall_score": 82.5,
                "issue_tags_count": 3,
                "processing_status": "Completed"
            }
        }
    }


# ---------------------------------------------------------------------------
# Async pipeline — new schemas (202 + status polling)
# ---------------------------------------------------------------------------

class PipelineStartedResponse(BaseModel):
    """
    Returned immediately (HTTP 202) when a pipeline run is accepted.
    The pipeline executes asynchronously in a FastAPI BackgroundTask.

    NOTE (architecture): BackgroundTasks is appropriate for this local
    take-home / demo deployment where a single Uvicorn worker is
    sufficient.  Production deployments with multiple workers or
    long-running CPU jobs should use a durable queue/worker such as
    Celery + Redis or a managed job queue (e.g. Cloud Tasks, SQS) so
    that work survives worker restarts.
    """
    call_id: uuid.UUID = Field(..., description="Call identifier")
    pipeline_status: str = Field(..., description="'accepted' or 'already_processing'")
    message: str = Field(..., description="Human-readable status message")


class PipelineStageStatus(BaseModel):
    """Status of a single pipeline stage as seen at poll time."""
    stage: str = Field(..., description="Stage name")
    status: Literal["Waiting", "Processing", "Completed", "Failed", "Cancelled"] = Field(
        ..., description="Current status of the stage"
    )
    error: str | None = Field(None, description="Error message — set only on the actually failed stage")


class PipelineStatusResponse(BaseModel):
    """
    Full pipeline status returned by GET /pipeline/{call_id}/status.
    Derived exclusively from Call.processing_status + ProcessingJob fields
    — no additional DB tables required.
    """
    call_id: uuid.UUID = Field(..., description="Call identifier")
    pipeline_status: Literal["pending", "processing", "completed", "failed", "cancelled"] = Field(
        ..., description="Overall pipeline status"
    )
    current_stage: str | None = Field(None, description="Stage currently executing, if any")
    stages: list[PipelineStageStatus] = Field(..., description="Per-stage status list in execution order")
    overall_score: float | None = Field(None, description="Final weighted score when completed")
    issue_tags_count: int | None = Field(None, description="Number of issue tags when completed")
    error_message: str | None = Field(None, description="Error from the failed stage, if applicable")
