# Project

## What This Is

Auto-grading system for physics lab assignments at UTD, integrated into Canvas LMS as an LTI 1.3 tool. Students complete assignments interactively inside Canvas, submissions are auto-graded for deterministic question types (numerical, identification, data tables), and scores are posted to the gradebook via AGS with manual posting policy.

Currently: FastAPI backend with Jinja2/HTMX frontend, PostgreSQL storage, working grading engine for numerical + identification + report questions (19 questions, 48 pts across Lab01 Q1-Q4). Dev-mode LTI bypass for local development. 33 passing tests.

## Core Value

A student launches a physics lab assignment from Canvas, fills in answers, submits, and receives instant scored feedback -- replacing manual TA grading for deterministic question types.

## Project Shape

- **Complexity:** complex
- **Why:** LTI 1.3 integration, multiple question type graders, Canvas iframe constraints, FERPA requirements, TA verification workflows
- **Web stack:** FastAPI + Jinja2/HTMX (server-rendered in Canvas LTI iframe)

## Current State

**Working (committed to main):**
- FastAPI app with session-based auth and dev-mode LTI bypass
- Grading engine: numerical (tolerance + precision), identification (case-insensitive match), report (value + uncertainty, partial credit), short answer (deferred to TA/M2)
- Section-based answer key schema (JSON) with 19 questions across 6 sections for Lab01
- Assignment rendering with section-grouped layout, checkpoint badges, report two-field inputs
- Results page with per-section subtotals and TA review indicators
- TA dashboard with section-based layout
- PostgreSQL schema via Alembic (users, submissions, answer keys, checkpoints)
- 33 unit tests all passing

**Not yet built:**
- Data table grading (R1/R2/R3 editable grids) -- next slice
- TA checkpoint verification UI
- AGS grade passback to Canvas
- Lab08 pre-lab format
- Real LTI 1.3 OIDC/JWKS auth (blocked on UTD Canvas admin)

## Architecture / Key Patterns

```
app/
  config.py         -- Pydantic settings (env-based)
  database.py       -- Async SQLAlchemy + asyncpg
  main.py           -- FastAPI app, SessionMiddleware, router includes
  models/           -- SQLAlchemy models (user, submission, answer_key, checkpoint)
  grading/
    numerical.py    -- grade_numerical() with tolerance + precision
    engine.py       -- grade_question(), grade_report(), grade_short_answer(), grade_submission()
  routers/
    lti.py          -- LTI 1.3 endpoints (placeholder)
    dev.py          -- Dev-mode bypass (/dev/launch)
    grading.py      -- /assignment/{id} render + /assignment/{id}/submit grade
  templates/        -- Jinja2 templates (base, assignment, results, error, ta_dashboard)
answer_keys/        -- JSON answer keys per assignment
tests/              -- pytest unit tests for grading engine
```

- **Grading dispatch:** `grade_submission()` iterates questions, dispatches by type to specialized graders
- **Answer keys:** JSON files in `answer_keys/`, loaded at request time (not DB-backed yet)
- **Auth:** Session cookie via Starlette SessionMiddleware; LTI launch sets session user
- **Templates:** Server-rendered Jinja2, Canvas iframe compatible (X-Frame-Options: ALLOWALL)

## Capability Contract

See `.gsd/REQUIREMENTS.md` for the explicit capability contract, requirement status, and coverage mapping.

## Milestone Sequence

- [ ] M001: M001-vd10ls: LTI 1.3 + Assignment Rendering + Numerical/Tabular Grading — Establish the core auto-grading platform — Canvas LTI 1.3 integration, assignment rendering in-browser, and deterministic grading for numerical, identification, data table, and checkpoint question types.
- [ ] M002-z2gqz6:  — Planned.
