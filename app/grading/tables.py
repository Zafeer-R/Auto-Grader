"""Data table grading: per-cell numerical grading with consistency flags.

Tables come in two kinds:
- raw (R1): student-collected measurements. No ground truth exists, so cells are
  checked for completeness only (0 points; the TA verifies data via Check Box #2).
- derived (R2, R3): analysis values computed from R1. Cells with an ``expected``
  value in the answer key grade numerically against it; cells without grade for
  a parseable value at the required precision. Every derived cell is also
  cross-checked against the value recomputed from the student's own R1 data —
  mismatches are flagged for TA review but never deducted (instructor policy).
"""

import math
from statistics import mean, stdev

from app.grading.numerical import grade_numerical, has_required_decimal_places


def _parse_cell(raw: str | None) -> float | None:
    if raw is None:
        return None
    cleaned = str(raw).strip()
    if not cleaned:
        return None
    try:
        value = float(cleaned)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def _consistency_tolerance(derived: float, precision: int | None) -> float:
    """Allowance for rounding slop (2 units of last required digit) or 2% relative."""
    rounding = 2 * 10 ** -(precision if precision is not None else 2)
    return max(rounding, 0.02 * abs(derived))


def compute_r1_stats(r1_values: dict, r1_def: dict) -> dict:
    """Derive per-row statistics from raw R1 data.

    Returns {row_id: {"mean", "sd", "seom", "error"}} for rows where all
    trials parsed; rows with missing/garbage cells map to None.
    """
    stats: dict[str, dict | None] = {}
    for row in r1_def.get("rows", []):
        row_id = row["id"]
        row_values = r1_values.get(row_id, {}) if isinstance(r1_values, dict) else {}
        parsed = [_parse_cell(row_values.get(col["id"])) for col in r1_def.get("columns", [])]
        if any(v is None for v in parsed) or len(parsed) < 2:
            stats[row_id] = None
            continue
        try:
            row_mean = mean(parsed)
            row_sd = stdev(parsed)  # sample standard deviation (n-1)
            row_seom = row_sd / math.sqrt(len(parsed))
            instrument = row.get("instrument_uncertainty", 0.0)
            row_error = max(row_seom, instrument)
        except ArithmeticError:
            stats[row_id] = None
            continue
        if not all(math.isfinite(value) for value in (row_mean, row_sd, row_seom, row_error)):
            stats[row_id] = None
            continue
        stats[row_id] = {
            "mean": row_mean,
            "sd": row_sd,
            "seom": row_seom,
            "error": row_error,
        }
    return stats


def compute_r3_derived(r1_stats: dict) -> dict | None:
    """Compute expected R3 values (volume, density) from R1-derived statistics.

    Volume = L*W*T of means; highest/lowest via min/max propagation using each
    row's error; uncertainty = (highest - lowest) / 2. Density = M / V with the
    same propagation (max numerator over min denominator and vice versa).
    """
    needed = ("length", "width", "thickness", "mass")
    if any(r1_stats.get(k) is None for k in needed):
        return None

    length, width, thickness, mass_ = (r1_stats[k] for k in needed)

    v_mean = length["mean"] * width["mean"] * thickness["mean"]
    v_high = (
        (length["mean"] + length["error"])
        * (width["mean"] + width["error"])
        * (thickness["mean"] + thickness["error"])
    )
    v_low = (
        (length["mean"] - length["error"])
        * (width["mean"] - width["error"])
        * (thickness["mean"] - thickness["error"])
    )
    if not all(math.isfinite(value) for value in (v_mean, v_high, v_low)):
        return None
    if v_low <= 0 or v_mean <= 0:
        return None

    d_mean = mass_["mean"] / v_mean
    d_high = (mass_["mean"] + mass_["error"]) / v_low
    d_low = (mass_["mean"] - mass_["error"]) / v_high
    v_uncertainty = (v_high - v_low) / 2
    d_uncertainty = (d_high - d_low) / 2
    if not all(
        math.isfinite(value)
        for value in (d_mean, d_high, d_low, v_uncertainty, d_uncertainty)
    ):
        return None

    return {
        "volume": {
            "mean": v_mean,
            "highest": v_high,
            "lowest": v_low,
            "uncertainty": v_uncertainty,
        },
        "density": {
            "mean": d_mean,
            "highest": d_high,
            "lowest": d_low,
            "uncertainty": d_uncertainty,
        },
    }


def _grade_cell(raw: str | None, cell_def: dict, precision: int | None) -> dict:
    """Grade one derived-table cell.

    With ``expected`` in the cell definition: numerical grading against it.
    Without: full credit for a parseable value at the required precision.
    """
    points = cell_def.get("points", 0.0)
    raw_str = "" if raw is None else str(raw).strip()

    if not raw_str:
        return {
            "correct": False, "score": 0.0, "max_score": points,
            "feedback": "No answer provided.",
        }

    if _parse_cell(raw_str) is None:
        return {
            "correct": False, "score": 0.0, "max_score": points,
            "feedback": f"Could not parse '{raw_str}' as a finite number.",
        }

    if "expected" in cell_def:
        result = grade_numerical(
            student_answer=raw_str,
            expected=cell_def["expected"],
            tolerance=cell_def.get("tolerance", 0.01),
            max_score=points,
            precision=precision,
        )
        return {
            "correct": result.correct, "score": result.score,
            "max_score": result.max_score, "feedback": result.feedback,
        }

    if not has_required_decimal_places(raw_str, precision):
        return {
            "correct": False, "score": 0.0, "max_score": points,
            "feedback": f"Answer must be expressed to {precision} decimal places.",
        }
    return {"correct": True, "score": points, "max_score": points, "feedback": "Recorded."}


