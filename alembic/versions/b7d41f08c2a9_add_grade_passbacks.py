"""add grade_passbacks

Revision ID: b7d41f08c2a9
Revises: 4eca25300999
Create Date: 2026-07-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b7d41f08c2a9'
down_revision: Union[str, None] = '4eca25300999'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('grade_passbacks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('submission_id', sa.Integer(), nullable=False),
    sa.Column('lineitem_url', sa.String(length=1000), nullable=False),
    sa.Column('lti_user_id', sa.String(length=255), nullable=False),
    sa.Column('score_given', sa.Float(), nullable=False),
    sa.Column('score_maximum', sa.Float(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('last_error', sa.String(length=500), nullable=False),
    sa.Column('posted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['submission_id'], ['submissions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_grade_passbacks_submission_id'), 'grade_passbacks', ['submission_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_grade_passbacks_submission_id'), table_name='grade_passbacks')
    op.drop_table('grade_passbacks')
