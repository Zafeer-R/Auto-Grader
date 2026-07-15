"""TA routes: submissions dashboard, checkpoint verification, grade passback."""

import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.grading.checkpoints import checkpoint_sections, effective_score
from app.launch_context import get_launch_context
from app.models.checkpoint import (
    CHECKPOINT_STATE_UNIQUE_CONSTRAINT,
    CheckpointState,
)
from app.models.passback import GradePassback
from app.models.submission import Submission
from app.models.user import User
from app.routers.grading import _build_section_questions, load_answer_key
from app.services.ags import AGSClient, AGSError

router = APIRouter(prefix="/ta", tags=["ta"])
templates = Jinja2Templates(directory="app/templates")


def _ags_client() -> AGSClient:
    return AGSClient(
        mode=settings.ags_mode,
        token_url=settings.lti_token_url,
        client_id=settings.lti_client_id,
        private_key_pem=settings.lti_tool_private_key,
        key_id=settings.lti_tool_key_id,
    )


def _grading_progress(answer_key: dict) -> str:
    """Return the AGS grading state implied by this assignment's graders."""
    for question in answer_key.get("questions", {}).values():
        grading = str(question.get("grading", "")).lower()
        if question.get("type") == "short_answer" or grading.startswith(
            ("deferred", "manual")
        ):
            return "PendingManual"
    return "FullyGraded"


async def _lock_submission(
    db: AsyncSession, submission_id: int
) -> Submission | None:
    """Lock a submission as the serialization point for checkpoint passback."""
    result = await db.execute(
        select(Submission)
        .where(Submission.id == submission_id)
        .with_for_update()
    )
    return result.scalar_one_or_none()


def _checkpoint_toggle_statement(
    *,
    submission_id: int,
    checkpoint_id: str,
    verified_by: int,
    verified_at: datetime.datetime,
    points: float,
):
    """Build one PostgreSQL statement that serializes checkpoint toggles."""
    statement = pg_insert(CheckpointState).values(
        submission_id=submission_id,
        checkpoint_id=checkpoint_id,
        verified=True,
        verified_by=verified_by,
        verified_at=verified_at,
        points=points,
        updated_at=verified_at,
    )
    return statement.on_conflict_do_update(
        constraint=CHECKPOINT_STATE_UNIQUE_CONSTRAINT,
        set_={
            "verified": ~CheckpointState.verified,
            "verified_by": statement.excluded.verified_by,
            "verified_at": statement.excluded.verified_at,
            "points": statement.excluded.points,
            "updated_at": statement.excluded.updated_at,
        },
    )


async def _post_grade(
    db: AsyncSession, request: Request, submission: Submission, answer_key: dict
) -> GradePassback:
    """Post a submission's effective score via AGS, persisting the outcome."""
    locked_submission = await _lock_submission(db, submission.id)
    if locked_submission is None:
        raise LookupError(f"Submission {submission.id} no longer exists.")
    submission = locked_submission

    result = await db.execute(
        select(CheckpointState).where(CheckpointState.submission_id == submission.id)
    )
    states = {cs.checkpoint_id: cs.verified for cs in result.scalars()}
    score = effective_score(
        submission.total_score or 0.0, checkpoint_sections(answer_key), states
    )

    result = await db.execute(
        select(GradePassback).where(GradePassback.submission_id == submission.id)
    )
    passback = result.scalar_one_or_none()
    if passback is None:
        passback = GradePassback(submission_id=submission.id, attempts=0)
        db.add(passback)

    student = await db.get(User, submission.user_id)
    passback.lti_user_id = student.lti_user_id
    launch_context = get_launch_context(request.session, submission.assignment_id)
    passback.lineitem_url = passback.lineitem_url or (
        launch_context["ags_lineitem"] if launch_context is not None else ""
    )
    passback.score_given = score["total"]
    passback.score_maximum = answer_key.get("total_points", submission.max_score or 0)

    try:
        outcome = await _ags_client().post_score(
            lineitem_url=passback.lineitem_url,
            lti_user_id=passback.lti_user_id,
            score_given=passback.score_given,
            score_maximum=passback.score_maximum,
            grading_progress=_grading_progress(answer_key),
        )
        passback.status = outcome["status"]
        passback.attempts += max(outcome["attempts"], 1)
        passback.last_error = ""
        passback.posted_at = datetime.datetime.now(datetime.timezone.utc)
    except AGSError as exc:
        passback.status = "failed"
        passback.attempts += exc.attempts
        passback.last_error = str(exc)[:500]

    await db.commit()
    return passback


def _require_ta(request: Request) -> str | None:
    """Return an error message if the session user is not a TA/instructor."""
    if not request.session.get("user_id"):
        return "Not authenticated. Please launch from Canvas or use /dev/launch."
    if request.session.get("role") not in ("ta", "instructor"):
        return "TA or instructor role required."
    return None


