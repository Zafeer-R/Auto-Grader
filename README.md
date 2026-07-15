# Auto-Grader: Physics Lab Auto-Grading System

Auto-grading system for physics lab assignments at UTD, integrated into Canvas LMS as an LTI 1.3 tool. Students complete assignments interactively inside Canvas, submissions are auto-graded, and scores are posted to the gradebook via AGS.

## Tech Stack

- **Backend:** Python 3.11+ / FastAPI
- **Database:** PostgreSQL 16
- **Frontend:** Jinja2 templates / HTMX (server-rendered in Canvas LTI iframe)
- **Migrations:** Alembic (async)

## Quick Start

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

## Project Documentation

All project tracking lives in `.gsd/`:

- **`.gsd/PROJECT.md`** — project overview, current state, architecture
- **`.gsd/ROADMAP.md`** — milestone registry
- **`.gsd/DECISIONS.md`** — architectural decision log
- **`.gsd/KNOWLEDGE.md`** — project rules and patterns
- **`.gsd/CODEBASE.md`** — structural file map
- **`.gsd/phases/`** — milestone context, slice plans, summaries, and acceptance results

## Current Status

**Milestone M001** (LTI 1.3 + Assignment Rendering + Numerical/Tabular Grading) is code-complete:

- **S01** (LTI Launch + Single Question Grading) — complete
- **S02** (Full Numerical + ID Grading, Q1-Q4) — complete
- **S03** (Data Table Grading R1/R2/R3) — complete
- **S04** (TA Checkpoint Verification UI) — complete
- **S05** (AGS Grade Passback to Canvas) — complete in dry-run; live posting awaits the UTD Canvas developer key
- **S06** (Lab08 Pre-lab Format) — complete; expected values provisional pending instructor

Human UAT for S03–S06 is deferred — checklists live in `.gsd/phases/01-*/`,
and `.gsd/phases/01-*/01-AUDIT.md` tracks what blocks archiving the milestone.
