from app.grading.numerical import GradeResult, grade_numerical


def grade_question(question_def: dict, student_answer: str) -> GradeResult:
    """Grade a single question based on its definition from the answer key."""
    q_type = question_def.get("type", "numerical")

    if q_type == "numerical":
        return grade_numerical(
            student_answer=student_answer,
            expected=question_def["expected"],
            tolerance=question_def.get("tolerance", 0.01),
            max_score=question_def["points"],
            precision=question_def.get("precision"),
        )

    if q_type == "identification":
        cleaned = student_answer.strip().upper()
        correct_answers = [a.upper() for a in question_def["accepted"]]
        correct = cleaned in correct_answers
        return GradeResult(
            correct=correct,
            score=question_def["points"] if correct else 0.0,
            max_score=question_def["points"],
            feedback="Correct." if correct else f"Incorrect. Expected one of: {', '.join(question_def['accepted'])}.",
        )

    return GradeResult(
        correct=False,
        score=0.0,
        max_score=question_def.get("points", 0),
        feedback=f"Unknown question type: {q_type}",
    )


def grade_submission(answers: dict[str, str], answer_key: dict) -> dict:
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

    return {
        "questions": results,
        "total_score": total_score,
        "total_max": total_max,
    }
