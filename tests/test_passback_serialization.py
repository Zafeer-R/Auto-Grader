import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from sqlalchemy.dialects import postgresql

from app.routers import ta


def _assert_submission_for_update(statement) -> None:
    sql = " ".join(
        str(statement.compile(dialect=postgresql.dialect())).split()
    )
    assert "FROM submissions" in sql
    assert "WHERE submissions.id =" in sql
    assert sql.endswith("FOR UPDATE")


async def test_post_grade_locks_submission_through_canvas_post(monkeypatch):
    submission = SimpleNamespace(
        id=5,
        user_id=9,
        total_score=22.0,
        max_score=30.0,
    )
    student = SimpleNamespace(lti_user_id="canvas-user-9")
    passback = SimpleNamespace(lineitem_url="", attempts=0)

    lock_result = Mock()
    lock_result.scalar_one_or_none.return_value = submission
    checkpoint_result = Mock()
    checkpoint_result.scalars.return_value = []
    passback_result = Mock()
    passback_result.scalar_one_or_none.return_value = passback
    results = [lock_result, checkpoint_result, passback_result]
    statements = []
    events = []

    async def execute(statement):
        index = len(statements)
        statements.append(statement)
        events.append(["lock", "checkpoints", "passback"][index])
        return results[index]

    async def commit():
        events.append("commit")

    async def post_score(**_kwargs):
        events.append("post")
        return {"status": "posted", "attempts": 1, "payload": {}}

    db = SimpleNamespace(
        execute=AsyncMock(side_effect=execute),
        get=AsyncMock(return_value=student),
        commit=AsyncMock(side_effect=commit),
    )
    request = SimpleNamespace(
        session={"ags_lineitem": "https://canvas.test/line_items/17"}
    )
    client = SimpleNamespace(post_score=AsyncMock(side_effect=post_score))
    monkeypatch.setattr(ta, "_ags_client", lambda: client)

    await ta._post_grade(
        db,
        request,
        submission,
        {"total_points": 30, "questions": {}},
    )

    _assert_submission_for_update(statements[0])
    assert events == ["lock", "checkpoints", "passback", "post", "commit"]


async def test_toggle_locks_same_submission_before_checkpoint_write(monkeypatch):
    submission = SimpleNamespace(id=7, user_id=2, assignment_id="lab01")
    student = SimpleNamespace(id=2)
    passback = SimpleNamespace(
        status="posted",
        posted_at=datetime.datetime.now(datetime.timezone.utc),
        last_error="",
    )

    lock_result = Mock()
    lock_result.scalar_one_or_none.return_value = submission
    toggle_result = Mock()
    passback_result = Mock()
    passback_result.scalar_one_or_none.return_value = passback
    results = [lock_result, toggle_result, passback_result]
    statements = []
    events = []

    async def execute(statement):
        index = len(statements)
        statements.append(statement)
        events.append(["lock", "toggle", "passback"][index])
        return results[index]

    async def commit():
        events.append("commit")

    db = SimpleNamespace(
        execute=AsyncMock(side_effect=execute),
        get=AsyncMock(return_value=student),
        commit=AsyncMock(side_effect=commit),
    )
    request = SimpleNamespace(session={"user_id": 1, "role": "ta"})
    answer_key = {
        "sections": [
            {
                "id": "safety",
                "title": "Lab Safety Training",
                "type": "checkpoint",
                "points": 10,
            }
        ]
    }
    monkeypatch.setattr(ta, "load_answer_key", lambda _assignment_id: answer_key)
    monkeypatch.setattr(ta, "_submission_row", AsyncMock(return_value={}))
    monkeypatch.setattr(
        ta.templates,
        "TemplateResponse",
        lambda _request, _template, context: context,
    )

    await ta.toggle_checkpoint(request, submission.id, "safety", db)

    _assert_submission_for_update(statements[0])
    assert events == ["lock", "toggle", "passback", "commit"]
    assert passback.status == "pending"

