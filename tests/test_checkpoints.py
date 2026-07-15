import json
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader

from app.grading.checkpoints import checkpoint_sections, effective_score


def _lab01():
    with open("answer_keys/lab01.json") as f:
        return json.load(f)


class TestCheckpointSections:
    def test_lab01_has_three_checkpoints(self):
        cps = checkpoint_sections(_lab01())
        assert [cp["id"] for cp in cps] == ["safety", "checkpoint1", "checkpoint2"]
        assert sum(cp["points"] for cp in cps) == 30

    def test_no_sections(self):
        assert checkpoint_sections({"questions": {}}) == []


class TestEffectiveScore:
    def setup_method(self):
        self.checkpoints = checkpoint_sections(_lab01())

    def test_none_verified(self):
        score = effective_score(64.0, self.checkpoints, {})
        assert score["total"] == 64.0
        assert score["checkpoint_score"] == 0.0
        assert score["checkpoint_max"] == 30.0
        assert all(cp["verified"] is False for cp in score["checkpoints"])

    def test_all_verified(self):
        verified = {"safety": True, "checkpoint1": True, "checkpoint2": True}
        score = effective_score(64.0, self.checkpoints, verified)
        assert score["total"] == 94.0
        assert score["checkpoint_score"] == 30.0

    def test_partial_verified(self):
        score = effective_score(64.0, self.checkpoints, {"safety": True})
        assert score["total"] == 74.0
        assert score["checkpoints"][0]["verified"] is True
        assert score["checkpoints"][1]["verified"] is False

    def test_unverify_after_verify(self):
        # A toggled-off checkpoint (verified=False in the map) awards nothing
        score = effective_score(10.0, self.checkpoints, {"safety": False})
        assert score["total"] == 10.0

    def test_unknown_checkpoint_ids_ignored(self):
        score = effective_score(10.0, self.checkpoints, {"bogus": True})
        assert score["total"] == 10.0

    def test_full_lab01_budget(self):
        # Perfect auto score (70) + all checkpoints (30) = the 100-pt report sheet
        score = effective_score(70.0, self.checkpoints, {
            "safety": True, "checkpoint1": True, "checkpoint2": True,
        })
        assert score["total"] == 100.0


class TestTaDashboardTemplates:
    def _render(self, template, **ctx):
        env = Environment(loader=FileSystemLoader("app/templates"))
        return env.get_template(template).render(**ctx)

    def _row(self, verified):
        key = _lab01()
        score = effective_score(40.0, checkpoint_sections(key), verified)
        return {
            "submission": SimpleNamespace(id=7, submitted_at=None, max_score=70.0),
            "student": SimpleNamespace(display_name="Test Student", lti_user_id="dev-student-001"),
            "score": score,
            "flags": ["Table R2 — Length (cm) / SD: entered 0.9 ..."],
            "grade_max": key["total_points"],
        }

    def test_row_fragment_renders_toggles(self):
        html = self._render("_ta_row.html", row=self._row({"safety": True}))
        assert 'hx-post="/ta/submission/7/checkpoint/safety"' in html
        assert "cp-on" in html and "cp-off" in html
        assert "&#9888; 1" in html  # flag count badge

    def test_dashboard_lists_rows(self):
        key = _lab01()
        html = self._render(
            "ta_submissions.html",
            assignment_id="lab01", title=key["title"],
            rows=[self._row({})], checkpoints=checkpoint_sections(key), role="ta",
        )
        assert "1 submission" in html
        assert "Lab Safety Training" in html
        assert "40.0 / 70.0" in html

    def test_dashboard_empty_state(self):
        key = _lab01()
        html = self._render(
            "ta_submissions.html",
            assignment_id="lab01", title=key["title"],
            rows=[], checkpoints=checkpoint_sections(key), role="ta",
        )
        assert "No submissions yet" in html

    def test_results_page_shows_checkpoint_status(self):
        summary = effective_score(40.0, checkpoint_sections(_lab01()), {"safety": True})
        html = self._render(
            "results.html",
            assignment_id="lab01", title="Lab 1",
            result={"total_score": 40.0, "total_max": 70.0, "questions": {}, "flags": []},
            section_results=[], checkpoint_summary=summary, grade_max=100,
        )
        assert "Pending TA verification" in html
        assert "+10 pts" in html
        assert "Total so far: 50.0 / 100" in html