def _grade_raw_table(table_def: dict, student_table: dict) -> dict:
    """Completeness check for a raw-data table (0 points)."""
    cells: dict[str, dict] = {}
    filled = 0
    total = 0
    for row in table_def.get("rows", []):
        row_values = student_table.get(row["id"], {}) if isinstance(student_table, dict) else {}
        for col in table_def.get("columns", []):
            total += 1
            raw = row_values.get(col["id"], "")
            ok = _parse_cell(raw) is not None
            filled += ok
            cells[f"{row['id']}.{col['id']}"] = {
                "value": str(raw).strip() if raw else "",
                "correct": ok,
                "score": 0.0,
                "max_score": 0.0,
                "feedback": "Recorded." if ok else "Missing or not a number.",
                "consistent": None,
            }
    complete = filled == total
    return {
        "kind": "raw",
        "cells": cells,
        "score": 0.0,
        "max_score": table_def.get("points", 0.0),
        "complete": complete,
        "flags": [] if complete else [
            f"{table_def.get('title', 'Table')}: {filled}/{total} cells filled — TA will review."
        ],
    }


def _grade_derived_table(
    table_def: dict, student_table: dict, derived: dict | None
) -> dict:
    """Per-cell grading plus consistency flags against R1-derived values."""
    cells: dict[str, dict] = {}
    score = 0.0
    max_score = 0.0
    flags: list[str] = []
    title = table_def.get("title", "Table")

    if derived is None:
        flags.append(
            f"{title}: could not verify against Table R1 data "
            "(R1 incomplete) — TA will review."
        )

    for row in table_def.get("rows", []):
        row_id = row["id"]
        precision = row.get("precision")
        row_values = student_table.get(row_id, {}) if isinstance(student_table, dict) else {}
        row_derived = derived.get(row_id) if derived else None

        for col in table_def.get("columns", []):
            col_id = col["id"]
            cell_def = row.get("cells", {}).get(col_id, {})
            raw = row_values.get(col_id, "")

            graded = _grade_cell(raw, cell_def, precision)
            score += graded["score"]
            max_score += graded["max_score"]

            consistent = None
            value = _parse_cell(raw)
            if row_derived is not None and value is not None:
                expected_from_data = row_derived.get(col_id)
                if expected_from_data is not None:
                    consistent = (
                        abs(value - expected_from_data)
                        <= _consistency_tolerance(expected_from_data, precision)
                    )
                    if not consistent:
                        flags.append(
                            f"{title} — {row.get('label', row_id)} / {col.get('label', col_id)}: "
                            f"entered {value:g}, but your Table R1 data gives "
                            f"{expected_from_data:.{(precision or 2) + 1}f}. "
                            "No points deducted — flagged for TA review."
                        )

            cells[f"{row_id}.{col_id}"] = {
                "value": str(raw).strip() if raw else "",
                **graded,
                "consistent": consistent,
            }

    return {
        "kind": "derived",
        "cells": cells,
        "score": score,
        "max_score": max_score,
        "flags": flags,
    }


def grade_data_tables(tables_def: dict, answers: dict) -> dict:
    """Grade all data tables in an answer key.

    ``answers`` maps table ids to {row_id: {col_id: raw_string}} dicts.
    Returns per-table results plus table score totals and consistency flags.
    Grading never raises on malformed input — bad cells score 0 with feedback.
    """
    results: dict[str, dict] = {}
    total_score = 0.0
    total_max = 0.0
    all_flags: list[str] = []

    r1_def = tables_def.get("r1")
    r1_answers = answers.get("r1", {})
    r1_stats = compute_r1_stats(r1_answers, r1_def) if r1_def else {}
    r3_derived = compute_r3_derived(r1_stats) if r1_stats else None

    for table_id, table_def in tables_def.items():
        student_table = answers.get(table_id, {})
        if not isinstance(student_table, dict):
            student_table = {}

        if table_def.get("kind") == "raw":
            graded = _grade_raw_table(table_def, student_table)
        else:
            # Consistency source: "r1_stats" checks rows against statistics of
            # the student's R1 data; "volume_density" against propagated V/D.
            # Rows lacking a derived value simply skip the consistency check.
            mode = table_def.get("consistency")
            if mode == "volume_density":
                derived = r3_derived
            elif mode == "r1_stats" and any(v is not None for v in r1_stats.values()):
                derived = r1_stats
            else:
                derived = None
            graded = _grade_derived_table(table_def, student_table, derived)

        results[table_id] = graded
        total_score += graded["score"]
        total_max += graded["max_score"]
        all_flags.extend(graded["flags"])

    return {
        "tables": results,
        "total_score": total_score,
        "total_max": total_max,
        "flags": all_flags,
    }
