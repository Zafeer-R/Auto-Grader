import datetime
import importlib.util
from pathlib import Path

from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects import postgresql

from app.models.checkpoint import (
    CHECKPOINT_STATE_UNIQUE_CONSTRAINT,
    CheckpointState,
)
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
