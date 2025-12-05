"""increase_segment_column_sizes

Revision ID: increase_segment_columns_001
Revises: 3eb55c7d589f
Create Date: 2025-11-03 14:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'increase_segment_columns_001'
down_revision: Union[str, None] = '3eb55c7d589f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Increase column sizes for transcript_segments to accommodate longer device IDs."""
    
    # Increase google_meet_user_id from VARCHAR(100) to VARCHAR(500)
    op.alter_column(
        'transcript_segments',
        'google_meet_user_id',
        existing_type=sa.String(100),
        type_=sa.String(500),
        existing_nullable=False
    )
    
    # Increase speaker_username from VARCHAR(100) to VARCHAR(200)
    op.alter_column(
        'transcript_segments',
        'speaker_username',
        existing_type=sa.String(100),
        type_=sa.String(200),
        existing_nullable=False
    )


def downgrade() -> None:
    """Revert column sizes back to original."""
    
    # Revert google_meet_user_id back to VARCHAR(100)
    op.alter_column(
        'transcript_segments',
        'google_meet_user_id',
        existing_type=sa.String(500),
        type_=sa.String(100),
        existing_nullable=False
    )
    
    # Revert speaker_username back to VARCHAR(100)
    op.alter_column(
        'transcript_segments',
        'speaker_username',
        existing_type=sa.String(200),
        type_=sa.String(100),
        existing_nullable=False
    )

