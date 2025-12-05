"""add prompts table

Revision ID: 2025_01_27_0000
Revises: 2025_01_27_0001
Create Date: 2025-01-27 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2025_01_27_0000'
down_revision = '2025_01_27_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create prompts table
    op.create_table('prompts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('prompt_type', sa.String(length=50), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_prompts_id'), 'prompts', ['id'], unique=False)
    op.create_index(op.f('ix_prompts_name'), 'prompts', ['name'], unique=True)
    op.create_index(op.f('ix_prompts_prompt_type'), 'prompts', ['prompt_type'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_prompts_prompt_type'), table_name='prompts')
    op.drop_index(op.f('ix_prompts_name'), table_name='prompts')
    op.drop_index(op.f('ix_prompts_id'), table_name='prompts')
    
    # Drop table
    op.drop_table('prompts')
