"""Add processed audio column

Revision ID: b6e7a240b9e8
Revises: adf9fe823186
Create Date: 2026-07-03 09:24:12.586301

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6e7a240b9e8'
down_revision: Union[str, Sequence[str], None] = 'adf9fe823186'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('call', sa.Column('processed_audio_file', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('call', 'processed_audio_file')
