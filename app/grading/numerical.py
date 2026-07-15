import re
from dataclasses import dataclass

_NUMERIC_LITERAL = re.compile(
    r"^[+-]?(?:(?:\d+(?:\.(?P<fraction>\d*))?)|"
    r"(?:\.(?P<leading_fraction>\d+)))"
    r"(?:[eE](?P<exponent>[+-]?\d+))?$"
)


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


def decimal_places(answer: str) -> int | None:
    """Return the decimal resolution expressed by a numeric literal.

    Scientific notation shifts the mantissa's resolution by its exponent:
    ``5.080e0`` carries three decimal places, ``5.080e1`` carries two, and
    ``5080e-3`` carries three. Invalid numeric syntax returns ``None``.
    """
    match = _NUMERIC_LITERAL.fullmatch(answer.strip())
    if match is None:
        return None

    fraction = match.group("fraction")
    if fraction is None:
        fraction = match.group("leading_fraction") or ""
    try:
        exponent = int(match.group("exponent") or "0")
    except ValueError:
        return None
    return len(fraction) - exponent


def has_required_decimal_places(answer: str, precision: int | None) -> bool:
    """Whether ``answer`` expresses at least the requested decimal resolution."""
    if precision is None:
        return True
    expressed_places = decimal_places(answer)
    return expressed_places is not None and expressed_places >= precision


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
        precision: Required decimal places. If set, the answer must have at least
                   this resolution (e.g. precision=2 means "to 0.01").
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

    if not has_required_decimal_places(cleaned, precision):
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
