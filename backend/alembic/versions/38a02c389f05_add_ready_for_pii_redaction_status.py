"""Add ready for pii redaction status

Revision ID: 38a02c389f05
Revises: 02428b3efbb2
Create Date: 2026-07-03 10:48:18.040370

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '38a02c389f05'
down_revision: Union[str, Sequence[str], None] = '02428b3efbb2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
