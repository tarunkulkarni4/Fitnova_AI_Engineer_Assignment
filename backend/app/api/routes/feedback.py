from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.feedback import FeedbackType
from app.schemas import (
    ExportRecordItem,
    FeedbackCallReviewResponse,
    FeedbackResponseItem,
    ScoreCorrectionInput,
    SummaryCorrectionInput,
    TagAddInput,
    TagCorrectInput,
    TagRejectInput,
    TranscriptCorrectionInput,
)
from app.services.feedback_service import FeedbackService

router = APIRouter()


# ---------------------------------------------------------------------------
# 1. Score Correction
# ---------------------------------------------------------------------------

@router.post(
    "/feedback/{call_id}/score",
    response_model=FeedbackResponseItem,
    status_code=status.HTTP_201_CREATED,
    summary="Correct a call quality score dimension",
)
def correct_score(
    call_id: UUID,
    payload: ScoreCorrectionInput,
    db: Session = Depends(get_db),
) -> FeedbackResponseItem:
    fb = FeedbackService(db).correct_score(
        call_id=call_id,
        reviewer_name=payload.reviewer_name,
        dimension=payload.dimension,
        corrected_score=payload.corrected_score,
        comments=payload.comments,
    )
    # Re-fetch or parse logic inside history helper
    history = FeedbackService(db).get_feedback_history(call_id)
    # Find the one we just added by ID
    for item in history:
        if item["feedback_id"] == fb.id:
            return FeedbackResponseItem(**item)
    raise ValueError("Feedback not found after insert.")


# ---------------------------------------------------------------------------
# 2. Issue Tag Review
# ---------------------------------------------------------------------------

@router.post(
    "/feedback/{call_id}/tags/{issue_tag_id}/reject",
    response_model=FeedbackResponseItem,
    status_code=status.HTTP_201_CREATED,
    summary="Reject an AI issue tag",
)
def reject_tag(
    call_id: UUID,
    issue_tag_id: UUID,
    payload: TagRejectInput,
    db: Session = Depends(get_db),
) -> FeedbackResponseItem:
    fb = FeedbackService(db).reject_tag(
        call_id=call_id,
        issue_tag_id=issue_tag_id,
        reviewer_name=payload.reviewer_name,
        comments=payload.comments,
    )
    history = FeedbackService(db).get_feedback_history(call_id)
    for item in history:
        if item["feedback_id"] == fb.id:
            return FeedbackResponseItem(**item)
    raise ValueError("Feedback not found after insert.")


@router.post(
    "/feedback/{call_id}/tags/{issue_tag_id}/correct",
    response_model=FeedbackResponseItem,
    status_code=status.HTTP_201_CREATED,
    summary="Correct an AI issue tag evidence or details",
)
def correct_tag(
    call_id: UUID,
    issue_tag_id: UUID,
    payload: TagCorrectInput,
    db: Session = Depends(get_db),
) -> FeedbackResponseItem:
    fb = FeedbackService(db).correct_tag(
        call_id=call_id,
        issue_tag_id=issue_tag_id,
        reviewer_name=payload.reviewer_name,
        category=payload.category,
        timestamp=payload.timestamp,
        quote=payload.quote,
        reason=payload.reason,
        comments=payload.comments,
    )
    history = FeedbackService(db).get_feedback_history(call_id)
    for item in history:
        if item["feedback_id"] == fb.id:
            return FeedbackResponseItem(**item)
    raise ValueError("Feedback not found after insert.")


@router.post(
    "/feedback/{call_id}/tags/add",
    response_model=FeedbackResponseItem,
    status_code=status.HTTP_201_CREATED,
    summary="Manually add a missed issue tag",
)
def add_tag(
    call_id: UUID,
    payload: TagAddInput,
    db: Session = Depends(get_db),
) -> FeedbackResponseItem:
    fb = FeedbackService(db).add_tag(
        call_id=call_id,
        reviewer_name=payload.reviewer_name,
        category=payload.category,
        timestamp=payload.timestamp,
        quote=payload.quote,
        reason=payload.reason,
        comments=payload.comments,
    )
    history = FeedbackService(db).get_feedback_history(call_id)
    for item in history:
        if item["feedback_id"] == fb.id:
            return FeedbackResponseItem(**item)
    raise ValueError("Feedback not found after insert.")