def _build_submission_row(
    submission: Submission,
    student: User,
    answer_key: dict,
    states: dict[str, bool],
    passback: GradePassback | None,
) -> dict:
    """Build a dashboard row from submission data already loaded from storage."""
    checkpoints = checkpoint_sections(answer_key)
    score = effective_score(submission.total_score or 0.0, checkpoints, states)
    flags = (submission.grade_result or {}).get("flags", [])
    return {
        "submission": submission,
        "student": student,
        "score": score,
        "flags": flags,
        "passback": passback,
        "grade_max": answer_key.get("total_points", 0),
    }


async def _submission_row(
    db: AsyncSession, submission: Submission, student: User, answer_key: dict
) -> dict:
    """Load and build one row for an HTMX submission refresh."""
    result = await db.execute(
        select(CheckpointState).where(CheckpointState.submission_id == submission.id)
    )
    states = {cs.checkpoint_id: cs.verified for cs in result.scalars()}

    result = await db.execute(
        select(GradePassback).where(GradePassback.submission_id == submission.id)
    )
    passback = result.scalar_one_or_none()

    return _build_submission_row(submission, student, answer_key, states, passback)


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
    submissions = result.all()
    submission_ids = [submission.id for submission, _student in submissions]

    states_by_submission: dict[int, dict[str, bool]] = {}
    passbacks_by_submission: dict[int, GradePassback] = {}
    if submission_ids:
        result = await db.execute(
            select(CheckpointState).where(
                CheckpointState.submission_id.in_(submission_ids)
            )
        )
        for state in result.scalars():
            states_by_submission.setdefault(state.submission_id, {})[
                state.checkpoint_id
            ] = state.verified

        result = await db.execute(
            select(GradePassback).where(
                GradePassback.submission_id.in_(submission_ids)
            )
        )
        passbacks_by_submission = {
            passback.submission_id: passback for passback in result.scalars()
        }

    rows = [
        _build_submission_row(
            submission,
            student,
            answer_key,
            states_by_submission.get(submission.id, {}),
            passbacks_by_submission.get(submission.id),
        )
        for submission, student in submissions
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

    submission = await _lock_submission(db, submission_id)
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

    now = datetime.datetime.now(datetime.timezone.utc)
    await db.execute(
        _checkpoint_toggle_statement(
            submission_id=submission_id,
            checkpoint_id=checkpoint_id,
            verified_by=request.session["user_id"],
            verified_at=now,
            points=checkpoints[checkpoint_id]["points"],
        )
    )

    result = await db.execute(
        select(GradePassback).where(GradePassback.submission_id == submission_id)
    )
    passback = result.scalar_one_or_none()
    if passback is not None:
        passback.status = "pending"
        passback.posted_at = None
        passback.last_error = ""

    await db.commit()

    student = await db.get(User, submission.user_id)
    row = await _submission_row(db, submission, student, answer_key)
    return templates.TemplateResponse(request, "_ta_row.html", {"row": row})


@router.post("/submission/{submission_id}/post-grade", response_class=HTMLResponse)
async def post_grade(
    request: Request, submission_id: int, db: AsyncSession = Depends(get_db)
):
    """Post one submission's effective score via AGS; returns the row fragment."""
    error = _require_ta(request)
    if error:
        return templates.TemplateResponse(request, "error.html", {"message": error})

    submission = await db.get(Submission, submission_id)
    if not submission:
        return templates.TemplateResponse(request, "error.html", {
            "message": f"Submission {submission_id} not found.",
        })

    answer_key = load_answer_key(submission.assignment_id)
    if not answer_key:
        return templates.TemplateResponse(request, "error.html", {
            "message": f"No answer key found for '{submission.assignment_id}'.",
        })

    await _post_grade(db, request, submission, answer_key)

    student = await db.get(User, submission.user_id)
    row = await _submission_row(db, submission, student, answer_key)
    return templates.TemplateResponse(request, "_ta_row.html", {"row": row})


@router.post("/assignment/{assignment_id}/post-all")
async def post_all_grades(
    request: Request, assignment_id: str, db: AsyncSession = Depends(get_db)
):
    """Post the latest submission per student, then reload the dashboard."""
    error = _require_ta(request)
    if error:
        return templates.TemplateResponse(request, "error.html", {"message": error})

    answer_key = load_answer_key(assignment_id)
    if not answer_key:
        return templates.TemplateResponse(request, "error.html", {
            "message": f"No answer key found for assignment '{assignment_id}'.",
        })

    result = await db.execute(
        select(Submission)
        .where(Submission.assignment_id == assignment_id)
        .order_by(Submission.id.desc())
    )
    latest_per_student: dict[int, Submission] = {}
    for submission in result.scalars():
        latest_per_student.setdefault(submission.user_id, submission)

    for submission in latest_per_student.values():
        await _post_grade(db, request, submission, answer_key)

    return RedirectResponse(url=f"/ta/assignment/{assignment_id}", status_code=303)


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
