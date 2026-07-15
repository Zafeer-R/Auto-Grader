import datetime
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects import postgresql

from app.models.checkpoint import (
    CHECKPOINT_STATE_UNIQUE_CONSTRAINT,
    CheckpointState,
)
from app.routers.grading import _carry_forward_checkpoints
from app.routers.ta import _checkpoint_toggle_statement


def test_checkpoint_model_has_composite_unique_constraint():
    constraints = [
        constraint
        for constraint in CheckpointState.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    ]

    assert any(
        constraint.name == CHECKPOINT_STATE_UNIQUE_CONSTRAINT
        and [column.name for column in constraint.columns]
        == ["submission_id", "checkpoint_id"]
        for constraint in constraints
    )


def test_toggle_is_one_atomic_postgresql_upsert():
    now = datetime.datetime(2026, 7, 15, 12, 30, tzinfo=datetime.timezone.utc)
    statement = _checkpoint_toggle_statement(
        submission_id=7,
        checkpoint_id="safety",
        verified_by=3,
        verified_at=now,
        points=10.0,
    )

    compiled = statement.compile(dialect=postgresql.dialect())
    sql = " ".join(str(compiled).split())

    assert "INSERT INTO checkpoint_states" in sql
    assert (
        f"ON CONFLICT ON CONSTRAINT {CHECKPOINT_STATE_UNIQUE_CONSTRAINT} DO UPDATE"
        in sql
    )
    assert "verified = NOT checkpoint_states.verified" in sql
    assert "verified_by = excluded.verified_by" in sql
    assert "verified_at = excluded.verified_at" in sql
    assert "points = excluded.points" in sql


async def test_carry_forward_locks_previous_submission_before_copying_states():
    verified_at = datetime.datetime(
        2026, 7, 15, 12, 30, tzinfo=datetime.timezone.utc
    )
    previous = SimpleNamespace(id=6)
    state = SimpleNamespace(
        checkpoint_id="safety",
        verified=True,
        verified_by=3,
        verified_at=verified_at,
        points=10.0,
    )
    previous_result = Mock()
    previous_result.scalar_one_or_none.return_value = previous
    state_result = Mock()
    state_result.scalars.return_value = [state]
    statements = []

    async def execute(statement):
        statements.append(statement)
        return [previous_result, state_result][len(statements) - 1]

    db = SimpleNamespace(
        execute=AsyncMock(side_effect=execute),
        add=Mock(),
    )
    submission = SimpleNamespace(id=7, user_id=2, assignment_id="lab01")

    verified = await _carry_forward_checkpoints(db, submission)

    previous_sql = " ".join(
        str(statements[0].compile(dialect=postgresql.dialect())).split()
    )
    states_sql = " ".join(
        str(statements[1].compile(dialect=postgresql.dialect())).split()
    )
    assert "FROM submissions" in previous_sql
    assert "ORDER BY submissions.id DESC" in previous_sql
    assert "FOR UPDATE" in previous_sql
    assert "FROM checkpoint_states" in states_sql
    assert "checkpoint_states.submission_id" in states_sql

    copied = db.add.call_args.args[0]
    assert copied.submission_id == submission.id
    assert copied.checkpoint_id == state.checkpoint_id
    assert copied.verified is state.verified
    assert copied.verified_by == state.verified_by
    assert copied.verified_at == state.verified_at
    assert copied.points == state.points
    assert verified == {"safety": True}


def test_migration_deduplicates_before_adding_constraint(monkeypatch):
    migration_path = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "cf9a7b132d0e_checkpoint_state_uniqueness.py"
    )
    spec = importlib.util.spec_from_file_location("checkpoint_state_uniqueness", migration_path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    events = []
    monkeypatch.setattr(
        migration.op,
        "execute",
        lambda statement: events.append(("sql", str(statement))),
    )
    monkeypatch.setattr(
        migration.op,
        "create_unique_constraint",
        lambda name, table, columns: events.append(("constraint", name, table, columns)),
    )

    migration.upgrade()

    assert events[0][0] == "sql"
    assert "row_number() OVER" in events[0][1]
    assert "duplicate_rank > 1" in events[0][1]
    assert events[1] == (
        "constraint",
        CHECKPOINT_STATE_UNIQUE_CONSTRAINT,
        "checkpoint_states",
        ["submission_id", "checkpoint_id"],
    )
