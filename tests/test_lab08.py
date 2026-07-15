import json
import math

import pytest
from jinja2 import Environment, FileSystemLoader

from app.grading.engine import grade_submission
from app.grading.numerical import count_sig_figs, grade_numerical
from app.routers.grading import _build_section_questions, _build_section_results


def _lab08():
    with open("answer_keys/lab08.json") as f:
        return json.load(f)


class TestCountSigFigs:
    @pytest.mark.parametrize("answer,expected", [
        ("3.27", 3),
        ("0.0100", 3),
        ("4.90", 3),
        ("3.2", 2),
        ("0.01", 1),
        ("490", 3),        # ambiguous integer trailing zeros counted (permissive)
        ("12.780", 5),
        ("-0.256", 3),
        ("2.56e2", 3),
        ("0", 1),
    ])
    def test_counting(self, answer, expected):
        assert count_sig_figs(answer) == expected


class TestSigFigGrading:
    def test_pass_at_three(self):
        r = grade_numerical("3.27", expected=3.2667, tolerance=0.05, max_score=2, sig_figs=3)
        assert r.correct is True

    def test_fail_too_few(self):
        r = grade_numerical("3.3", expected=3.2667, tolerance=0.05, max_score=2, sig_figs=3)
        assert r.correct is False
        assert "significant figures" in r.feedback

    def test_extra_precision_accepted(self):
        r = grade_numerical("3.2667", expected=3.2667, tolerance=0.05, max_score=2, sig_figs=3)
        assert r.correct is True

    def test_leading_zeros_do_not_count(self):
        r = grade_numerical("0.01", expected=0.0100, tolerance=0.0002, max_score=2, sig_figs=3)
        assert r.correct is False
        r = grade_numerical("0.0100", expected=0.0100, tolerance=0.0002, max_score=2, sig_figs=3)
        assert r.correct is True


class TestLab08Key:
    def test_provisional_key_is_self_consistent(self):
        """The placeholder problem must obey the physics it claims."""
        q = _lab08()["questions"]
        m, big_m, radius, h, g = 0.500, 2.00, 0.100, 1.00, 9.80

        inertia = 0.5 * big_m * radius**2
        a = m * g / (m + big_m / 2)
        assert q["q2_i"]["expected"] == pytest.approx(inertia, rel=1e-3)
        assert q["q2_a"]["expected"] == pytest.approx(a, rel=1e-3)
        # T = m(g - a); τ = T·R
        assert q["q2_t"]["expected"] == pytest.approx(m * (g - a), rel=1e-3)
        assert q["q2_torque"]["expected"] == pytest.approx(
            q["q2_t"]["expected"] * radius, rel=1e-3
        )
        # Energy: U = K_h + K_d
        assert q["q2_u"]["expected"] == pytest.approx(m * g * h, rel=1e-3)
        assert q["q2_v"]["expected"] == pytest.approx(math.sqrt(2 * a * h), rel=1e-3)
        assert q["q2_u"]["expected"] == pytest.approx(
            q["q2_kh"]["expected"] + q["q2_kd"]["expected"], rel=1e-2
        )
        # Part 3: identical disk dropped — ω halves, KE halves, L conserved
        omega_i = q["q2_v"]["expected"] / radius
        assert q["q3_l"]["expected"] == pytest.approx(inertia * omega_i, rel=1e-3)
        assert q["q3_ki"]["expected"] == pytest.approx(q["q2_kd"]["expected"], rel=1e-3)
        assert q["q3_wf"]["expected"] == pytest.approx(omega_i / 2, rel=1e-3)
        assert q["q3_kf"]["expected"] == pytest.approx(q["q3_ki"]["expected"] / 2, rel=1e-2)

    def test_all_correct_submission(self):
        answers = {
            "q1_1": "a = R * alpha (string does not slip)",
            "q1_2": "torque = I * alpha",
            "q2_a": "3.27", "q2_t": "3.27", "q2_torque": "0.327", "q2_i": "0.0100",
            "q2_u": "4.90", "q2_v": "2.56", "q2_kh": "1.63", "q2_kd": "3.27",
            "q3_l": "0.256", "q3_ki": "3.27", "q3_wf": "12.8", "q3_kf": "1.63",
        }
        result = grade_submission(answers, _lab08())
        for q_id in ["q2_a", "q2_t", "q2_torque", "q2_i", "q2_u", "q2_v",
                     "q2_kh", "q2_kd", "q3_l", "q3_ki", "q3_wf", "q3_kf"]:
            assert result["questions"][q_id]["correct"] is True, q_id
        # 30 total − 8 TA-graded derivations = 22 auto-gradeable
        assert result["total_score"] == 22.0
        assert result["total_max"] == 30.0
        assert result["tables"] == {}

    def test_sig_fig_violation_scores_zero(self):
        result = grade_submission({"q2_i": "0.01"}, _lab08())
        assert result["questions"]["q2_i"]["correct"] is False
        assert "significant figures" in result["questions"]["q2_i"]["feedback"]

    def test_renders_with_same_templates(self):
        key = _lab08()
        env = Environment(loader=FileSystemLoader("app/templates"))
        sections = _build_section_questions(key)
        html = env.get_template("assignment.html").render(
            assignment_id="lab08", title=key["title"], sections=sections,
            total_points=key["total_points"], role="student",
        )
        assert "Rotational Motion" in html
        assert 'name="q_q2_a"' in html and 'name="q_q3_kf"' in html
        assert html.count("<textarea") == 2  # the two derivations

        result = grade_submission({"q2_a": "3.27"}, key)
        rendered = env.get_template("results.html").render(
            assignment_id="lab08", title=key["title"], result=result,
            section_results=_build_section_results(key, result),
        )
        assert "Question (2)" in rendered
