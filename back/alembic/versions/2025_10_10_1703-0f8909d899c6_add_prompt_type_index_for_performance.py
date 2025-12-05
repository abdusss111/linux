"""add_prompt_type_index_for_performance

Revision ID: 0f8909d899c6
Revises: 15aaab98bda8
Create Date: 2025-10-10 17:03:38.785842

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0f8909d899c6'
down_revision: Union[str, None] = '15aaab98bda8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add index on prompt_type column for better dashboard metrics performance."""
    # Add index on prompt_type for faster filtering by admin/user prompts
    op.create_index('ix_prompts_prompt_type', 'prompts', ['prompt_type'])


def downgrade() -> None:
    """Remove prompt_type index."""
    # Remove the index
    op.drop_index('ix_prompts_prompt_type', table_name='prompts')
