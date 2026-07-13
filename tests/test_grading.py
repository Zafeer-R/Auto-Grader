import json

import pytest

from app.grading.numerical import grade_numerical
from app.grading.engine import grade_question, grade_report, grade_short_answer, grade_submission


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

        # Total auto-gradeable: 9 (Q1) + 2 (meas) + 15 (Q2) + 12 (Q3) + 4 (Q4_1) = 42
        assert result["total_score"] == 42.0

    def test_lab01_total_max(self):
        """Verify total max points matches expected from answer key."""
        with open("answer_keys/lab01.json") as f:
            answer_key = json.load(f)

        result = grade_submission({}, answer_key)
        # All questions contribute to max, including deferred short_answer
        expected_max = sum(q["points"] for q in answer_key["questions"].values())
        assert result["total_max"] == expected_max
