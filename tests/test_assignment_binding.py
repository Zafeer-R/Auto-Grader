from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.launch_context import get_launch_context, record_launch_context
from app.models.passback import GradePassback
from app.models.submission import Submission
from app.routers import grading
from app.routers.grading import _require_launched_assignment, submit_assignment


def _request(session: dict) -> Request:
    async def unexpected_receive():
        raise AssertionError("a rejected submission must not read its request body")

    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/assignment/lab08/submit",
            "headers": [],
            "session": session,
        },
        unexpected_receive,
    )


def test_legacy_matching_assignment_is_accepted():
    request = _request({
        "assignment_id": "lab01",
        "ags_lineitem": "https://canvas.test/line_items/lab01",
    })

    context = _require_launched_assignment(request, "lab01")

    assert context["ags_lineitem"].endswith("/lab01")


def test_multiple_launched_assignments_are_accepted():
    request = _request({
        "launch_contexts": {
            "lab01": {"ags_lineitem": "https://canvas.test/line_items/lab01"},
            "lab08": {"ags_lineitem": "https://canvas.test/line_items/lab08"},
        }
    })

    assert _require_launched_assignment(request, "lab01")["ags_lineitem"].endswith(
        "/lab01"
    )
    assert _require_launched_assignment(request, "lab08")["ags_lineitem"].endswith(
        "/lab08"
    )


@pytest.mark.parametrize(
    "session",
    [
        {"assignment_id": "lab01"},
        {
            "launch_contexts": {
                "lab01": {
                    "ags_lineitem": "https://canvas.test/line_items/lab01",
                }
            }
        },
        {},
    ],
    ids=["legacy-different-assignment", "different-assignment", "missing-context"],
)
def test_untrusted_assignment_is_rejected(session):
    request = _request(session)

    with pytest.raises(HTTPException) as exc_info:
        _require_launched_assignment(request, "lab08")

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Assignment does not match the active launch."


def test_record_launch_preserves_assignments_for_same_user():
    session = {}

    record_launch_context(
        session,
        user_id=7,
        assignment_id="lab01",
        ags_lineitem="https://canvas.test/line_items/lab01",
    )
    record_launch_context(
        session,
        user_id=7,
        assignment_id="lab08",
        ags_lineitem="https://canvas.test/line_items/lab08",
    )

    assert get_launch_context(session, "lab01")["ags_lineitem"].endswith("/lab01")
    assert get_launch_context(session, "lab08")["ags_lineitem"].endswith("/lab08")
    assert "assignment_id" not in session
    assert "ags_lineitem" not in session


def test_record_launch_clears_contexts_when_user_changes():
    session = {}
    record_launch_context(
        session,
        user_id=7,
        assignment_id="lab01",
        ags_lineitem="https://canvas.test/line_items/lab01",
    )

    record_launch_context(
        session,
        user_id=8,
        assignment_id="lab08",
        ags_lineitem="https://canvas.test/line_items/lab08",
    )

    assert get_launch_context(session, "lab01") is None
    assert get_launch_context(session, "lab08") is not None


def test_new_launch_migrates_same_users_legacy_context():
    session = {
        "user_id": 7,
        "assignment_id": "lab01",
        "ags_lineitem": "https://canvas.test/line_items/lab01",
    }

    record_launch_context(
        session,
        user_id=7,
        assignment_id="lab08",
        ags_lineitem="https://canvas.test/line_items/lab08",
    )

    assert get_launch_context(session, "lab01")["ags_lineitem"].endswith("/lab01")
    assert get_launch_context(session, "lab08")["ags_lineitem"].endswith("/lab08")


@pytest.mark.asyncio
async def test_submit_rejects_mismatch_before_processing_body_or_database():
    request = _request({
        "user_id": 1,
        "role": "student",
        "assignment_id": "lab01",
        "ags_lineitem": "https://canvas.test/line_items/lab01",
    })

    with pytest.raises(HTTPException) as exc_info:
        await submit_assignment(request, "lab08", db=None)

    assert exc_info.value.status_code == 403


@pytest.mark.parametrize("assignment_id", ["lab01", "lab08"])
async def test_submit_uses_its_assignment_lineitem(monkeypatch, assignment_id):
    session = {
        "user_id": 7,
        "role": "student",
        "launch_contexts": {
            "lab01": {"ags_lineitem": "https://canvas.test/line_items/lab01"},
            "lab08": {"ags_lineitem": "https://canvas.test/line_items/lab08"},
        },
    }
    request = SimpleNamespace(session=session, form=AsyncMock(return_value={}))
    added = []

    def add(model):
        added.append(model)

    async def flush():
        next(model for model in added if isinstance(model, Submission)).id = 41

    db = SimpleNamespace(
        add=Mock(side_effect=add),
        flush=AsyncMock(side_effect=flush),
        get=AsyncMock(return_value=SimpleNamespace(lti_user_id="canvas-user-7")),
        commit=AsyncMock(),
    )
    answer_key = {"questions": {}, "total_points": 0}
    grade_result = {
        "questions": {},
        "total_score": 0.0,
        "total_max": 0.0,
    }
    monkeypatch.setattr(grading, "load_answer_key", lambda _assignment_id: answer_key)
    monkeypatch.setattr(grading, "grade_submission", lambda _answers, _key: grade_result)
    monkeypatch.setattr(
        grading,
        "_carry_forward_checkpoints",
        AsyncMock(return_value={}),
    )
    monkeypatch.setattr(
        grading.templates,
        "TemplateResponse",
        lambda _request, _template, context: context,
    )

    await grading.submit_assignment(request, assignment_id, db)

    passback = next(model for model in added if isinstance(model, GradePassback))
    assert passback.lineitem_url == f"https://canvas.test/line_items/{assignment_id}"
    db.commit.assert_awaited_once()
