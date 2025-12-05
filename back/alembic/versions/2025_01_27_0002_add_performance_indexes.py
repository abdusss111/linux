"""Add performance indexes for meetings endpoint

Revision ID: 2025_01_27_0002_add_performance_indexes
Revises: 2025_08_23_1248-cbb40db1ed4c_new
Create Date: 2025-01-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'perf_indexes_001'
down_revision = 'cbb40db1ed4c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add composite index for meetings (user_id, created_at) for efficient pagination
    op.create_index(
        'idx_meetings_user_created', 
        'meetings', 
        ['user_id', 'created_at'], 
        unique=False
    )
    
    # Add composite index for segments (session_id, speaker_username) for speaker aggregation
    op.create_index(
        'idx_segments_session_speaker', 
        'transcript_segments', 
        ['session_id', 'speaker_username'], 
        unique=False
    )
    
    # Add index on segments.session_id for faster joins
    op.create_index(
        'idx_segments_session_id', 
        'transcript_segments', 
        ['session_id'], 
        unique=False
    )
    
    # Add index on meetings.created_at for ordering (if not already exists)
    op.create_index(
        'idx_meetings_created_at', 
        'meetings', 
        ['created_at'], 
        unique=False
    )


def downgrade() -> None:
    # Drop indexes in reverse order
    op.drop_index('idx_meetings_created_at', table_name='meetings')
    op.drop_index('idx_segments_session_id', table_name='transcript_segments')
    op.drop_index('idx_segments_session_speaker', table_name='transcript_segments')
    op.drop_index('idx_meetings_user_created', table_name='meetings')
