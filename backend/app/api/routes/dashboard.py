from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.call import ProcessingStatus
from app.models.issue import IssueSeverity
from app.schemas.dashboard import (
    AdvisorDashboardResponse,
    CallReviewResponse,
    OrganizationDashboardResponse,
    PaginatedAdvisorListResponse,
    PaginatedCallListResponse,
    TeamDashboardResponse,
)
from app.services.dashboard_service import DashboardService

router = APIRouter()



# ---------------------------------------------------------------------------
# Shared date-range dependency
# ---------------------------------------------------------------------------

def _validate_dates(
    start_date: date | None = Query(None, description="Filter calls on or after this date (YYYY-MM-DD)"),
    end_date: date | None = Query(None, description="Filter calls on or before this date (YYYY-MM-DD)"),
) -> tuple[date | None, date | None]:
    from fastapi import HTTPException
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be on or before end_date.",
        )
    return start_date, end_date


def _validate_scores(
    min_score: int | None = Query(None, ge=0, le=100, description="Minimum overall score (0-100)"),
    max_score: int | None = Query(None, ge=0, le=100, description="Maximum overall score (0-100)"),
) -> tuple[int | None, int | None]:
    from fastapi import HTTPException
    if min_score is not None and max_score is not None and min_score > max_score:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min_score must be less than or equal to max_score.",
        )
    return min_score, max_score


# ---------------------------------------------------------------------------
# 1. Organization Dashboard
# ---------------------------------------------------------------------------

@router.get(
    "/dashboard/org/{organization_id}",
    response_model=OrganizationDashboardResponse,
    summary="Organization-level dashboard",
    description=(
        "Returns org-wide call volumes, average quality scores, dimension breakdowns, "
        "top issue categories, and per-team performance summaries. "
        "Only completed calls with AI scores are included in quality averages."
    ),
)
def get_org_dashboard(
    organization_id: UUID,
    team_id: UUID | None = Query(None),
    dates: tuple[date | None, date | None] = Depends(_validate_dates),
    db: Session = Depends(get_db),
) -> OrganizationDashboardResponse:
    start_date, end_date = dates
    return DashboardService(db).get_org_dashboard(
        organization_id=organization_id,
        team_id=team_id,
        start_date=start_date,
        end_date=end_date,
    )


# ---------------------------------------------------------------------------
# 2. Team Dashboard
# ---------------------------------------------------------------------------

@router.get(
    "/dashboard/team/{team_id}",
    response_model=TeamDashboardResponse,
    summary="Team-level dashboard",
    description=(
        "Returns team call volumes, quality averages, dimension breakdowns, "
        "top issue categories, and an advisor leaderboard sorted by average score DESC."
    ),
)
def get_team_dashboard(
    team_id: UUID,
    dates: tuple[date | None, date | None] = Depends(_validate_dates),
    db: Session = Depends(get_db),
) -> TeamDashboardResponse:
    start_date, end_date = dates
    return DashboardService(db).get_team_dashboard(team_id, start_date, end_date)


# ---------------------------------------------------------------------------
# 3. Advisor Dashboard
# ---------------------------------------------------------------------------

@router.get(
    "/dashboard/advisor/{advisor_id}",
    response_model=AdvisorDashboardResponse,
    summary="Advisor personal dashboard",
    description=(
        "Returns advisor call history, quality scores, dimension breakdowns, "
        "top issues, the 10 most recent calls, and the 3 lowest-scoring improvement areas. "
        "Improvement areas are computed deterministically from stored scores — no LLM."
    ),
)
def get_advisor_dashboard(
    advisor_id: UUID,
    dates: tuple[date | None, date | None] = Depends(_validate_dates),
    db: Session = Depends(get_db),
) -> AdvisorDashboardResponse:
    start_date, end_date = dates
    return DashboardService(db).get_advisor_dashboard(advisor_id, start_date, end_date)


# ---------------------------------------------------------------------------
# 4. Call Review
# ---------------------------------------------------------------------------

@router.get(
    "/dashboard/calls/{call_id}",
    response_model=CallReviewResponse,
    summary="Full call review",
    description=(
        "Returns complete intelligence for a single call: metadata, AI scores, issue tags, "
        "AI summary, and the REDACTED transcript. "
        "If the redacted transcript file is missing, transcript_available=false is returned "
        "and the endpoint does not fail."
    ),
)
def get_call_review(
    call_id: UUID,
    db: Session = Depends(get_db),
) -> CallReviewResponse:
    return DashboardService(db).get_call_review(call_id)


# ---------------------------------------------------------------------------
# 5. Paginated / Filtered Call List
# ---------------------------------------------------------------------------

@router.get(
    "/dashboard/calls",
    response_model=PaginatedCallListResponse,
    summary="Paginated and filtered call list",
    description=(
        "Returns a paginated list of calls with optional filters. "
        "Issue-related filters (severity, issue_category) use EXISTS subqueries "
        "to avoid row duplication and ensure correct pagination totals."
    ),
)
def get_call_list(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page (max 100)"),
    organization_id: UUID | None = Query(None),
    team_id: UUID | None = Query(None),
    advisor_id: UUID | None = Query(None),
    processing_status: ProcessingStatus | None = Query(
        None,
        description="Filter by processing status. Invalid values return HTTP 422."
    ),
    severity: IssueSeverity | None = Query(
        None,
        description="Return only calls that have at least one issue tag of this severity."
    ),
    issue_category: str | None = Query(
        None,
        description="Return only calls that have at least one issue tag with this category."
    ),
    has_source_reference: bool | None = Query(
        None,
        description="Filter calls by whether they have an external source_reference."
    ),
    sort: Literal["newest", "oldest", "highest_score", "lowest_score"] = Query(
        "newest",
        description="Sort order."
    ),
    scores: tuple[int | None, int | None] = Depends(_validate_scores),
    dates: tuple[date | None, date | None] = Depends(_validate_dates),
    db: Session = Depends(get_db),
) -> PaginatedCallListResponse:
    min_score, max_score = scores
    start_date, end_date = dates
    return DashboardService(db).get_call_list(
        page=page,
        page_size=page_size,
        organization_id=organization_id,
        team_id=team_id,
        advisor_id=advisor_id,
        processing_status=processing_status,
        min_score=min_score,
        max_score=max_score,
        severity=severity,
        issue_category=issue_category,
        start_date=start_date,
        end_date=end_date,
        has_source_reference=has_source_reference,
        sort=sort,
    )


# ---------------------------------------------------------------------------
# 6. Advisor List (analytics)
# ---------------------------------------------------------------------------

@router.get(
    "/dashboard/advisors",
    response_model=PaginatedAdvisorListResponse,
    summary="Paginated advisor analytics list",
    description=(
        "Returns a paginated list of advisors with analytics: completed calls, "
        "average score, and critical issue count. "
        "Filters: organization_id, team_id, search (name), status, page, page_size. "
        "Uses batch GROUP BY queries — no N+1."
    ),
)
def get_advisor_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    organization_id: UUID | None = Query(None),
    team_id: UUID | None = Query(None),
    search: str | None = Query(None, description="Case-insensitive name search"),
    advisor_status: str | None = Query(None, alias="status", description="Active or Inactive"),
    db: Session = Depends(get_db),
) -> PaginatedAdvisorListResponse:
    return DashboardService(db).get_advisor_list(
        organization_id=organization_id,
        team_id=team_id,
        search=search,
        advisor_status=advisor_status,
        page=page,
        page_size=page_size,
    )
