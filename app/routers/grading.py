import datetime
import json
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
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
        if sec_questions or section.get("type") == "checkpoint":
            result.append({
                "id": sec_id,
                "title": section["title"],
                "points": section.get("points", 0),
                "instructions": section.get("instructions"),
                "type": section.get("type"),
                "questions": sec_questions,
            })
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

    section_questions = _build_section_questions(answer_key)

    if role in ("ta", "instructor"):
        return templates.TemplateResponse(request, "ta_dashboard.html", {
            "assignment_id": assignment_id,
            "title": answer_key.get("title", assignment_id),
            "sections": section_questions,
            "role": role,
        })

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

    section_results = _build_section_results(answer_key, result)

    return templates.TemplateResponse(request, "results.html", {
        "assignment_id": assignment_id,
        "title": answer_key.get("title", assignment_id),
        "result": result,
        "section_results": section_results,
    })


def _build_section_results(answer_key: dict, result: dict) -> list[dict]:
    """Organize grading results by section for the results template."""
    sections = answer_key.get("sections", [])
    if not sections:
        return [{"title": "Results", "questions": result["questions"]}]

    output = []
    for section in sections:
        sec_id = section["id"]
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
