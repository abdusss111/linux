"""add_analytics_performance_indexes

Revision ID: 3eb55c7d589f
Revises: 0f8909d899c6
Create Date: 2025-10-13 13:30:55.683178

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3eb55c7d589f'
down_revision: Union[str, None] = '0f8909d899c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add performance indexes for analytics endpoints."""
    
    # Use raw SQL with IF NOT EXISTS to avoid conflicts
    connection = op.get_bind()
    
    # Users table indexes for analytics
    connection.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_users_created_at_analytics 
        ON users(created_at)
    """))
    
    # Chat messages table indexes
    connection.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id 
        ON chat_messages(session_id)
    """))
    
    # Transcript segments table indexes for analytics
    connection.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_transcript_segments_timestamp 
        ON transcript_segments(timestamp)
    """))
    
    # Composite index for transcript segments (session_id, timestamp) for duration calculations
    connection.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_transcript_segments_session_timestamp 
        ON transcript_segments(session_id, timestamp)
    """))
    
    # Meeting participants table indexes (check if table exists first)
    try:
        connection.execute(sa.text("""
            CREATE INDEX IF NOT EXISTS idx_meeting_participants_session_id 
            ON meeting_participants(session_id)
        """))
    except Exception:
        # Table might not exist or have different structure
        pass
    
    try:
        connection.execute(sa.text("""
            CREATE INDEX IF NOT EXISTS idx_meeting_participants_user_id 
            ON meeting_participants(user_id)
        """))
    except Exception:
        # Table might not exist or have different structure
        pass
    
    # Additional composite indexes for common analytics queries
    connection.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_meetings_created_at_user_id 
        ON meetings(created_at, user_id)
    """))
    
    # Index for transcript segments google_meet_user_id for participant counting
    connection.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_transcript_segments_google_meet_user_id 
        ON transcript_segments(google_meet_user_id)
    """))


def downgrade() -> None:
    """Remove analytics performance indexes."""
    
    # Use raw SQL to drop indexes safely
    connection = op.get_bind()
    
    # Drop indexes in reverse order (if they exist)
    indexes_to_drop = [
        'idx_transcript_segments_google_meet_user_id',
        'idx_meetings_created_at_user_id', 
        'idx_meeting_participants_user_id',
        'idx_meeting_participants_session_id',
        'idx_transcript_segments_session_timestamp',
        'idx_transcript_segments_timestamp',
        'idx_chat_messages_session_id',
        'idx_users_created_at_analytics'
    ]
    
    for index_name in indexes_to_drop:
        try:
            connection.execute(sa.text(f"DROP INDEX IF EXISTS {index_name}"))
        except Exception:
            # Index might not exist, continue
            pass
