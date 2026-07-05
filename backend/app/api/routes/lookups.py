"""
Read-only lookup endpoints.

Provides lightweight id+name payloads for:
- Organization context selector
- Team context selector
- Advisor dropdown (upload form)
- Issue taxonomy (single source of truth from validators.py)

No mutations. No analytics aggregations.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from uuid import UUID

from app.database.database import get_db
from app.models.advisor import Advisor, AdvisorStatus
from app.models.organization import Organization
from app.models.team import Team
from app.schemas.lookups import AdvisorLookup, IssueTaxonomyItem, OrganizationLookup, TeamLookup
from app.ai.analysis.validators import ALLOWED_CATEGORIES, ABSENCE_TAGS, SEVERITY_MAP

router = APIRouter()

# Human-readable labels for each category (derived from category key)
def _category_to_label(category: str) -> str:
    return category.replace("_", " ").title()


# ---------------------------------------------------------------------------
# Organizations
# ---------------------------------------------------------------------------

@router.get(
    "/lookups/organizations",
    response_model=list[OrganizationLookup],
    summary="List all organizations",
    description="Returns id + name for all organizations. Used for context selector.",
)
def list_organizations(db: Session = Depends(get_db)) -> list[OrganizationLookup]:
    rows = db.query(Organization).order_by(Organization.name).all()
    return [OrganizationLookup(id=r.id, name=r.name, industry=r.industry) for r in rows]


# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------

@router.get(
    "/lookups/teams",
    response_model=list[TeamLookup],
    summary="List teams",
    description="Returns teams. Filter by organization_id to scope to a single org.",
)
def list_teams(
    organization_id: UUID | None = Query(None, description="Filter by organization"),
    db: Session = Depends(get_db),
) -> list[TeamLookup]:
    from sqlalchemy.orm import joinedload
    q = db.query(Team).options(joinedload(Team.organization)).order_by(Team.name)
    if organization_id is not None:
        q = q.filter(Team.organization_id == organization_id)
    rows = q.all()
    return [
        TeamLookup(
            id=r.id,
            name=r.name,
            organization_id=r.organization.id,
            organization_name=r.organization.name,
        )
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Advisors (lightweight — for dropdowns)
# ---------------------------------------------------------------------------

@router.get(
    "/lookups/advisors",
    response_model=list[AdvisorLookup],
    summary="List advisors (lightweight)",
    description=(
        "Returns id + name + status for advisor dropdowns and the upload form. "
        "For analytics use GET /dashboard/advisors instead."
    ),
)
def list_advisors(
    organization_id: UUID | None = Query(None),
    team_id: UUID | None = Query(None),
    search: str | None = Query(None),
    status: str | None = Query(None, description="Active or Inactive"),
    db: Session = Depends(get_db),
) -> list[AdvisorLookup]:
    from sqlalchemy.orm import joinedload
    from fastapi import HTTPException

    q = (
        db.query(Advisor)
        .options(joinedload(Advisor.team))
        .join(Team, Team.id == Advisor.team_id)
        .order_by(Advisor.name)
    )
    if organization_id is not None:
        q = q.filter(Team.organization_id == organization_id)
    if team_id is not None:
        q = q.filter(Advisor.team_id == team_id)
    if search:
        q = q.filter(Advisor.name.ilike(f"%{search.strip()}%"))
    if status:
        try:
            status_enum = AdvisorStatus(status)
            q = q.filter(Advisor.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid status '{status}'. Allowed: Active, Inactive.",
            )

    rows = q.all()
    return [
        AdvisorLookup(
            id=r.id,
            name=r.name,
            email=r.email,
            status=r.status.value,
            team_id=r.team.id,
            team_name=r.team.name,
        )
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Issue taxonomy
# ---------------------------------------------------------------------------

@router.get(
    "/lookups/issue-taxonomy",
    response_model=list[IssueTaxonomyItem],
    summary="Issue taxonomy",
    description=(
        "Returns all valid issue categories with their fixed severity and absence_based flag. "
        "Imports directly from the backend analysis validators — no manual duplication."
    ),
)
def get_issue_taxonomy() -> list[IssueTaxonomyItem]:
    items = []
    for category in sorted(ALLOWED_CATEGORIES):
        severity_enum = SEVERITY_MAP.get(category)
        severity_str = severity_enum.value if severity_enum else "Unknown"
        items.append(
            IssueTaxonomyItem(
                category=category,
                label=_category_to_label(category),
                severity=severity_str,
                absence_based=category in ABSENCE_TAGS,
            )
        )
    return items
