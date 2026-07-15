"""TA routes: submissions dashboard and checkpoint verification."""

import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.grading.checkpoints import checkpoint_sections, effective_score
from app.models.checkpoint import CheckpointState
from app.models.submission import Submission
from app.models.user import User
from app.routers.grading import _build_section_questions, load_answer_key

router = APIRouter(prefix="/ta", tags=["ta"])
templates = Jinja2Templates(directory="app/templates")


def _require_ta(request: Request) -> str | None:
    """Return an error message if the session user is not a TA/instructor."""
    if not request.session.get("user_id"):
        return "Not authenticated. Please launch from Canvas or use /dev/launch."
    if request.session.get("role") not in ("ta", "instructor"):
        return "TA or instructor role required."
    return None


async def _submission_row(
    db: AsyncSession, submission: Submission, student: User, answer_key: dict
) -> dict:
    """Build one dashboard row: scores, checkpoint states, consistency flags."""
    result = await db.execute(
        select(CheckpointState).where(CheckpointState.submission_id == submission.id)
    )
    states = {cs.checkpoint_id: cs.verified for cs in result.scalars()}

    checkpoints = checkpoint_sections(answer_key)
    score = effective_score(submission.total_score or 0.0, checkpoints, states)

    flags = (submission.grade_result or {}).get("flags", [])
    return {
        "submission": submission,
        "student": student,
        "score": score,
        "flags": flags,
        "grade_max": answer_key.get("total_points", 0),
    }


@router.get("/assignment/{assignment_id}", response_class=HTMLResponse)
async def ta_dashboard(
    request: Request, assignment_id: str, db: AsyncSession = Depends(get_db)
):
    """Submissions dashboard: one row per submission, newest first."""
    error = _require_ta(request)
    if error:
        return templates.TemplateResponse(request, "error.html", {"message": error})

    answer_key = load_answer_key(assignment_id)
    if not answer_key:
        return templates.TemplateResponse(request, "error.html", {
            "message": f"No answer key found for assignment '{assignment_id}'.",
        })

    result = await db.execute(
        select(Submission, User)
        .join(User, Submission.user_id == User.id)
        .where(Submission.assignment_id == assignment_id)
        .order_by(Submission.submitted_at.desc())
    )
    rows = [
        await _submission_row(db, submission, student, answer_key)
        for submission, student in result.all()
    ]

    return templates.TemplateResponse(request, "ta_submissions.html", {
        "assignment_id": assignment_id,
        "title": answer_key.get("title", assignment_id),
        "rows": rows,
        "checkpoints": checkpoint_sections(answer_key),
        "role": request.session.get("role"),
    })


@router.post("/submission/{submission_id}/checkpoint/{checkpoint_id}", response_class=HTMLResponse)
async def toggle_checkpoint(
    request: Request,
    submission_id: int,
    checkpoint_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Toggle a checkpoint's verified state; returns the updated row fragment."""
    error = _require_ta(request)
    if error:
        return templates.TemplateResponse(request, "error.html", {"message": error})

    submission = await db.get(Submission, submission_id)
    if not submission:
        return templates.TemplateResponse(request, "error.html", {
            "message": f"Submission {submission_id} not found.",
        })

    answer_key = load_answer_key(submission.assignment_id)
    checkpoints = {cp["id"]: cp for cp in checkpoint_sections(answer_key or {})}
    if checkpoint_id not in checkpoints:
        return templates.TemplateResponse(request, "error.html", {
            "message": f"Unknown checkpoint '{checkpoint_id}'.",
        })

    result = await db.execute(
        select(CheckpointState).where(
            CheckpointState.submission_id == submission_id,
            CheckpointState.checkpoint_id == checkpoint_id,
        )
    )
    state = result.scalar_one_or_none()
    now = datetime.datetime.now(datetime.timezone.utc)
    if state is None:
        state = CheckpointState(
            submission_id=submission_id,
            checkpoint_id=checkpoint_id,
            verified=True,
            verified_by=request.session["user_id"],
            verified_at=now,
            points=checkpoints[checkpoint_id]["points"],
        )
        db.add(state)
    else:
        state.verified = not state.verified
        state.verified_by = request.session["user_id"]
        state.verified_at = now
        state.points = checkpoints[checkpoint_id]["points"]
    await db.commit()

    student = await db.get(User, submission.user_id)
    row = await _submission_row(db, submission, student, answer_key)
    return templates.TemplateResponse(request, "_ta_row.html", {"row": row})


@router.get("/assignment/{assignment_id}/structure", response_class=HTMLResponse)
async def ta_structure(request: Request, assignment_id: str):
    """Read-only view of the assignment structure and nominal expected values."""
    error = _require_ta(request)
    if error:
        return templates.TemplateResponse(request, "error.html", {"message": error})

    answer_key = load_answer_key(assignment_id)
    if not answer_key:
        return templates.TemplateResponse(request, "error.html", {
            "message": f"No answer key found for assignment '{assignment_id}'.",
        })

    return templates.TemplateResponse(request, "ta_dashboard.html", {
        "assignment_id": assignment_id,
        "title": answer_key.get("title", assignment_id),
        "sections": _build_section_questions(answer_key),
        "role": request.session.get("role"),
    })
