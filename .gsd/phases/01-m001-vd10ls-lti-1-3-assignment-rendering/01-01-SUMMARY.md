---
id: S01
parent: M001
milestone: M001
provides:
  - grading-engine-numerical
  - grading-engine-identification
  - dev-lti-bypass
  - assignment-rendering
  - submission-storage
requires:
  []
affects:
  []
key_files:
  - app/main.py
  - app/grading/engine.py
  - app/grading/numerical.py
  - app/routers/dev.py
  - tests/test_grading.py
key_decisions:
  - Dev-mode LTI bypass gated behind DEBUG=true
  - JSON file answer keys from answer_keys directory
  - Synchronous grading, no async queue
  - Session-based auth via SessionMiddleware
patterns_established:
  - (none)
observability_surfaces:
  - none
drill_down_paths:
  []
duration: ""
verification_result: passed
completed_at: 2026-07-14T17:12:06.606Z
blocker_discovered: false
---

# S01: LTI Launch + Single Question Grading Tracer

**Built working FastAPI app proving full grading pipeline: dev-mode LTI launch, Lab01 Q1 rendering, numerical + identification grading, PostgreSQL storage, scored results**

## What Happened

Established the project scaffold and proved the end-to-end pipeline. Built FastAPI app with Pydantic config, async SQLAlchemy + asyncpg, Alembic migrations, session-based auth. Created dev-mode LTI bypass gated behind DEBUG=true. Implemented grading engine with numerical (tolerance + precision) and identification (case-insensitive match). JSON answer key format with Lab01 Q1 (6 questions, 9 pts). Jinja2 templates for assignment form, results page, and TA dashboard, all Canvas iframe compatible. 18 unit tests passing. Committed as 419d298.

## Verification

18 unit tests passing via pytest. Manual browser verification of dev launch flow.

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Operational Readiness

None.

## Deviations

None.

## Known Limitations

None.

## Follow-ups

None.

## Files Created/Modified

None.
