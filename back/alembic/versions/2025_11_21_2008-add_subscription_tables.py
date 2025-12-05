"""add_subscription_tables

Revision ID: add_subscription_tables_001
Revises: increase_segment_columns_001
Create Date: 2025-11-21 20:08:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'add_subscription_tables_001'
down_revision: Union[str, None] = 'increase_segment_columns_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types first (if they don't exist)
    connection = op.get_bind()
    
    # Check if types exist before creating
    result = connection.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_type WHERE typname = 'subscriptionplan'
        )
    """))
    if not result.scalar():
        op.execute("CREATE TYPE subscriptionplan AS ENUM ('free', 'standard', 'premium')")
    
    result = connection.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_type WHERE typname = 'subscriptionstatus'
        )
    """))
    if not result.scalar():
        op.execute("CREATE TYPE subscriptionstatus AS ENUM ('active', 'expired', 'cancelled')")
    
    # Check if subscriptions table exists
    result = connection.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'subscriptions'
        )
    """))
    subscriptions_exists = result.scalar()
    
    # Check if plan column exists (to detect incomplete table creation)
    plan_column_exists = False
    if subscriptions_exists:
        result = connection.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'subscriptions' 
                AND column_name = 'plan'
            )
        """))
        plan_column_exists = result.scalar()
    
    # Create subscriptions table with enum types (if it doesn't exist or is incomplete)
    if not subscriptions_exists or not plan_column_exists:
        if subscriptions_exists and not plan_column_exists:
            # Table exists but is incomplete - drop and recreate
            print("WARNING: subscriptions table exists but is incomplete. Recreating...")
            op.drop_table('subscriptions')
        
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
        op.create_index(op.f('ix_subscriptions_id'), 'subscriptions', ['id'], unique=False)
        op.create_index(op.f('ix_subscriptions_user_id'), 'subscriptions', ['user_id'], unique=True)
        op.create_index(op.f('ix_subscriptions_plan'), 'subscriptions', ['plan'], unique=False)
        op.create_index(op.f('ix_subscriptions_status'), 'subscriptions', ['status'], unique=False)
    else:
        # Table exists, check which columns exist and create missing indexes
        indexes_to_create = {
            'ix_subscriptions_id': (['id'], False),
            'ix_subscriptions_user_id': (['user_id'], True),
            'ix_subscriptions_plan': (['plan'], False),
            'ix_subscriptions_status': (['status'], False)
        }
        
        for index_name, (columns, is_unique) in indexes_to_create.items():
            # Check if index exists
            result = connection.execute(text(f"""
                SELECT EXISTS (
                    SELECT 1 FROM pg_indexes 
                    WHERE indexname = '{index_name}'
                )
            """))
            index_exists = result.scalar()
            
            if not index_exists:
                # Check if all columns exist
                all_columns_exist = True
                for col in columns:
                    result = connection.execute(text(f"""
                        SELECT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'subscriptions' AND column_name = '{col}'
                        )
                    """))
                    if not result.scalar():
                        all_columns_exist = False
                        break
                
                if all_columns_exist:
                    # All columns exist, create index
                    op.create_index(index_name, 'subscriptions', columns, unique=is_unique)
    
    # Check if subscription_history table exists
    result = connection.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = 'subscription_history'
        )
    """))
    history_exists = result.scalar()
    
    # Check if subscriptions.id is INTEGER (required for FK)
    subscriptions_id_type = None
    if subscriptions_exists:
        result = connection.execute(text("""
            SELECT data_type 
            FROM information_schema.columns 
            WHERE table_name = 'subscriptions' AND column_name = 'id'
        """))
        row = result.fetchone()
        if row:
            subscriptions_id_type = row[0]
    
    # Create subscription_history table (if it doesn't exist and subscriptions has correct structure)
    if not history_exists and subscriptions_exists and subscriptions_id_type == 'integer':
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
        op.create_index(op.f('ix_subscription_history_id'), 'subscription_history', ['id'], unique=False)
        op.create_index(op.f('ix_subscription_history_subscription_id'), 'subscription_history', ['subscription_id'], unique=False)
    elif history_exists:
        # Table exists, check indexes
        for index_name in ['ix_subscription_history_id', 'ix_subscription_history_subscription_id']:
            result = connection.execute(text(f"""
                SELECT EXISTS (
                    SELECT 1 FROM pg_indexes 
                    WHERE indexname = '{index_name}'
                )
            """))
            if not result.scalar():
                if 'subscription_id' in index_name:
                    op.create_index(index_name, 'subscription_history', ['subscription_id'], unique=False)
                else:
                    op.create_index(index_name, 'subscription_history', ['id'], unique=False)
    
    # Check if subscription_plan column exists in meetings table
    result = connection.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'meetings' 
            AND column_name = 'subscription_plan'
        )
    """))
    column_exists = result.scalar()
    
    # Add subscription_plan column to meetings table (if it doesn't exist)
    if not column_exists:
        print("Adding subscription_plan column to meetings table...")
        op.add_column('meetings', sa.Column('subscription_plan', sa.String(length=20), nullable=True))
        print("subscription_plan column added successfully.")
    else:
        print("subscription_plan column already exists in meetings table.")


def downgrade() -> None:
    # Remove subscription_plan column from meetings (if it exists)
    connection = op.get_bind()
    result = connection.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'meetings' 
            AND column_name = 'subscription_plan'
        )
    """))
    if result.scalar():
        op.drop_column('meetings', 'subscription_plan')
    
    # Drop subscription_history table
    op.drop_index(op.f('ix_subscription_history_subscription_id'), table_name='subscription_history')
    op.drop_index(op.f('ix_subscription_history_id'), table_name='subscription_history')
    op.drop_table('subscription_history')
    
    # Drop subscriptions table
    op.drop_index(op.f('ix_subscriptions_status'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_plan'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_user_id'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_id'), table_name='subscriptions')
    op.drop_table('subscriptions')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS subscriptionstatus')
    op.execute('DROP TYPE IF EXISTS subscriptionplan')

