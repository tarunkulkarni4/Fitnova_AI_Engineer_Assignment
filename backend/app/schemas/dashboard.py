"""
Pydantic schemas for the Dashboard Analytics API.

All aggregate float fields are rounded to 2 decimal places.
Null is returned when no analyzed calls exist (never divide-by-zero).
Raw ORM objects are never returned directly.
"""
import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared building blocks
# ---------------------------------------------------------------------------

class DimensionAverages(BaseModel):
    rapport: float | None = Field(None, description="Average rapport score (0-100)")
    needs_discovery: float | None = Field(None, description="Average needs discovery score")
    product_knowledge: float | None = Field(None, description="Average product knowledge score")
    objection_handling: float | None = Field(None, description="Average objection handling score")
    compliance: float | None = Field(None, description="Average compliance score")
    trial_booking: float | None = Field(None, description="Average trial booking score")
    closing: float | None = Field(None, description="Average closing score")


class IssueTagCount(BaseModel):
    category: str = Field(..., description="Issue category identifier")
    count: int = Field(..., description="Number of occurrences across calls in scope")
    severity: str = Field(..., description="Most common severity for this category")


class TeamPerformanceSummary(BaseModel):
    team_id: uuid.UUID
    team_name: str
    average_score: float | None = Field(None, description="Average overall score; null if no analyzed calls")
    completed_calls: int


class AdvisorPerformanceSummary(BaseModel):
    advisor_id: uuid.UUID
    advisor_name: str
    completed_calls: int
    average_score: float | None = Field(None, description="Average overall score; null if no analyzed calls")
    critical_issue_count: int = Field(0, description="Number of Critical-severity issue tags across their calls")


class ImprovementArea(BaseModel):
    dimension: str = Field(..., description="Human-readable dimension name")
    average_score: float | None = Field(None, description="Average score for this dimension")


class RecentCall(BaseModel):
    call_id: uuid.UUID
    upload_time: datetime
    duration: int | None = Field(None, description="Duration in seconds")
    overall_score: int | None = Field(None, description="AI overall score; null if not yet analyzed")
    issue_count: int = Field(0, description="Number of issue tags detected")
    processing_status: str


# ---------------------------------------------------------------------------
# Call Review sub-schemas
# ---------------------------------------------------------------------------

class TranscriptSegment(BaseModel):
    speaker: str
    start_time: float
    end_time: float
    text: str
    confidence: float | None = None


class CallScoreDetail(BaseModel):
    rapport: int | None = None
    needs_discovery: int | None = None
    product_knowledge: int | None = None
    objection_handling: int | None = None
    compliance: int | None = None
    trial_booking: int | None = None
    closing: int | None = None
    overall: int | None = None


class IssueTagDetail(BaseModel):
    category: str
    severity: str
    timestamp: float | None = None
    speaker: str | None = None
    quote: str | None = None
    reason: str | None = None
    confidence: float | None = None


class AISummaryDetail(BaseModel):
    executive_summary: str
    customer_goal: str | None = None
    objections: str | None = None
    recommended_next_step: str | None = None
    sentiment: str | None = None


class CallMetadata(BaseModel):
    call_id: uuid.UUID
    advisor_id: uuid.UUID
    advisor_name: str
    team_id: uuid.UUID
    team_name: str
    upload_time: datetime
    processing_status: str
    language: str | None = None
    duration: int | None = Field(None, description="Duration in seconds")
    source_type: str
    call_type: str = "SALES_CALL"
    is_sales_call: bool = True
    non_sales_reason: str | None = None
    classification_confidence: float | None = None


# ---------------------------------------------------------------------------
# Dashboard response schemas
# ---------------------------------------------------------------------------

class OrganizationDashboardResponse(BaseModel):
    organization_id: uuid.UUID
    organization_name: str
    total_teams: int
    total_advisors: int
    total_calls: int
    completed_calls: int
    failed_calls: int
    processing_calls: int
    average_quality_score: float | None = Field(None, description="Average overall score across completed analyzed calls")
    average_dimension_scores: DimensionAverages
    top_issue_tags: list[IssueTagCount] = Field(default_factory=list)
    team_performance: list[TeamPerformanceSummary] = Field(default_factory=list)


class TeamDashboardResponse(BaseModel):
    team_id: uuid.UUID
    team_name: str
    organization_id: uuid.UUID
    organization_name: str
    total_advisors: int
    total_calls: int
    completed_calls: int
    failed_calls: int
    processing_calls: int
    average_quality_score: float | None = None
    average_dimension_scores: DimensionAverages
    top_issue_tags: list[IssueTagCount] = Field(default_factory=list)
    advisor_leaderboard: list[AdvisorPerformanceSummary] = Field(
        default_factory=list,
        description="Advisors sorted by average_score DESC"
    )


class AdvisorDashboardResponse(BaseModel):
    advisor_id: uuid.UUID
    advisor_name: str
    advisor_email: str
    advisor_status: str
    team_id: uuid.UUID
    team_name: str
    organization_id: uuid.UUID
    organization_name: str
    total_calls: int
    completed_calls: int
    failed_calls: int
    processing_calls: int
    average_quality_score: float | None = None
    average_dimension_scores: DimensionAverages
    top_issue_tags: list[IssueTagCount] = Field(default_factory=list)
    recent_calls: list[RecentCall] = Field(default_factory=list, description="Last 10 calls, newest first")
    improvement_areas: list[ImprovementArea] = Field(
        default_factory=list,
        description="Bottom 3 scoring dimensions (deterministic, lowest average first)"
    )


class CallReviewResponse(BaseModel):
    metadata: CallMetadata
    score: CallScoreDetail | None = None
    issue_tags: list[IssueTagDetail] = Field(default_factory=list)
    summary: AISummaryDetail | None = None
    transcript_available: bool = Field(True, description="False when redacted transcript file is missing from disk")
    transcript: list[TranscriptSegment] = Field(
        default_factory=list,
        description="Segments from the redacted transcript artifact. Empty when transcript_available=false."
    )


# ---------------------------------------------------------------------------
# Call list
# ---------------------------------------------------------------------------

class CallListItem(BaseModel):
    call_id: uuid.UUID
    advisor_id: uuid.UUID
    advisor_name: str
    team_id: uuid.UUID
    team_name: str
    upload_time: datetime
    processing_status: str
    duration: int | None = None
    overall_score: int | None = None
    issue_count: int = 0
    call_type: str = "SALES_CALL"
    is_sales_call: bool = True
    non_sales_reason: str | None = None
    classification_confidence: float | None = None
    source_type: str
    source_reference: str | None = None


class PaginatedCallListResponse(BaseModel):
    items: list[CallListItem]
    page: int
    page_size: int
    total: int
    total_pages: int


# ---------------------------------------------------------------------------
# Advisor list (analytics, for /dashboard/advisors)
# ---------------------------------------------------------------------------

class AdvisorListItem(BaseModel):
    advisor_id: uuid.UUID
    advisor_name: str
    advisor_email: str
    advisor_status: str
    team_id: uuid.UUID
    team_name: str
    organization_id: uuid.UUID
    organization_name: str
    completed_calls: int = 0
    average_score: float | None = None
    critical_issue_count: int = 0


class PaginatedAdvisorListResponse(BaseModel):
    items: list[AdvisorListItem]
    page: int
    page_size: int
    total: int
    total_pages: int

