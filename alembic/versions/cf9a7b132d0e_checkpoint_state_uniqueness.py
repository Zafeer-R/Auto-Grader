"""Enforce one state per submission checkpoint.

Revision ID: cf9a7b132d0e
Revises: b7d41f08c2a9
Create Date: 2026-07-15

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "cf9a7b132d0e"
down_revision: str | None = "b7d41f08c2a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONSTRAINT_NAME = "uq_checkpoint_states_submission_checkpoint"


def upgrade() -> None:
    # Retain the most recently updated row so older databases can accept the
    # constraint even if concurrent first toggles already created duplicates.
    op.execute(
        sa.text(
            """
            WITH ranked AS (
                SELECT
                    id,
                    row_number() OVER (
                        PARTITION BY submission_id, checkpoint_id
                        ORDER BY updated_at DESC NULLS LAST, id DESC
                    ) AS duplicate_rank
                FROM checkpoint_states
            )
            DELETE FROM checkpoint_states
            USING ranked
            WHERE checkpoint_states.id = ranked.id
              AND ranked.duplicate_rank > 1
            """
        )
    )
    op.create_unique_constraint(
        CONSTRAINT_NAME,
        "checkpoint_states",
        ["submission_id", "checkpoint_id"],
    )


def downgrade() -> None:
    op.drop_constraint(CONSTRAINT_NAME, "checkpoint_states", type_="unique")
