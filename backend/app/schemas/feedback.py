from datetime import datetime
from typing import Literal, Any
import uuid
from pydantic import BaseModel, Field, field_validator


class ScoreCorrectionInput(BaseModel):
    reviewer_name: str = Field(..., min_length=1, description="Name of the reviewer")
    dimension: Literal[
        "rapport",
        "needs_discovery",
        "product_knowledge",
        "objection_handling",
        "compliance",
        "trial_booking",
        "closing"
    ] = Field(..., description="The score dimension to correct")
    corrected_score: int = Field(..., ge=0, le=100, description="Corrected score value (0-100)")
    comments: str | None = Field(None, description="Optional explanation for the score correction")


class TagRejectInput(BaseModel):
    reviewer_name: str = Field(..., min_length=1)
    comments: str | None = None


class TagCorrectInput(BaseModel):
    reviewer_name: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)
    timestamp: float | None = None
    quote: str | None = None
    reason: str | None = None
    comments: str | None = None


class TagAddInput(BaseModel):
    reviewer_name: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)
    timestamp: float | None = None
    quote: str | None = None
    reason: str | None = None
    comments: str | None = None


class SummaryCorrectionInput(BaseModel):
    reviewer_name: str = Field(..., min_length=1)
    field: Literal[
        "executive_summary",
        "customer_goal",
        "objections",
        "recommended_next_step",
        "sentiment"
    ] = Field(..., description="The summary field to correct")
    corrected_value: str = Field(..., min_length=1, description="Corrected value text")
    comments: str | None = None


class TranscriptCorrectionInput(BaseModel):
    reviewer_name: str = Field(..., min_length=1)
    segment_index: int = Field(..., ge=0)
    corrected_speaker: str = Field(..., min_length=1, description="Advisor, Customer, Unknown, or existing SPEAKER_*")
    corrected_text: str = Field(..., min_length=1, description="Corrected segment text")
    comments: str | None = None


# ---------------------------------------------------------------------------
# Responses / Outputs
# ---------------------------------------------------------------------------

class FeedbackResponseItem(BaseModel):
    feedback_id: uuid.UUID
    feedback_type: str
    reviewer_name: str
    original_value: Any
    corrected_value: Any
    comments: str | None
    reviewed_at: datetime


class ScoreDetail(BaseModel):
    rapport: int | None = None
    needs_discovery: int | None = None
    product_knowledge: int | None = None
    objection_handling: int | None = None
    compliance: int | None = None
    trial_booking: int | None = None
    closing: int | None = None
    overall: int | None = None


class IssueTagDetail(BaseModel):
    id: uuid.UUID | str | None = None
    category: str
    severity: str
    timestamp: float | None = None
    speaker: str | None = None
    quote: str | None = None
    reason: str | None = None
    confidence: float | None = None


class SummaryDetail(BaseModel):
    executive_summary: str
    customer_goal: str | None = None
    objections: str | None = None
    recommended_next_step: str | None = None
    sentiment: str | None = None


class TranscriptSegment(BaseModel):
    speaker: str
    start_time: float
    end_time: float
    text: str
    confidence: float | None = None


class CallReviewResponse(BaseModel):
    call_id: uuid.UUID
    original_score: ScoreDetail | None = None
    effective_score: ScoreDetail | None = None
    original_issue_tags: list[IssueTagDetail] = Field(default_factory=list)
    effective_issue_tags: list[IssueTagDetail] = Field(default_factory=list)
    original_summary: SummaryDetail | None = None
    effective_summary: SummaryDetail | None = None
    original_transcript: list[TranscriptSegment] = Field(default_factory=list)
    effective_transcript: list[TranscriptSegment] = Field(default_factory=list)
    feedback_history: list[FeedbackResponseItem] = Field(default_factory=list)


class ExportRecordItem(BaseModel):
    call_id: uuid.UUID
    feedback_type: str
    original_value: Any
    corrected_value: Any
    comments: str | None
    reviewed_at: datetime
