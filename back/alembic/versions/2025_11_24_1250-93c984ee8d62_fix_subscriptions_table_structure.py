"""fix_subscriptions_table_structure

Revision ID: 93c984ee8d62
Revises: 15594b2c06d4
Create Date: 2025-11-24 12:50:58.247605

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '93c984ee8d62'
down_revision: Union[str, None] = '15594b2c06d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix subscriptions table structure - ensure plan column exists."""
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
    
    # Check if subscriptions table exists
    result = connection.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'subscriptions'
        )
    """))
    table_exists = result.scalar()
    
    # Check if plan column exists
    plan_column_exists = False
    if table_exists:
        result = connection.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'subscriptions' 
                AND column_name = 'plan'
            )
        """))
        plan_column_exists = result.scalar()
    
    # If table exists but plan column is missing, we need to fix it
    if table_exists and not plan_column_exists:
        print("WARNING: subscriptions table exists but plan column is missing. Recreating table...")
        
        # Use direct SQL with IF EXISTS to safely drop dependencies
        # This avoids transaction errors if dependencies don't exist
        connection.execute(text("""
            DO $$ 
            BEGIN
                -- Drop indexes if they exist
                DROP INDEX IF EXISTS ix_subscriptions_status;
                DROP INDEX IF EXISTS ix_subscriptions_plan;
                DROP INDEX IF EXISTS ix_subscriptions_user_id;
                DROP INDEX IF EXISTS ix_subscriptions_id;
                
                -- Drop foreign key constraint if it exists
                ALTER TABLE subscriptions DROP CONSTRAINT IF EXISTS subscriptions_user_id_fkey;
            END $$;
        """))
        
        # Drop the table using direct SQL
        connection.execute(text("DROP TABLE IF EXISTS subscriptions CASCADE"))
        table_exists = False
    
    # Create subscriptions table if it doesn't exist
    if not table_exists:
        print("Creating subscriptions table with correct structure...")
        op.create_table(
            'subscriptions',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('user_id', sa.String(), nullable=False),
            sa.Column('plan', postgresql.ENUM('free', 'standard', 'premium', name='subscriptionplan', create_type=False), nullable=False),
            sa.Column('status', postgresql.ENUM('active', 'expired', 'cancelled', name='subscriptionstatus', create_type=False), nullable=False),
            sa.Column('start_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
            sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Create indexes
        op.create_index('ix_subscriptions_id', 'subscriptions', ['id'], unique=False)
        op.create_index('ix_subscriptions_user_id', 'subscriptions', ['user_id'], unique=True)
        op.create_index('ix_subscriptions_plan', 'subscriptions', ['plan'], unique=False)
        op.create_index('ix_subscriptions_status', 'subscriptions', ['status'], unique=False)
        print("subscriptions table created successfully.")
    else:
        print("subscriptions table already exists with correct structure.")


def downgrade() -> None:
    """This migration is idempotent, no downgrade needed."""
    pass
