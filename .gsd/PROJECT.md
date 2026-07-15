# Project

## What This Is

Auto-grading system for physics lab assignments at UTD, integrated into Canvas LMS as an LTI 1.3 tool. Students complete assignments interactively inside Canvas, submissions are auto-graded for deterministic question types (numerical, identification, data tables), and scores are posted to the gradebook via AGS with manual posting policy.

Currently: FastAPI backend with Jinja2/HTMX frontend, PostgreSQL storage, working grading engine for numerical + identification + report + data-table questions across Lab01 (full report) and Lab08 (pre-lab), TA checkpoint verification dashboard, AGS passback client (dry-run until Canvas dev key). Dev-mode LTI bypass for local development. 88 passing tests.

## Core Value

A student launches a physics lab assignment from Canvas, fills in answers, submits, and receives instant scored feedback -- replacing manual TA grading for deterministic question types.

## Project Shape

- **Complexity:** complex
- **Why:** LTI 1.3 integration, multiple question type graders, Canvas iframe constraints, FERPA requirements, TA verification workflows
- **Web stack:** FastAPI + Jinja2/HTMX (server-rendered in Canvas LTI iframe)

## Current State

**Working (committed):**
- FastAPI app with session-based auth and dev-mode LTI bypass
- Grading engine: numerical (tolerance + precision + sig figs), identification, report (value + uncertainty, partial credit), data tables (per-cell + consistency flags vs student's own R1 data, flag-only), short answer (deferred to TA/M2)
- Section-based answer key schema (JSON): Lab01 full report (19 questions + R1/R2/R3 tables, 100-pt budget reconciled) and Lab08 pre-lab (values provisional pending instructor)
- Assignment rendering: section-grouped layout, checkpoint badges, report two-field inputs, editable table grids
- Results page: per-section subtotals, per-cell ✓/✗ with ⚠ consistency flags, checkpoint status, auto/checkpoint/total split
- TA dashboard: submissions list, HTMX checkpoint toggles (carry forward on resubmit), consistency-flag surfacing, AGS posting with status chips
- AGS passback client per LTI 1.3 spec: JWT-assertion token, retry w/ backoff, dry_run/live/disabled modes, per-submission GradePassback tracking
- PostgreSQL schema via Alembic (users, submissions, answer keys, checkpoints, grade_passbacks)
- 88 unit tests all passing (DB-free)

**Blocked externally (see 01-AUDIT.md):**
- Real LTI 1.3 OIDC/JWKS auth + live AGS posting — UTD Canvas admin must issue a developer key; activation is config + launch-claim extraction
- Instructor confirmations: Lab01 table nominals, Lab08 given values, exact sig-fig rules, measurement-field points (D006)

**Not yet done:**
- Human UAT for S03–S06 (deferred by user; checklists in .gsd/phases/01-*/0?-0?-UAT.md)

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
