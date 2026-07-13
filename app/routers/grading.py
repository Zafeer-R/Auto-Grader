import datetime
import json
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.grading.engine import grade_submission
from app.models.submission import Submission

router = APIRouter(tags=["grading"])
templates = Jinja2Templates(directory="app/templates")

ANSWER_KEYS_DIR = Path("answer_keys")


def load_answer_key(assignment_id: str) -> dict | None:
    """Load answer key JSON from the answer_keys directory."""
    path = ANSWER_KEYS_DIR / f"{assignment_id}.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


@router.get("/assignment/{assignment_id}", response_class=HTMLResponse)
async def view_assignment(request: Request, assignment_id: str):
    """Render the assignment form for a student."""
    user_id = request.session.get("user_id")
    role = request.session.get("role", "student")
    if not user_id:
        return templates.TemplateResponse(request, "error.html", {
            "message": "Not authenticated. Please launch from Canvas or use /dev/launch.",
        })

    answer_key = load_answer_key(assignment_id)
    if not answer_key:
        return templates.TemplateResponse(request, "error.html", {
            "message": f"No answer key found for assignment '{assignment_id}'.",
        })

    return templates.TemplateResponse(request, "assignment.html", {
        "assignment_id": assignment_id,
        "title": answer_key.get("title", assignment_id),
        "questions": answer_key["questions"],
        "role": role,
    })


@router.post("/assignment/{assignment_id}/submit")
async def submit_assignment(
    request: Request,
    assignment_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Grade a student submission and return results."""
    user_id = request.session.get("user_id")
    if not user_id:
        return templates.TemplateResponse(request, "error.html", {
            "message": "Not authenticated.",
        })

    form_data = await request.form()
    answers = {key: form_data[key] for key in form_data if key.startswith("q_")}
    # Strip the q_ prefix for grading
    clean_answers = {k.removeprefix("q_"): v for k, v in answers.items()}

    answer_key = load_answer_key(assignment_id)
    if not answer_key:
        return templates.TemplateResponse(request, "error.html", {
            "message": f"No answer key found for assignment '{assignment_id}'.",
        })

    result = grade_submission(clean_answers, answer_key)

    # Store submission
    submission = Submission(
        user_id=user_id,
        assignment_id=assignment_id,
        answers=clean_answers,
        total_score=result["total_score"],
        max_score=result["total_max"],
        grade_result=result,
        graded_at=datetime.datetime.now(datetime.timezone.utc),
    )
    db.add(submission)
    await db.commit()

    return templates.TemplateResponse(request, "results.html", {
        "assignment_id": assignment_id,
        "title": answer_key.get("title", assignment_id),
        "result": result,
    })
