"""add_subscription_plan_to_meetings_if_missing

Revision ID: 15594b2c06d4
Revises: set_all_users_premium_001
Create Date: 2025-11-24 12:48:09.887524

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '15594b2c06d4'
down_revision: Union[str, None] = 'set_all_users_premium_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add subscription_plan column to meetings table if it doesn't exist."""
    connection = op.get_bind()
    
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
    """Remove subscription_plan column from meetings table if it exists."""
    connection = op.get_bind()
    
    # Check if subscription_plan column exists
    result = connection.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'meetings' 
            AND column_name = 'subscription_plan'
        )
    """))
    column_exists = result.scalar()
    
    if column_exists:
        op.drop_column('meetings', 'subscription_plan')
