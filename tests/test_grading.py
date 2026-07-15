import json

import pytest

from app.grading.engine import grade_question, grade_report, grade_short_answer, grade_submission
from app.grading.numerical import grade_numerical
from app.grading.tables import compute_r1_stats, compute_r3_derived, grade_data_tables


class TestGradeNumerical:
    def test_exact_match(self):
        r = grade_numerical("0.01", expected=0.01, tolerance=0.005, max_score=2)
        assert r.correct is True
        assert r.score == 2

    def test_within_tolerance(self):
        r = grade_numerical("0.012", expected=0.01, tolerance=0.005, max_score=2)
        assert r.correct is True

    def test_outside_tolerance(self):
        r = grade_numerical("0.05", expected=0.01, tolerance=0.005, max_score=2)
        assert r.correct is False
        assert r.score == 0.0

    def test_empty_answer(self):
        r = grade_numerical("", expected=0.01, tolerance=0.005, max_score=2)
        assert r.correct is False
        assert "No answer" in r.feedback

    def test_non_numeric(self):
        r = grade_numerical("abc", expected=0.01, tolerance=0.005, max_score=2)
        assert r.correct is False
        assert "parse" in r.feedback.lower()

    def test_precision_required_pass(self):
        r = grade_numerical("3.14", expected=3.14, tolerance=0.01, max_score=3, precision=2)
        assert r.correct is True

    def test_precision_required_fail(self):
        r = grade_numerical("3.1", expected=3.14, tolerance=0.1, max_score=3, precision=2)
        assert r.correct is False
        assert "decimal places" in r.feedback

    def test_negative_value(self):
        r = grade_numerical("-0.5", expected=-0.5, tolerance=0.01, max_score=1)
        assert r.correct is True

    def test_boundary_tolerance(self):
        r = grade_numerical("0.015", expected=0.01, tolerance=0.005, max_score=2)
        assert r.correct is True

    def test_just_outside_tolerance(self):
        r = grade_numerical("0.016", expected=0.01, tolerance=0.005, max_score=2)
        assert r.correct is False

    def test_precision_with_trailing_zeros(self):
        r = grade_numerical("3.10", expected=3.10, tolerance=0.01, max_score=3, precision=2)
        assert r.correct is True

    def test_precision_too_many_decimals_still_passes(self):
        r = grade_numerical("3.140", expected=3.14, tolerance=0.01, max_score=3, precision=2)
        assert r.correct is True


class TestGradeQuestion:
    def test_identification_correct(self):
        q_def = {"type": "identification", "accepted": ["A"], "points": 1}
        r = grade_question(q_def, "A")
        assert r.correct is True
        assert r.score == 1

    def test_identification_case_insensitive(self):
        q_def = {"type": "identification", "accepted": ["A"], "points": 1}
        r = grade_question(q_def, "a")
        assert r.correct is True

    def test_identification_wrong(self):
        q_def = {"type": "identification", "accepted": ["A"], "points": 1}
        r = grade_question(q_def, "B")
        assert r.correct is False

    def test_identification_multiple_accepted(self):
        q_def = {"type": "identification", "accepted": ["aluminum", "aluminium", "al"], "points": 4}
        assert grade_question(q_def, "aluminum").correct is True
        assert grade_question(q_def, "Aluminium").correct is True
        assert grade_question(q_def, "AL").correct is True
        assert grade_question(q_def, "copper").correct is False

    def test_numerical_via_engine(self):
        q_def = {"type": "numerical", "expected": 0.01, "tolerance": 0.005, "points": 2}
        r = grade_question(q_def, "0.01")
        assert r.correct is True

    def test_unknown_type(self):
        q_def = {"type": "fancy", "points": 1}
        r = grade_question(q_def, "something")
        assert r.correct is False
        assert "Unknown" in r.feedback


