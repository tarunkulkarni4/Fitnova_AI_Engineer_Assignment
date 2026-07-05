"""
Pydantic schemas for the read-only lookup endpoints.
"""
import uuid
from pydantic import BaseModel, Field


class OrganizationLookup(BaseModel):
    id: uuid.UUID
    name: str
    industry: str | None = None


class TeamLookup(BaseModel):
    id: uuid.UUID
    name: str
    organization_id: uuid.UUID
    organization_name: str


class AdvisorLookup(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    status: str
    team_id: uuid.UUID
    team_name: str


class IssueTaxonomyItem(BaseModel):
    category: str = Field(..., description="Raw category identifier")
    label: str = Field(..., description="Human-readable label")
    severity: str = Field(..., description="Fixed severity")
    absence_based: bool = Field(..., description="True for absence-based issue categories")
