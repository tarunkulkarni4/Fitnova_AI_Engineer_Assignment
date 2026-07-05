"""Add ready for diarization status

Revision ID: 27aeb3d9b236
Revises: b6e7a240b9e8
Create Date: 2026-07-03 09:46:33.950146

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '27aeb3d9b236'
down_revision: Union[str, Sequence[str], None] = 'b6e7a240b9e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
