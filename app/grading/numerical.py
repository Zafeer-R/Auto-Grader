from dataclasses import dataclass


@dataclass
class GradeResult:
    correct: bool
    score: float
    max_score: float
    feedback: str


def count_sig_figs(answer: str) -> int:
    """Count significant figures in a numeric string.

    Leading zeros never count; trailing zeros after a decimal point count.
    Integer trailing zeros are ambiguous ("490" could be 2 or 3 sig figs) —
    counted as significant, the permissive reading for grading.
    """
    cleaned = answer.strip().lstrip("+-")
    if "e" in cleaned.lower():
        cleaned = cleaned.lower().split("e")[0]
    digits = cleaned.replace(".", "")
    stripped = digits.lstrip("0")
    if not stripped:
        # All zeros ("0", "0.00"): every written zero after the first counts
        return max(len(digits) - 1, 1) if digits else 0
    return len(stripped)


def grade_numerical(
    student_answer: str,
    expected: float,
    tolerance: float,
    max_score: float,
    precision: int | None = None,
    sig_figs: int | None = None,
) -> GradeResult:
    """Grade a numerical answer against an expected value with tolerance.

    Args:
        student_answer: The student's answer as a string.
        expected: The expected correct value.
        tolerance: Absolute tolerance for comparison (e.g. 0.01 means +-0.01).
        max_score: Maximum points for this question.
        precision: Required decimal places. If set, the answer must have exactly this many
                   decimal places (e.g. precision=2 means "to 0.01").
        sig_figs: Required significant figures. If set, the answer must carry at
                  least this many (extra precision is accepted).
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

    # Check significant figures if required
    if sig_figs is not None and count_sig_figs(cleaned) < sig_figs:
        return GradeResult(
            correct=False,
            score=0.0,
            max_score=max_score,
            feedback=f"Answer must be expressed to {sig_figs} significant figures.",
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
