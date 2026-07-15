from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.routers import ta
from app.services.ags import AGSClient


@pytest.mark.parametrize(
    ("answer_key", "expected_progress"),
    [
        (
            {
                "total_points": 30,
                "questions": {
                    "explanation": {
                        "type": "short_answer",
                        "grading": "deferred_m2",
                        "points": 8,
                    }
                },
            },
            "PendingManual",
        ),
        (
            {
                "total_points": 30,
                "questions": {
                    "calculation": {"type": "numerical", "points": 30}
                },
            },
            "FullyGraded",
        ),
    ],
)
async def test_ta_post_grade_threads_assignment_grading_progress(
    monkeypatch, answer_key, expected_progress
):
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
    db = SimpleNamespace(
        execute=AsyncMock(
            side_effect=[lock_result, checkpoint_result, passback_result]
        ),
        get=AsyncMock(return_value=student),
        commit=AsyncMock(),
    )
    request = SimpleNamespace(
        session={"ags_lineitem": "https://canvas.test/line_items/17"}
    )
    client = SimpleNamespace(
        post_score=AsyncMock(
            return_value={"status": "posted", "attempts": 1, "payload": {}}
        )
    )
    monkeypatch.setattr(ta, "_ags_client", lambda: client)

    await ta._post_grade(db, request, submission, answer_key)

    client.post_score.assert_awaited_once_with(
        lineitem_url="https://canvas.test/line_items/17",
        lti_user_id="canvas-user-9",
        score_given=22.0,
        score_maximum=30,
        grading_progress=expected_progress,
    )
    db.commit.assert_awaited_once()


async def test_pending_manual_is_emitted_in_score_payload():
    result = await AGSClient(mode="dry_run").post_score(
        "https://canvas.test/line_items/17",
        "canvas-user-9",
        22.0,
        30.0,
        grading_progress="PendingManual",
    )

    assert result["payload"]["gradingProgress"] == "PendingManual"
