from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.models.passback import GradePassback
from app.routers import ta
from app.services.ags import AGSError


def _post_grade_context(*, existing_attempts: int):
    submission = SimpleNamespace(
        id=5,
        user_id=9,
        total_score=22.0,
        max_score=30.0,
    )
    passback = SimpleNamespace(lineitem_url="", attempts=existing_attempts)

    lock_result = Mock()
    lock_result.scalar_one_or_none.return_value = submission
    checkpoint_result = Mock()
    checkpoint_result.scalars.return_value = []
    passback_result = Mock()
    passback_result.scalar_one_or_none.return_value = passback
    db = SimpleNamespace(
        execute=AsyncMock(
            side_effect=[lock_result, checkpoint_result, passback_result]
        ),
        get=AsyncMock(return_value=SimpleNamespace(lti_user_id="canvas-user-9")),
        commit=AsyncMock(),
    )
    request = SimpleNamespace(
        session={"ags_lineitem": "https://canvas.test/line_items/17"}
    )
    answer_key = {"total_points": 30, "questions": {}}
    return db, request, submission, passback, answer_key


@pytest.mark.parametrize("failure_attempts", [1, 3])
async def test_ta_persists_failure_attempt_count(monkeypatch, failure_attempts):
    db, request, submission, passback, answer_key = _post_grade_context(
        existing_attempts=4
    )
    client = SimpleNamespace(
        post_score=AsyncMock(
            side_effect=AGSError("Canvas rejected the score", attempts=failure_attempts)
        )
    )
    monkeypatch.setattr(ta, "_ags_client", lambda: client)

    await ta._post_grade(db, request, submission, answer_key)

    assert passback.status == "failed"
    assert passback.attempts == 4 + failure_attempts
    assert passback.last_error == "Canvas rejected the score"
    db.commit.assert_awaited_once()


async def test_ta_preserves_successful_retry_accounting(monkeypatch):
    db, request, submission, passback, answer_key = _post_grade_context(
        existing_attempts=4
    )
    client = SimpleNamespace(
        post_score=AsyncMock(
            return_value={"status": "posted", "attempts": 2, "payload": {}}
        )
    )
    monkeypatch.setattr(ta, "_ags_client", lambda: client)

    await ta._post_grade(db, request, submission, answer_key)

    assert passback.status == "posted"
    assert passback.attempts == 6
    assert passback.last_error == ""
    db.commit.assert_awaited_once()


async def test_ta_initializes_attempts_when_creating_passback(monkeypatch):
    submission = SimpleNamespace(
        id=5,
        user_id=9,
        total_score=22.0,
        max_score=30.0,
    )
    lock_result = Mock()
    lock_result.scalar_one_or_none.return_value = submission
    checkpoint_result = Mock()
    checkpoint_result.scalars.return_value = []
    passback_result = Mock()
    passback_result.scalar_one_or_none.return_value = None
    db = SimpleNamespace(
        execute=AsyncMock(
            side_effect=[lock_result, checkpoint_result, passback_result]
        ),
        add=Mock(),
        get=AsyncMock(return_value=SimpleNamespace(lti_user_id="canvas-user-9")),
        commit=AsyncMock(),
    )
    request = SimpleNamespace(
        session={"ags_lineitem": "https://canvas.test/line_items/17"}
    )
    answer_key = {"total_points": 30, "questions": {}}
    client = SimpleNamespace(
        post_score=AsyncMock(
            return_value={"status": "posted", "attempts": 1, "payload": {}}
        )
    )
    monkeypatch.setattr(ta, "_ags_client", lambda: client)

    passback = await ta._post_grade(db, request, submission, answer_key)

    assert isinstance(passback, GradePassback)
    assert passback.submission_id == submission.id
    assert passback.attempts == 1
    db.add.assert_called_once_with(passback)
    db.commit.assert_awaited_once()
