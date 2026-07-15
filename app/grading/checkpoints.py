"""Checkpoint scoring: TA-verified items layered on top of auto-graded scores.

Checkpoints (Lab Safety Training, Check Box #1/#2) are binary pass/fail items
set by the TA, worth points the grading engine cannot award. The submission's
stored total_score stays auto-graded only; the effective score adds verified
checkpoint points at read time.
"""


def checkpoint_sections(answer_key: dict) -> list[dict]:
    """Extract checkpoint sections from an answer key."""
    return [
        {
            "id": s["id"],
            "title": s["title"],
            "points": s.get("points", 0),
            "instructions": s.get("instructions"),
        }
        for s in answer_key.get("sections", [])
        if s.get("type") == "checkpoint"
    ]


def effective_score(
    auto_score: float, checkpoints: list[dict], verified: dict[str, bool]
) -> dict:
    """Combine the auto-graded score with TA-verified checkpoint points.

    ``verified`` maps checkpoint id -> whether the TA has verified it.
    """
    breakdown = []
    checkpoint_score = 0.0
    checkpoint_max = 0.0
    for cp in checkpoints:
        is_verified = bool(verified.get(cp["id"], False))
        points = cp.get("points", 0)
        checkpoint_max += points
        if is_verified:
            checkpoint_score += points
        breakdown.append({**cp, "verified": is_verified})

    return {
        "auto_score": auto_score,
        "checkpoint_score": checkpoint_score,
        "checkpoint_max": checkpoint_max,
        "total": auto_score + checkpoint_score,
        "checkpoints": breakdown,
    }
