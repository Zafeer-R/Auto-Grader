import pytest
from fastapi import HTTPException
from starlette.requests import Request

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


def test_matching_assignment_is_accepted():
    request = _request({"assignment_id": "lab01"})

    _require_launched_assignment(request, "lab01")


@pytest.mark.parametrize(
    "session",
    [
        {"assignment_id": "lab01"},
        {},
    ],
    ids=["different-assignment", "missing-launch-context"],
)
def test_untrusted_assignment_is_rejected(session):
    request = _request(session)

    with pytest.raises(HTTPException) as exc_info:
        _require_launched_assignment(request, "lab08")

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Assignment does not match the active launch."


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