class TestGradeReport:
    def test_both_correct(self):
        q_def = {
            "type": "report",
            "expected_value": 3.81,
            "expected_error": 0.01,
            "value_tolerance": 0.50,
            "error_tolerance": 0.50,
            "precision": 2,
            "points": 3,
        }
        r = grade_report(q_def, {"value": "3.81", "error": "0.01"})
        assert r.correct is True
        assert r.score == 3.0
        assert "Value: Correct" in r.feedback
        assert "Uncertainty: Correct" in r.feedback

    def test_value_correct_error_wrong(self):
        q_def = {
            "type": "report",
            "expected_value": 3.81,
            "expected_error": 0.01,
            "value_tolerance": 0.05,
            "error_tolerance": 0.005,
            "precision": 2,
            "points": 4,
        }
        r = grade_report(q_def, {"value": "3.81", "error": "0.50"})
        assert r.correct is False
        assert r.score == 2.0  # Half points for value
        assert "Value: Correct" in r.feedback
        assert "Uncertainty: Incorrect" in r.feedback

    def test_both_wrong(self):
        q_def = {
            "type": "report",
            "expected_value": 3.81,
            "expected_error": 0.01,
            "value_tolerance": 0.05,
            "error_tolerance": 0.005,
            "precision": 2,
            "points": 4,
        }
        r = grade_report(q_def, {"value": "9.99", "error": "9.99"})
        assert r.correct is False
        assert r.score == 0.0

    def test_empty_answer(self):
        q_def = {
            "type": "report",
            "expected_value": 3.81,
            "expected_error": 0.01,
            "value_tolerance": 0.50,
            "error_tolerance": 0.50,
            "points": 3,
        }
        r = grade_report(q_def, {"value": "", "error": ""})
        assert r.correct is False
        assert r.score == 0.0

    def test_string_fallback_parsing(self):
        q_def = {
            "type": "report",
            "expected_value": 3.81,
            "expected_error": 0.01,
            "value_tolerance": 0.50,
            "error_tolerance": 0.50,
            "precision": 2,
            "points": 3,
        }
        r = grade_report(q_def, "3.81 +/- 0.01")
        assert r.correct is True

    def test_string_with_plusminus_symbol(self):
        q_def = {
            "type": "report",
            "expected_value": 11.97,
            "expected_error": 0.04,
            "value_tolerance": 0.50,
            "error_tolerance": 0.50,
            "precision": 2,
            "points": 3,
        }
        r = grade_report(q_def, "11.97 \u00b1 0.04")
        assert r.correct is True

    def test_precision_enforced(self):
        q_def = {
            "type": "report",
            "expected_value": 3.81,
            "expected_error": 0.01,
            "value_tolerance": 0.50,
            "error_tolerance": 0.50,
            "precision": 2,
            "points": 4,
        }
        # Value has only 1 decimal place — should fail precision check
        r = grade_report(q_def, {"value": "3.8", "error": "0.01"})
        assert r.score == 2.0  # Only error half scores


class TestGradeShortAnswer:
    def test_with_answer(self):
        q_def = {"type": "short_answer", "points": 6, "grading": "deferred_m2"}
        r = grade_short_answer(q_def, "Random errors and systematic errors")
        assert r.correct is False
        assert r.score == 0.0
        assert "TA" in r.feedback

    def test_empty_answer(self):
        q_def = {"type": "short_answer", "points": 6, "grading": "deferred_m2"}
        r = grade_short_answer(q_def, "")
        assert r.correct is False
        assert "No answer" in r.feedback


def _lab01_tables():
    with open("answer_keys/lab01.json") as f:
        return json.load(f)["tables"]


# Consistent student data: L/W/T measured with calipers, M with balance.
# Stats below are hand-derived from these trials.
R1_ANSWERS = {
    "length": {"1": "5.08", "2": "5.09", "3": "5.07", "4": "5.08", "5": "5.08"},
    "width": {"1": "2.54", "2": "2.55", "3": "2.53", "4": "2.54", "5": "2.54"},
    "thickness": {"1": "0.64", "2": "0.64", "3": "0.63", "4": "0.65", "5": "0.64"},
    "mass": {"1": "22.30", "2": "22.31", "3": "22.29", "4": "22.30", "5": "22.30"},
}

R2_ANSWERS = {
    "length": {"mean": "5.080", "sd": "0.007", "seom": "0.003", "error": "0.005"},
    "width": {"mean": "2.540", "sd": "0.007", "seom": "0.003", "error": "0.005"},
    "thickness": {"mean": "0.640", "sd": "0.007", "seom": "0.003", "error": "0.005"},
    "mass": {"mean": "22.30", "sd": "0.01", "seom": "0.00", "error": "0.01"},
}

R3_ANSWERS = {
    "volume": {"mean": "8.26", "highest": "8.35", "lowest": "8.17", "uncertainty": "0.09"},
    "density": {"mean": "2.70", "highest": "2.73", "lowest": "2.67", "uncertainty": "0.03"},
}


