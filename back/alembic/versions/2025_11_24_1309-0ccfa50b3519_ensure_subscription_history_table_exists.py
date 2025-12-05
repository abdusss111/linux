"""ensure_subscription_history_table_exists

Revision ID: 0ccfa50b3519
Revises: 93c984ee8d62
Create Date: 2025-11-24 13:09:54.119835

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '0ccfa50b3519'
down_revision: Union[str, None] = '93c984ee8d62'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Ensure subscription_history table exists with all required fields."""
    connection = op.get_bind()
    
    # Check if enum types exist, create if not
    result = connection.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_type WHERE typname = 'subscriptionplan'
        )
    """))
    if not result.scalar():
        print("Creating subscriptionplan enum type...")
        op.execute("CREATE TYPE subscriptionplan AS ENUM ('free', 'standard', 'premium')")
    
    result = connection.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_type WHERE typname = 'subscriptionstatus'
        )
    """))
    if not result.scalar():
        print("Creating subscriptionstatus enum type...")
        op.execute("CREATE TYPE subscriptionstatus AS ENUM ('active', 'expired', 'cancelled')")
    
    # Check if subscriptions table exists (required for FK)
    result = connection.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'subscriptions'
        )
    """))
    subscriptions_exists = result.scalar()
    
    if not subscriptions_exists:
        print("WARNING: subscriptions table does not exist. Cannot create subscription_history table.")
        print("Please ensure add_subscription_tables_001 migration is applied first.")
        return
    
    # Check if subscription_history table exists
    result = connection.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'subscription_history'
        )
    """))
    history_exists = result.scalar()
    
    if not history_exists:
        print("Creating subscription_history table...")
        op.create_table(
            'subscription_history',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('subscription_id', sa.Integer(), nullable=False),
            sa.Column('old_plan', postgresql.ENUM('free', 'standard', 'premium', name='subscriptionplan', create_type=False), nullable=True),
            sa.Column('new_plan', postgresql.ENUM('free', 'standard', 'premium', name='subscriptionplan', create_type=False), nullable=False),
            sa.Column('old_status', postgresql.ENUM('active', 'expired', 'cancelled', name='subscriptionstatus', create_type=False), nullable=True),
            sa.Column('new_status', postgresql.ENUM('active', 'expired', 'cancelled', name='subscriptionstatus', create_type=False), nullable=False),
            sa.Column('changed_by', sa.String(), nullable=True),
            sa.Column('reason', sa.String(length=500), nullable=True),
            sa.Column('changed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Create indexes for subscription_history
        op.create_index('ix_subscription_history_id', 'subscription_history', ['id'], unique=False)
        op.create_index('ix_subscription_history_subscription_id', 'subscription_history', ['subscription_id'], unique=False)
        print("subscription_history table created successfully.")
    else:
        print("subscription_history table already exists. Checking indexes...")
        
        # Check and create missing indexes
        index_names = {
            'ix_subscription_history_id': ['id'],
            'ix_subscription_history_subscription_id': ['subscription_id']
        }
        
        for index_name, columns in index_names.items():
            result = connection.execute(text(f"""
                SELECT EXISTS (
                    SELECT 1 FROM pg_indexes 
                    WHERE schemaname = 'public'
                    AND indexname = '{index_name}'
                )
            """))
            if not result.scalar():
                print(f"Creating missing index: {index_name}")
                op.create_index(index_name, 'subscription_history', columns, unique=False)
        
        print("subscription_history table structure verified.")


def downgrade() -> None:
    """Remove subscription_history table if it exists."""
    connection = op.get_bind()
    
    result = connection.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'subscription_history'
        )
    """))
    
    if result.scalar():
        # Drop indexes first
        op.drop_index('ix_subscription_history_subscription_id', table_name='subscription_history')
        op.drop_index('ix_subscription_history_id', table_name='subscription_history')
        # Drop table
        op.drop_table('subscription_history')
