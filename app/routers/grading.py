import datetime
import json
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.grading.checkpoints import checkpoint_sections, effective_score
from app.grading.engine import grade_submission
from app.models.checkpoint import CheckpointState
from app.models.passback import GradePassback
from app.models.submission import Submission
from app.models.user import User

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


def _build_section_questions(answer_key: dict) -> list[dict]:
    """Organize questions into sections for template rendering."""
    sections = answer_key.get("sections", [])
    questions = answer_key["questions"]

    if not sections:
        return [{"id": "all", "title": "", "instructions": None, "type": None, "questions": questions}]

    result = []
    for section in sections:
        sec_id = section["id"]
        sec_questions = {
            q_id: q_def for q_id, q_def in questions.items()
            if q_def.get("section") == sec_id
        }
        if sec_questions or section.get("type") in ("checkpoint", "data_table"):
            entry = {
                "id": sec_id,
                "title": section["title"],
                "points": section.get("points", 0),
                "instructions": section.get("instructions"),
                "type": section.get("type"),
                "questions": sec_questions,
            }
            if section.get("type") == "data_table":
                entry["table_id"] = section.get("table")
                entry["table"] = answer_key.get("tables", {}).get(section.get("table"))
            result.append(entry)
    return result


@router.get("/assignment/{assignment_id}", response_class=HTMLResponse)
async def view_assignment(request: Request, assignment_id: str):
    """Render the assignment form for a student or TA dashboard."""
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

    if role in ("ta", "instructor"):
        return RedirectResponse(url=f"/ta/assignment/{assignment_id}", status_code=303)

    section_questions = _build_section_questions(answer_key)

    return templates.TemplateResponse(request, "assignment.html", {
        "assignment_id": assignment_id,
        "title": answer_key.get("title", assignment_id),
        "sections": section_questions,
        "total_points": answer_key.get("total_points", 0),
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

    answer_key = load_answer_key(assignment_id)
    if not answer_key:
        return templates.TemplateResponse(request, "error.html", {
            "message": f"No answer key found for assignment '{assignment_id}'.",
        })

    # Build answers dict, handling report questions (two fields)
    clean_answers: dict[str, str | dict] = {}
    for q_id, q_def in answer_key["questions"].items():
        if q_def["type"] == "report":
            clean_answers[q_id] = {
                "value": form_data.get(f"q_{q_id}_value", ""),
                "error": form_data.get(f"q_{q_id}_error", ""),
            }
        else:
            clean_answers[q_id] = form_data.get(f"q_{q_id}", "")

    # Collect data table cells (inputs named t_{table}_{row}_{col})
    for t_id, t_def in answer_key.get("tables", {}).items():
        clean_answers[t_id] = {
            row["id"]: {
                col["id"]: form_data.get(f"t_{t_id}_{row['id']}_{col['id']}", "")
                for col in t_def.get("columns", [])
            }
            for row in t_def.get("rows", [])
        }

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
    await db.flush()

    # Carry checkpoint verifications forward from the previous submission,
    # so TA-verified items survive a resubmit.
    verified_states = await _carry_forward_checkpoints(db, submission)

    section_results = _build_section_results(answer_key, result)
    checkpoint_summary = effective_score(
        result["total_score"], checkpoint_sections(answer_key), verified_states
    )

    # Record passback intent; the TA posts it from the dashboard.
    student = await db.get(User, user_id)
    db.add(GradePassback(
        submission_id=submission.id,
        lineitem_url=request.session.get("ags_lineitem", ""),
        lti_user_id=student.lti_user_id if student else "",
        score_given=checkpoint_summary["total"],
        score_maximum=answer_key.get("total_points", result["total_max"]),
        status="pending",
    ))
    await db.commit()

    return templates.TemplateResponse(request, "results.html", {
        "assignment_id": assignment_id,
        "title": answer_key.get("title", assignment_id),
        "result": result,
        "section_results": section_results,
        "checkpoint_summary": checkpoint_summary,
        "grade_max": answer_key.get("total_points", result["total_max"]),
    })


async def _carry_forward_checkpoints(
    db: AsyncSession, submission: Submission
) -> dict[str, bool]:
    """Copy checkpoint states from the student's previous submission."""
    prev = await db.execute(
        select(Submission.id)
        .where(
            Submission.user_id == submission.user_id,
            Submission.assignment_id == submission.assignment_id,
            Submission.id != submission.id,
        )
        .order_by(Submission.id.desc())
        .limit(1)
    )
    prev_id = prev.scalar_one_or_none()
    if prev_id is None:
        return {}

    states = await db.execute(
        select(CheckpointState).where(CheckpointState.submission_id == prev_id)
    )
    verified: dict[str, bool] = {}
    for cs in states.scalars():
        db.add(CheckpointState(
            submission_id=submission.id,
            checkpoint_id=cs.checkpoint_id,
            verified=cs.verified,
            verified_by=cs.verified_by,
            verified_at=cs.verified_at,
            points=cs.points,
        ))
        verified[cs.checkpoint_id] = cs.verified
    return verified


def _build_section_results(answer_key: dict, result: dict) -> list[dict]:
    """Organize grading results by section for the results template."""
    sections = answer_key.get("sections", [])
    if not sections:
        return [{"title": "Results", "questions": result["questions"]}]

    output = []
    for section in sections:
        sec_id = section["id"]

        if section.get("type") == "data_table":
            table_id = section.get("table")
            table_result = result.get("tables", {}).get(table_id)
            table_def = answer_key.get("tables", {}).get(table_id)
            if table_result and table_def:
                output.append({
                    "title": section["title"],
                    "points": section.get("points", 0),
                    "score": table_result["score"],
                    "max_score": table_result["max_score"],
                    "type": "data_table",
                    "table_id": table_id,
                    "table": table_def,
                    "table_result": table_result,
                    "questions": {},
                })
            continue

        sec_questions = {}
        for q_id, q_def in answer_key["questions"].items():
            if q_def.get("section") == sec_id and q_id in result["questions"]:
                sec_questions[q_id] = {
                    **result["questions"][q_id],
                    "label": q_def.get("label", q_id),
                    "type": q_def.get("type"),
                }
        if sec_questions:
            sec_score = sum(q["score"] for q in sec_questions.values())
            sec_max = sum(q["max_score"] for q in sec_questions.values())
            output.append({
                "title": section["title"],
                "points": section.get("points", 0),
                "score": sec_score,
                "max_score": sec_max,
                "questions": sec_questions,
            })
    return output
