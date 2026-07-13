# S01: LTI Launch + Single Question Grading Tracer

**Status:** Complete
**Completed:** 2026-07-12
**Commit:** `419d298` on `main`

## What Was Built

A working FastAPI web application that proves the full grading pipeline end-to-end: LTI launch simulation, assignment rendering via Jinja2/HTMX, numerical + identification grading, submission storage in PostgreSQL, and scored results display.

## Architecture

```
Auto-Grader/
├── app/
│   ├── config.py            # Pydantic settings (env-based: DATABASE_URL, SECRET_KEY, DEBUG)
│   ├── database.py          # Async SQLAlchemy engine + session factory (asyncpg)
│   ├── main.py              # FastAPI app with SessionMiddleware, router includes
│   ├── models/
│   │   ├── base.py          # DeclarativeBase
│   │   ├── user.py          # User model (lti_user_id, role, course_id)
│   │   ├── submission.py    # Submission + SubmissionAnswer models (JSON grade_result)
│   │   ├── answer_key.py    # AnswerKey model (DB-backed, not yet used — JSON files for now)
│   │   └── checkpoint.py    # CheckpointState model (TA verification state)
│   ├── grading/
│   │   ├── numerical.py     # grade_numerical() — tolerance + precision checking
│   │   └── engine.py        # grade_question(), grade_submission() — dispatches by type
│   ├── routers/
│   │   ├── lti.py           # LTI 1.3 endpoints (placeholder — real OIDC/JWKS in future)
│   │   ├── dev.py           # Dev-mode bypass: /dev/launch (student), /dev/launch/ta (TA)
│   │   └── grading.py       # /assignment/{id} (render), /assignment/{id}/submit (grade)
│   └── templates/
│       ├── base.html        # Canvas-iframe-compatible base with CSP headers
│       ├── assignment.html  # Dynamic form rendering from answer key JSON
│       ├── results.html     # Per-question score breakdown with correct/incorrect indicators
│       └── error.html       # Error display page
├── answer_keys/
│   └── lab01.json           # Lab01 Q1 answer key (6 questions, 9 points total)
├── alembic/                 # Async PostgreSQL migrations
│   └── versions/
│       └── 4eca25300999_initial_schema.py
├── tests/
│   └── test_grading.py      # 18 unit tests (all passing)
├── docker-compose.yml       # PostgreSQL 16 container
├── pyproject.toml            # Python deps + build config
└── .env.example              # Config template
```

## Key Components

### Grading Engine (`app/grading/`)

- **`grade_numerical(student_answer, expected, tolerance, max_score, precision)`** — Parses string input, checks value within absolute tolerance, optionally validates decimal precision. Returns `GradeResult(correct, score, max_score, feedback)`.
- **`grade_question(question_def, student_answer)`** — Dispatches to type-specific graders (`numerical`, `identification`). Identification uses case-insensitive exact match against accepted values.
- **`grade_submission(answers, answer_key)`** — Grades all questions, returns per-question breakdown + totals.

### Answer Key Format (`answer_keys/lab01.json`)

```json
{
  "assignment_id": "lab01",
  "title": "Lab 1: Measurement & Error",
  "total_points": 9,
  "questions": {
    "q1_1": {
      "type": "identification",
      "label": "(1) Which set has random errors only?",
      "accepted": ["A"],
      "points": 1
    },
    "q1_5a": {
      "type": "numerical",
      "label": "(5) Uncertainty of the stopwatch",
      "expected": 0.01,
      "tolerance": 0.005,
      "points": 2,
      "unit": "s"
    }
  }
}
```

### Dev-Mode LTI Bypass (`app/routers/dev.py`)

- `GET /dev/launch` — Creates a test student user in DB, sets session, redirects to `/assignment/lab01`
- `GET /dev/launch/ta` — Same flow but with `role=ta`
- Only active when `DEBUG=true` in config

### Database Schema

| Table | Purpose |
|-------|---------|
| `users` | LTI user records (pseudonymous ID, role, course) |
| `submissions` | Student answers + grade results (JSON blob) |
| `answer_keys` | DB-backed answer keys (not yet used — JSON files for now) |
| `checkpoint_states` | TA checkpoint verification state |
| `submission_answers` | Per-question answer records |

### Templates

- **Canvas iframe compatible** — base template sets `X-Frame-Options: ALLOWALL` and avoids frame-busting
- **HTMX-ready** — form submission works as standard POST (HTMX partial updates planned for S02+)

## Test Coverage

18 tests in `tests/test_grading.py`:

| Test Class | Count | What's Tested |
|-----------|-------|---------------|
| `TestGradeNumerical` | 10 | Exact match, tolerance boundaries, empty/non-numeric input, precision validation, negative values |
| `TestGradeQuestion` | 4 | Identification correct/wrong/case-insensitive, numerical via engine dispatch |
| `TestGradeSubmission` | 4 | Full/partial submission, missing answers, real Lab01 answer key validation |

## How to Run

```bash
# 1. Start PostgreSQL
docker compose up -d

# 2. Set up environment
cp .env.example .env

# 3. Create database tables
alembic upgrade head

# 4. Run the app
uvicorn app.main:app --reload

# 5. Open in browser
# Student view: http://localhost:8000/dev/launch
# TA view:      http://localhost:8000/dev/launch/ta

# Run tests (no database needed)
pytest
```

## What's NOT Built Yet (Deferred to Later Slices)

- Real LTI 1.3 OIDC/JWKS auth (S01 uses dev-mode bypass) — blocked on UTD Canvas admin
- Lab01 Questions 2 & 3 (calculated values with precision rules) — S02
- Lab01 data tables R1/R2/R3 — S03
- TA checkpoint verification UI — S04
- AGS grade passback to Canvas — S05
- Lab08 pre-lab — S06

## Decisions Made During S01

1. **Dev-mode LTI bypass** — `/dev/launch` endpoint simulates LTI launch for local development without Canvas. Gated behind `DEBUG=true`.
2. **JSON file answer keys** — Answer keys loaded from `answer_keys/` directory rather than database. Simpler for hand-authoring in M1.
3. **Synchronous grading** — No async queue needed for deterministic numerical grading (<100ms per submission).
4. **Session-based auth** — Starlette `SessionMiddleware` with signed cookies. LTI launch sets session; all subsequent requests use session user.
