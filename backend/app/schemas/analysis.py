from pydantic import BaseModel, Field
from typing import Literal
import uuid

class EvidenceItem(BaseModel):
    timestamp: float | None = Field(None, description="The start time offset of the segment containing the quote")
    quote: str | None = Field(None, description="The exact quote string from the redacted transcript")

class DimensionScore(BaseModel):
    score: int = Field(..., ge=0, le=100, description="Dimension score between 0 and 100")
    reason: str = Field(..., description="Justification explaining the score")
    evidence: list[EvidenceItem] = Field(default_factory=list, description="List of supporting quotes and timestamps")

class IssueTagResult(BaseModel):
    category: str = Field(..., description="The category identifier of the issue tag from allowlist")
    quote: str | None = Field(None, description="Quote from transcript or null for absence-based tags")
    timestamp: float | None = Field(None, description="Start offset in seconds or null for absence")
    speaker: str | None = Field(None, description="Speaker name or null for absence")
    reason: str = Field(..., description="Detailed explanation of the issue")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence score")

class AnalysisSummary(BaseModel):
    executive_summary: str = Field(..., description="High-level executive summary of the call")
    customer_goal: str | None = Field(None, description="Identified fitness goals of the customer")
    objections: str | None = Field(None, description="Objections raised by the customer")
    recommended_next_step: str | None = Field(None, description="Recommended next action items")
    sentiment: Literal["Positive", "Neutral", "Negative", "Mixed"] = Field(..., description="Customer sentiment classification")

class AnalysisResult(BaseModel):
    scores: dict[str, DimensionScore] = Field(..., description="Evaluated rubric dimension scores")
    issue_tags: list[IssueTagResult] = Field(default_factory=list, description="Detected issue tags list")
    summary: AnalysisSummary = Field(..., description="High level summary of conversation findings")

class AnalysisBuildResponse(BaseModel):
    success: bool = Field(..., description="Indicates whether AI analysis succeeded")
    message: str = Field(..., description="Status description message")
    call_id: uuid.UUID = Field(..., description="Unique ID of the call")
    overall_score: float = Field(..., description="Calculated weighted quality score")
    issue_tags_count: int = Field(..., description="Number of issue tags successfully validated and persisted")
    processing_status: str = Field(..., description="The updated status of call processing")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "Call analysis completed successfully.",
                "call_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
                "overall_score": 78.5,
                "issue_tags_count": 2,
                "processing_status": "Completed"
            }
        }
    }
