import json

import pytest

from app.grading.numerical import grade_numerical
from app.grading.engine import grade_question, grade_submission


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

    def test_numerical_via_engine(self):
        q_def = {"type": "numerical", "expected": 0.01, "tolerance": 0.005, "points": 2}
        r = grade_question(q_def, "0.01")
        assert r.correct is True


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

    def test_lab01_answer_key(self):
        """Test against the actual Lab01 answer key file."""
        with open("answer_keys/lab01.json") as f:
            answer_key = json.load(f)

        answers = {
            "q1_1": "A",
            "q1_2": "C",
            "q1_3": "B",
            "q1_4": "B",
            "q1_5a": "0.01",
            "q1_5b": "0.05",
        }
        result = grade_submission(answers, answer_key)
        assert result["total_score"] == 9.0
        assert result["total_max"] == 9.0
