from dataclasses import dataclass


@dataclass
class GradeResult:
    correct: bool
    score: float
    max_score: float
    feedback: str


def grade_numerical(
    student_answer: str,
    expected: float,
    tolerance: float,
    max_score: float,
    precision: int | None = None,
) -> GradeResult:
    """Grade a numerical answer against an expected value with tolerance.

    Args:
        student_answer: The student's answer as a string.
        expected: The expected correct value.
        tolerance: Absolute tolerance for comparison (e.g. 0.01 means +-0.01).
        max_score: Maximum points for this question.
        precision: Required decimal places. If set, the answer must have exactly this many
                   decimal places (e.g. precision=2 means "to 0.01").
    """
    cleaned = student_answer.strip()
    if not cleaned:
        return GradeResult(
            correct=False, score=0.0, max_score=max_score, feedback="No answer provided."
        )

    try:
        value = float(cleaned)
    except ValueError:
        return GradeResult(
            correct=False,
            score=0.0,
            max_score=max_score,
            feedback=f"Could not parse '{cleaned}' as a number.",
        )

    # Check precision (decimal places) if required
    if precision is not None:
        if "." in cleaned:
            decimal_places = len(cleaned.rstrip("0").split(".")[-1])
            # Also check the raw decimal places (before stripping trailing zeros)
            raw_decimal_places = len(cleaned.split(".")[-1])
        else:
            decimal_places = 0
            raw_decimal_places = 0

        # Accept if the student wrote at least the required precision
        if raw_decimal_places < precision:
            return GradeResult(
                correct=False,
                score=0.0,
                max_score=max_score,
                feedback=f"Answer must be expressed to {precision} decimal places.",
            )

    # Check value within tolerance
    if abs(value - expected) <= tolerance:
        return GradeResult(
            correct=True, score=max_score, max_score=max_score, feedback="Correct."
        )

    return GradeResult(
        correct=False,
        score=0.0,
        max_score=max_score,
        feedback=f"Incorrect. Expected a value near {expected}.",
    )