class TestR1Stats:
    def test_stats_derivation(self):
        tables = _lab01_tables()
        stats = compute_r1_stats(R1_ANSWERS, tables["r1"])
        assert stats["length"]["mean"] == pytest.approx(5.08)
        assert stats["length"]["sd"] == pytest.approx(0.00707, abs=1e-4)
        assert stats["length"]["seom"] == pytest.approx(0.00316, abs=1e-4)
        # Error = max(SEOM, instrument uncertainty): calipers 0.005 wins
        assert stats["length"]["error"] == pytest.approx(0.005)
        # Balance uncertainty 0.01 wins for mass
        assert stats["mass"]["error"] == pytest.approx(0.01)

    def test_incomplete_row_is_none(self):
        tables = _lab01_tables()
        bad_mass = {"1": "22.30", "2": "", "3": "x", "4": "22.30", "5": "22.30"}
        partial = {**R1_ANSWERS, "mass": bad_mass}
        stats = compute_r1_stats(partial, tables["r1"])
        assert stats["mass"] is None
        assert stats["length"] is not None

    def test_r3_derivation(self):
        tables = _lab01_tables()
        stats = compute_r1_stats(R1_ANSWERS, tables["r1"])
        derived = compute_r3_derived(stats)
        assert derived["volume"]["mean"] == pytest.approx(8.258, abs=0.001)
        assert derived["density"]["mean"] == pytest.approx(2.700, abs=0.005)
        vol = derived["volume"]
        assert vol["highest"] > vol["mean"] > vol["lowest"]
        assert derived["density"]["uncertainty"] == pytest.approx(0.03, abs=0.005)

    def test_r3_derivation_missing_row(self):
        tables = _lab01_tables()
        stats = compute_r1_stats({**R1_ANSWERS, "mass": {}}, tables["r1"])
        assert compute_r3_derived(stats) is None


class TestGradeDataTables:
    def test_consistent_submission_full_score_no_flags(self):
        tables = _lab01_tables()
        result = grade_data_tables(
            tables, {"r1": R1_ANSWERS, "r2": R2_ANSWERS, "r3": R3_ANSWERS}
        )
        assert result["total_score"] == pytest.approx(24.0)
        assert result["total_max"] == pytest.approx(24.0)
        assert result["flags"] == []
        assert result["tables"]["r1"]["complete"] is True

    def test_inconsistent_value_keeps_points_but_flags(self):
        # SD wildly off from own R1 data but parseable at precision:
        # per instructor policy the cell keeps its points, flagged for TA.
        tables = _lab01_tables()
        r2 = {**R2_ANSWERS, "length": {**R2_ANSWERS["length"], "sd": "0.900"}}
        result = grade_data_tables(tables, {"r1": R1_ANSWERS, "r2": r2, "r3": R3_ANSWERS})
        assert result["total_score"] == pytest.approx(24.0)
        assert len(result["flags"]) == 1
        assert "Length" in result["flags"][0] and "SD" in result["flags"][0]
        assert result["tables"]["r2"]["cells"]["length.sd"]["consistent"] is False

    def test_precision_enforced_on_cells(self):
        tables = _lab01_tables()
        r2 = {**R2_ANSWERS, "length": {**R2_ANSWERS["length"], "sd": "0.1"}}
        result = grade_data_tables(tables, {"r1": R1_ANSWERS, "r2": r2, "r3": R3_ANSWERS})
        cell = result["tables"]["r2"]["cells"]["length.sd"]
        assert cell["correct"] is False
        assert "decimal places" in cell["feedback"]
        assert result["total_score"] == pytest.approx(24.0 - 0.75)

    def test_nominal_expected_enforced_on_mean(self):
        tables = _lab01_tables()
        r3 = {**R3_ANSWERS, "density": {**R3_ANSWERS["density"], "mean": "8.90"}}
        result = grade_data_tables(tables, {"r1": R1_ANSWERS, "r2": R2_ANSWERS, "r3": r3})
        cell = result["tables"]["r3"]["cells"]["density.mean"]
        assert cell["correct"] is False
        assert cell["score"] == 0.0

    def test_empty_cell_scores_zero(self):
        tables = _lab01_tables()
        r2 = {**R2_ANSWERS, "length": {**R2_ANSWERS["length"], "error": ""}}
        result = grade_data_tables(tables, {"r1": R1_ANSWERS, "r2": r2, "r3": R3_ANSWERS})
        cell = result["tables"]["r2"]["cells"]["length.error"]
        assert cell["score"] == 0.0
        assert "No answer" in cell["feedback"]

    def test_garbage_cell_scores_zero_no_crash(self):
        tables = _lab01_tables()
        r2 = {**R2_ANSWERS, "mass": {**R2_ANSWERS["mass"], "seom": "lots"}}
        result = grade_data_tables(tables, {"r1": R1_ANSWERS, "r2": r2, "r3": R3_ANSWERS})
        cell = result["tables"]["r2"]["cells"]["mass.seom"]
        assert cell["score"] == 0.0
        assert "parse" in cell["feedback"].lower()

    def test_missing_r1_skips_consistency_grades_rest(self):
        tables = _lab01_tables()
        result = grade_data_tables(tables, {"r2": R2_ANSWERS, "r3": R3_ANSWERS})
        # Cells still grade (nominal/precision), consistency could not run
        assert result["total_score"] == pytest.approx(24.0)
        r2_flags = result["tables"]["r2"]["flags"]
        assert any("could not verify" in f for f in r2_flags)
        assert result["tables"]["r2"]["cells"]["length.sd"]["consistent"] is None
        assert result["tables"]["r1"]["complete"] is False

    def test_empty_submission_zero_scores(self):
        tables = _lab01_tables()
        result = grade_data_tables(tables, {})
        assert result["total_score"] == 0.0
        assert result["total_max"] == pytest.approx(24.0)