# ---------------------------------------------------------------------------
# 3. Summary Correction
# ---------------------------------------------------------------------------

@router.post(
    "/feedback/{call_id}/summary",
    response_model=FeedbackResponseItem,
    status_code=status.HTTP_201_CREATED,
    summary="Correct a summary field or sentiment",
)
def correct_summary(
    call_id: UUID,
    payload: SummaryCorrectionInput,
    db: Session = Depends(get_db),
) -> FeedbackResponseItem:
    fb = FeedbackService(db).correct_summary(
        call_id=call_id,
        reviewer_name=payload.reviewer_name,
        field=payload.field,
        corrected_value=payload.corrected_value,
        comments=payload.comments,
    )
    history = FeedbackService(db).get_feedback_history(call_id)
    for item in history:
        if item["feedback_id"] == fb.id:
            return FeedbackResponseItem(**item)
    raise ValueError("Feedback not found after insert.")


# ---------------------------------------------------------------------------
# 4. Transcript Correction
# ---------------------------------------------------------------------------

@router.post(
    "/feedback/{call_id}/transcript",
    response_model=FeedbackResponseItem,
    status_code=status.HTTP_201_CREATED,
    summary="Correct transcript speaker or text segment",
)
def correct_transcript(
    call_id: UUID,
    payload: TranscriptCorrectionInput,
    db: Session = Depends(get_db),
) -> FeedbackResponseItem:
    fb = FeedbackService(db).correct_transcript(
        call_id=call_id,
        reviewer_name=payload.reviewer_name,
        segment_index=payload.segment_index,
        corrected_speaker=payload.corrected_speaker,
        corrected_text=payload.corrected_text,
        comments=payload.comments,
    )
    history = FeedbackService(db).get_feedback_history(call_id)
    for item in history:
        if item["feedback_id"] == fb.id:
            return FeedbackResponseItem(**item)
    raise ValueError("Feedback not found after insert.")


# ---------------------------------------------------------------------------
# 5. Effective Reviewed View
# ---------------------------------------------------------------------------

@router.get(
    "/feedback/{call_id}/reviewed",
    response_model=FeedbackCallReviewResponse,
    summary="Get composite effective call review view",
)
def get_effective_reviewed_view(
    call_id: UUID,
    db: Session = Depends(get_db),
) -> FeedbackCallReviewResponse:
    res = FeedbackService(db).get_effective_reviewed_view(call_id)
    return FeedbackCallReviewResponse(**res)


# ---------------------------------------------------------------------------
# 6. Feedback History
# ---------------------------------------------------------------------------

@router.get(
    "/feedback/{call_id}",
    response_model=list[FeedbackResponseItem],
    summary="Get feedback history for a call",
)
def get_feedback_history(
    call_id: UUID,
    db: Session = Depends(get_db),
) -> list[FeedbackResponseItem]:
    res = FeedbackService(db).get_feedback_history(call_id)
    return [FeedbackResponseItem(**item) for item in res]


# ---------------------------------------------------------------------------
# 7. Safe Feedback Export Dataset
# ---------------------------------------------------------------------------

@router.get(
    "/feedback/dataset/export",
    response_model=list[ExportRecordItem],
    summary="Export safe feedback dataset for future prompt/model improvements",
)
def export_feedback_dataset(
    feedback_type: FeedbackType | None = Query(None, description="Filter by feedback type"),
    team_id: UUID | None = Query(None, description="Limit feedback to calls from a specific team"),
    start_date: date | None = Query(None, description="Filter records on or after date"),
    end_date: date | None = Query(None, description="Filter records on or before date"),
    db: Session = Depends(get_db),
) -> list[ExportRecordItem]:
    res = FeedbackService(db).export_feedback_dataset(
        feedback_type=feedback_type,
        team_id=team_id,
        start_date=start_date,
        end_date=end_date,
    )
    return [ExportRecordItem(**item) for item in res]
