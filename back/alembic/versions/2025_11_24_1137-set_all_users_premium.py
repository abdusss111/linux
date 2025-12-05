"""set_all_users_premium

Revision ID: set_all_users_premium_001
Revises: add_subscription_tables_001
Create Date: 2025-11-24 11:37:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'set_all_users_premium_001'
down_revision: Union[str, None] = 'add_subscription_tables_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Set all existing users to premium plan (PRO users).
    Creates premium subscriptions for all users who don't have one.
    Updates all existing free/standard subscriptions to premium.
    """
    connection = op.get_bind()
    
    # Get all user IDs who don't have a subscription yet
    result = connection.execute(text("""
        SELECT id FROM users 
        WHERE id NOT IN (SELECT user_id FROM subscriptions)
    """))
    user_ids = [row[0] for row in result]
    
    # Check if subscriptions table exists and has data
    result = connection.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'subscriptions'
        )
    """))
    table_exists = result.scalar()
    
    if not table_exists:
        # Table doesn't exist yet, skip this migration step
        print("Subscriptions table does not exist yet. Skipping premium upgrade.")
        return
    
    # Store old plans BEFORE update for history (only if table has subscriptions)
    result = connection.execute(text("""
        SELECT COUNT(*) FROM subscriptions
    """))
    subscription_count = result.scalar()
    
    if subscription_count == 0:
        # No subscriptions exist yet, skip history creation
        print("No existing subscriptions found. Skipping history creation.")
    else:
        connection.execute(text("""
            CREATE TEMP TABLE temp_subscription_changes AS
            SELECT 
                id as subscription_id,
                plan as old_plan,
                status as old_status
            FROM subscriptions
            WHERE plan IN ('free'::subscriptionplan, 'standard'::subscriptionplan)
        """))
    
    # Update all existing free/standard subscriptions to premium (if any exist)
    if subscription_count > 0:
        connection.execute(text("""
            UPDATE subscriptions 
            SET plan = 'premium'::subscriptionplan,
                last_updated = NOW()
            WHERE plan IN ('free'::subscriptionplan, 'standard'::subscriptionplan)
        """))
        
        # Create history entries for subscriptions that were updated (free/standard -> premium)
        connection.execute(text("""
            INSERT INTO subscription_history (subscription_id, old_plan, new_plan, old_status, new_status, changed_by, reason, changed_at)
            SELECT 
                tsc.subscription_id,
                tsc.old_plan,
                'premium'::subscriptionplan,
                tsc.old_status,
                'active'::subscriptionstatus,
                'system',
                'Migration: Upgraded to premium plan (PRO user)',
                NOW()
            FROM temp_subscription_changes tsc
        """))
    
    # Verify table structure before inserting - check if plan column exists
    result = connection.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'subscriptions' 
            AND column_name = 'plan'
        )
    """))
    plan_column_exists = result.scalar()
    
    if not plan_column_exists:
        print("WARNING: subscriptions table exists but 'plan' column is missing.")
        print("This means add_subscription_tables_001 migration was not applied correctly.")
        print("Skipping set_all_users_premium_001 migration.")
        return
    
    # Create premium subscriptions for all users without subscriptions
    if user_ids:
        for user_id in user_ids:
            connection.execute(text("""
                INSERT INTO public.subscriptions (user_id, plan, status, start_date, last_updated, created_at)
                VALUES (:user_id, 'premium'::public.subscriptionplan, 'active'::public.subscriptionstatus, NOW(), NOW(), NOW())
            """), {"user_id": user_id})
    
    # Create history entries for new premium subscriptions (users without any subscription before)
    connection.execute(text("""
        INSERT INTO subscription_history (subscription_id, old_plan, new_plan, old_status, new_status, changed_by, reason, changed_at)
        SELECT 
            s.id,
            NULL,
            'premium'::subscriptionplan,
            NULL,
            s.status,
            'system',
            'Migration: Set all users to premium plan (PRO users)',
            NOW()
        FROM subscriptions s
        WHERE s.plan = 'premium'::subscriptionplan
        AND s.id NOT IN (SELECT subscription_id FROM subscription_history)
    """))
    
    # Clean up temp table (if it was created)
    if subscription_count > 0:
        connection.execute(text("DROP TABLE IF EXISTS temp_subscription_changes"))


def downgrade() -> None:
    """
    Revert all premium subscriptions back to free.
    Note: This will lose history of premium status.
    """
    connection = op.get_bind()
    
    # Update all premium subscriptions back to free
    connection.execute(text("""
        UPDATE subscriptions 
        SET plan = 'free'::subscriptionplan,
            last_updated = NOW()
        WHERE plan = 'premium'::subscriptionplan
    """))
    
    # Remove migration history entries
    connection.execute(text("""
        DELETE FROM subscription_history
        WHERE reason LIKE 'Migration: %premium%'
    """))