class TestGradeSubmission:
    def test_full_submission(self):
        answer_key = {
            "questions": {
                "q1": {"type": "identification", "accepted": ["A"], "points": 1},
                "q2": {"type": "numerical", "expected": 3.14, "tolerance": 0.01, "points": 3},
            }
        }
        result = grade_submission({"q1": "A", "q2": "3.14"}, answer_key)
        assert result["total_score"] == 4.0
        assert result["total_max"] == 4.0
        assert result["questions"]["q1"]["correct"] is True
        assert result["questions"]["q2"]["correct"] is True

    def test_partial_submission(self):
        answer_key = {
            "questions": {
                "q1": {"type": "identification", "accepted": ["A"], "points": 1},
                "q2": {"type": "numerical", "expected": 3.14, "tolerance": 0.01, "points": 3},
            }
        }
        result = grade_submission({"q1": "B", "q2": "3.14"}, answer_key)
        assert result["total_score"] == 3.0
        assert result["total_max"] == 4.0

    def test_missing_answer(self):
        answer_key = {
            "questions": {
                "q1": {"type": "identification", "accepted": ["A"], "points": 1},
            }
        }
        result = grade_submission({}, answer_key)
        assert result["total_score"] == 0.0

    def test_report_in_submission(self):
        answer_key = {
            "questions": {
                "r1": {
                    "type": "report",
                    "expected_value": 3.81,
                    "expected_error": 0.01,
                    "value_tolerance": 0.50,
                    "error_tolerance": 0.50,
                    "precision": 2,
                    "points": 3,
                },
            }
        }
        result = grade_submission(
            {"r1": {"value": "3.81", "error": "0.01"}},
            answer_key,
        )
        assert result["total_score"] == 3.0
        assert result["questions"]["r1"]["correct"] is True

    def test_lab01_answer_key(self):
        """Test against the actual Lab01 answer key file."""
        with open("answer_keys/lab01.json") as f:
            answer_key = json.load(f)

        # All correct answers for auto-gradeable questions
        answers = {
            "q1_1": "A",
            "q1_2": "C",
            "q1_3": "B",
            "q1_4": "B",
            "q1_5a": "0.01",
            "q1_5b": "0.05",
            "meas_balance": "0.01",
            "meas_calipers": "0.005",
            "q2_1": "3.81",
            "q2_2": "0.01",
            "q2_3": "0.00",
            "q2_4": "0.01",
            "q2_5": {"value": "3.81", "error": "0.01"},
            "q3_1": "11.97",
            "q3_2": "12.01",
            "q3_3": "11.93",
            "q3_4": {"value": "11.97", "error": "0.04"},
            "q4_1": "aluminum",
            "q4_2": "Random errors from measurement and systematic errors from instruments",
            "r1": R1_ANSWERS,
            "r2": R2_ANSWERS,
            "r3": R3_ANSWERS,
        }
        result = grade_submission(answers, answer_key)

        # Check all auto-gradeable questions are correct
        for q_id in ["q1_1", "q1_2", "q1_3", "q1_4", "q1_5a", "q1_5b",
                      "meas_balance", "meas_calipers",
                      "q2_1", "q2_2", "q2_3", "q2_4", "q2_5",
                      "q3_1", "q3_2", "q3_3", "q3_4",
                      "q4_1"]:
            assert result["questions"][q_id]["correct"] is True, f"{q_id} should be correct"

        # q4_2 is short answer — always scored 0 until TA grading
        assert result["questions"]["q4_2"]["score"] == 0.0

        # Consistent tables carry no flags
        assert result["flags"] == []

        # Auto-gradeable: 9 (Q1) + 15 (Q2) + 12 (Q3) + 4 (Q4_1) + 24 (R2+R3) = 64
        # (measurement uncertainties are 0-pt fields per the report sheet)
        assert result["total_score"] == 64.0

    def test_lab01_total_max(self):
        """Verify total max points matches expected from answer key."""
        with open("answer_keys/lab01.json") as f:
            answer_key = json.load(f)

        result = grade_submission({}, answer_key)
        # Questions plus data tables contribute to max (checkpoints are TA-scored)
        expected_max = sum(q["points"] for q in answer_key["questions"].values())
        expected_max += sum(t["points"] for t in answer_key["tables"].values())
        assert result["total_max"] == expected_max
        # Questions (46) + tables (24) + TA checkpoints (30) = 100-pt report sheet
        checkpoint_pts = sum(
            s["points"] for s in answer_key["sections"] if s.get("type") == "checkpoint"
        )
        assert result["total_max"] + checkpoint_pts == answer_key["total_points"]
