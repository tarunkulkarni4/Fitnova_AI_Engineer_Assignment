"""Add dashboard performance indexes on advisor.team_id and team.organization_id.

Revision ID: c3d1e7f8a902
Revises: 8ef8ed5a2dee
Create Date: 2026-07-03 06:25:00.000000
"""
from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c3d1e7f8a902'
down_revision: Union[str, Sequence[str], None] = '8ef8ed5a2dee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add indexes needed by dashboard aggregation queries."""
    op.create_index('ix_advisor_team_id', 'advisor', ['team_id'], unique=False)
    op.create_index('ix_team_organization_id', 'team', ['organization_id'], unique=False)


def downgrade() -> None:
    """Remove dashboard indexes."""
    op.drop_index('ix_team_organization_id', table_name='team')
    op.drop_index('ix_advisor_team_id', table_name='advisor')
