"""Add ready for transcript merge status

Revision ID: 02428b3efbb2
Revises: 27aeb3d9b236
Create Date: 2026-07-03 10:36:53.433512

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '02428b3efbb2'
down_revision: Union[str, Sequence[str], None] = '27aeb3d9b236'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
