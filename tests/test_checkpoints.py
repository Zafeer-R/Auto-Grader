import datetime
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from jinja2 import Environment, FileSystemLoader

from app.grading.checkpoints import checkpoint_sections, effective_score
from app.routers import ta


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


class TestCheckpointPassbackInvalidation:
    async def test_toggle_marks_existing_passback_pending(self, monkeypatch):
        submission = SimpleNamespace(id=7, user_id=2, assignment_id="lab01")
        student = SimpleNamespace(id=2)
        passback = SimpleNamespace(
            status="posted",
            posted_at=datetime.datetime.now(datetime.timezone.utc),
            last_error="old error",
        )

        lock_result = Mock()
        lock_result.scalar_one_or_none.return_value = submission
        toggle_result = Mock()
        passback_result = Mock()
        passback_result.scalar_one_or_none.return_value = passback
        db = SimpleNamespace(
            get=AsyncMock(return_value=student),
            execute=AsyncMock(
                side_effect=[lock_result, toggle_result, passback_result]
            ),
            commit=AsyncMock(),
        )
        request = SimpleNamespace(session={"user_id": 1, "role": "ta"})
        answer_key = {
            "sections": [
                {
                    "id": "safety",
                    "title": "Lab Safety Training",
                    "type": "checkpoint",
                    "points": 10,
                }
            ]
        }
        monkeypatch.setattr(ta, "load_answer_key", lambda _assignment_id: answer_key)
        monkeypatch.setattr(ta, "_submission_row", AsyncMock(return_value={}))
        monkeypatch.setattr(
            ta.templates,
            "TemplateResponse",
            lambda _request, _template, context: context,
        )

        await ta.toggle_checkpoint(request, submission.id, "safety", db)

        assert passback.status == "pending"
        assert passback.posted_at is None
        assert passback.last_error == ""
        db.commit.assert_awaited_once()


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

    def test_lab01_section_budget_and_zero_point_measurement_heading(self):
        key = _lab01()
        assert sum(section.get("points", 0) for section in key["sections"]) == key[
            "total_points"
        ]

        sections = ta._build_section_questions(key)
        measurement = next(
            section for section in sections if section["id"] == "measurement"
        )
        assert measurement["points"] == 0

        html = self._render(
            "assignment.html",
            assignment_id="lab01",
            title=key["title"],
            sections=sections,
            total_points=key["total_points"],
            role="student",
        )
        measurement_heading = html.split("<h2>Measurement", 1)[1].split("</h2>", 1)[
            0
        ]
        assert "pts" not in measurement_heading

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


class TestTaDashboardQueries:
    async def test_batch_loads_row_state_in_constant_queries(self, monkeypatch):
        submissions = [
            SimpleNamespace(
                id=submission_id,
                total_score=5.0,
                grade_result={"flags": [f"flag-{submission_id}"]},
            )
            for submission_id in (11, 12, 13)
        ]
        students = [
            SimpleNamespace(id=student_id, display_name=f"Student {student_id}")
            for student_id in (21, 22, 23)
        ]
        checkpoint_states = [
            SimpleNamespace(
                submission_id=11,
                checkpoint_id="checkpoint",
                verified=True,
            ),
            SimpleNamespace(
                submission_id=12,
                checkpoint_id="checkpoint",
                verified=False,
            ),
        ]
        passback = SimpleNamespace(submission_id=12, status="pending")

        submissions_result = Mock()
        submissions_result.all.return_value = list(zip(submissions, students))
        checkpoints_result = Mock()
        checkpoints_result.scalars.return_value = checkpoint_states
        passbacks_result = Mock()
        passbacks_result.scalars.return_value = [passback]
        db = SimpleNamespace(
            execute=AsyncMock(
                side_effect=[
                    submissions_result,
                    checkpoints_result,
                    passbacks_result,
                ]
            )
        )
        request = SimpleNamespace(session={"user_id": 1, "role": "ta"})
        answer_key = {
            "title": "Test Assignment",
            "total_points": 15,
            "sections": [
                {
                    "id": "checkpoint",
                    "title": "Checkpoint",
                    "type": "checkpoint",
                    "points": 10,
                }
            ],
        }
        single_row_builder = AsyncMock(
            side_effect=AssertionError("dashboard queried per submission")
        )
        monkeypatch.setattr(ta, "load_answer_key", lambda _assignment_id: answer_key)
        monkeypatch.setattr(ta, "_submission_row", single_row_builder)
        monkeypatch.setattr(
            ta.templates,
            "TemplateResponse",
            lambda _request, _template, context: context,
        )

        context = await ta.ta_dashboard(request, "test", db)

        assert db.execute.await_count == 3
        single_row_builder.assert_not_awaited()
        assert [row["score"]["total"] for row in context["rows"]] == [15.0, 5.0, 5.0]
        assert [row["passback"] for row in context["rows"]] == [None, passback, None]
        assert [row["flags"] for row in context["rows"]] == [
            ["flag-11"],
            ["flag-12"],
            ["flag-13"],
        ]
