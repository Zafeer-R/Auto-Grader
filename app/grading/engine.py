from app.grading.numerical import GradeResult, grade_numerical
from app.grading.tables import grade_data_tables


def grade_question(question_def: dict, student_answer: str | dict) -> GradeResult:
    """Grade a single question based on its definition from the answer key.

    For 'report' type questions, student_answer should be a dict with 'value' and 'error' keys.
    For all other types, student_answer is a string.
    """
    q_type = question_def.get("type", "numerical")

    if q_type == "numerical":
        answer_str = student_answer if isinstance(student_answer, str) else str(student_answer)
        return grade_numerical(
            student_answer=answer_str,
            expected=question_def["expected"],
            tolerance=question_def.get("tolerance", 0.01),
            max_score=question_def["points"],
            precision=question_def.get("precision"),
            sig_figs=question_def.get("sig_figs"),
        )

    if q_type == "identification":
        answer_str = student_answer if isinstance(student_answer, str) else str(student_answer)
        cleaned = answer_str.strip().upper()
        correct_answers = [a.upper() for a in question_def["accepted"]]
        correct = cleaned in correct_answers
        return GradeResult(
            correct=correct,
            score=question_def["points"] if correct else 0.0,
            max_score=question_def["points"],
            feedback="Correct." if correct else f"Incorrect. Expected one of: {', '.join(question_def['accepted'])}.",
        )

    if q_type == "report":
        return grade_report(question_def, student_answer)

    if q_type == "short_answer":
        return grade_short_answer(question_def, student_answer)

    return GradeResult(
        correct=False,
        score=0.0,
        max_score=question_def.get("points", 0),
        feedback=f"Unknown question type: {q_type}",
    )


def grade_report(question_def: dict, student_answer: str | dict) -> GradeResult:
    """Grade a report question (value +/- error, two separate fields).

    student_answer should be a dict with 'value' and 'error' keys,
    or we parse from a single string if needed.
    """
    max_score = question_def["points"]

    if isinstance(student_answer, dict):
        value_str = student_answer.get("value", "").strip()
        error_str = student_answer.get("error", "").strip()
    elif isinstance(student_answer, str) and student_answer.strip():
        # Try to parse "value +/- error" format as fallback
        parts = student_answer.replace("±", "+/-").replace("+-", "+/-").split("+/-")
        if len(parts) == 2:
            value_str = parts[0].strip()
            error_str = parts[1].strip()
        else:
            value_str = student_answer.strip()
            error_str = ""
    else:
        return GradeResult(
            correct=False, score=0.0, max_score=max_score,
            feedback="No answer provided.",
        )

    if not value_str and not error_str:
        return GradeResult(
            correct=False, score=0.0, max_score=max_score,
            feedback="No answer provided.",
        )

    # Grade value component
    value_result = grade_numerical(
        student_answer=value_str,
        expected=question_def["expected_value"],
        tolerance=question_def.get("value_tolerance", 0.01),
        max_score=max_score / 2,
        precision=question_def.get("precision"),
    )

    # Grade error component
    error_result = grade_numerical(
        student_answer=error_str,
        expected=question_def["expected_error"],
        tolerance=question_def.get("error_tolerance", 0.01),
        max_score=max_score / 2,
        precision=question_def.get("precision"),
    )

    total_score = value_result.score + error_result.score
    both_correct = value_result.correct and error_result.correct

    feedback_parts = []
    if value_result.correct:
        feedback_parts.append("Value: Correct.")
    else:
        feedback_parts.append(f"Value: {value_result.feedback}")
    if error_result.correct:
        feedback_parts.append("Uncertainty: Correct.")
    else:
        feedback_parts.append(f"Uncertainty: {error_result.feedback}")

    return GradeResult(
        correct=both_correct,
        score=total_score,
        max_score=max_score,
        feedback=" ".join(feedback_parts),
    )


def grade_short_answer(question_def: dict, student_answer: str | dict) -> GradeResult:
    """Handle short answer questions — deferred to M2 for LLM grading."""
    max_score = question_def["points"]
    answer_str = student_answer if isinstance(student_answer, str) else str(student_answer)
    if answer_str.strip():
        return GradeResult(
            correct=False,
            score=0.0,
            max_score=max_score,
            feedback="Answer recorded. This question will be graded by your TA.",
        )
    return GradeResult(
        correct=False,
        score=0.0,
        max_score=max_score,
        feedback="No answer provided. This question will be graded by your TA.",
    )


def grade_submission(answers: dict[str, str | dict], answer_key: dict) -> dict:
    """Grade a full submission against an answer key.

    Returns a dict with per-question results and totals.
    """
    results = {}
    total_score = 0.0
    total_max = 0.0

    for q_id, q_def in answer_key["questions"].items():
        student_answer = answers.get(q_id, "")
        result = grade_question(q_def, student_answer)
        results[q_id] = {
            "correct": result.correct,
            "score": result.score,
            "max_score": result.max_score,
            "feedback": result.feedback,
        }
        total_score += result.score
        total_max += result.max_score

    tables_result = None
    if answer_key.get("tables"):
        tables_result = grade_data_tables(answer_key["tables"], answers)
        total_score += tables_result["total_score"]
        total_max += tables_result["total_max"]

    return {
        "questions": results,
        "tables": tables_result["tables"] if tables_result else {},
        "flags": tables_result["flags"] if tables_result else [],
        "total_score": total_score,
        "total_max": total_max,
    }
