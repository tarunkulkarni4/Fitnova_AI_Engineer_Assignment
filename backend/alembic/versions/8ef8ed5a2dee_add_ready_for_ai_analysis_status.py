"""Add ready for ai analysis status

Revision ID: 8ef8ed5a2dee
Revises: 38a02c389f05
Create Date: 2026-07-03 11:02:29.815246

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8ef8ed5a2dee'
down_revision: Union[str, Sequence[str], None] = '38a02c389f05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
