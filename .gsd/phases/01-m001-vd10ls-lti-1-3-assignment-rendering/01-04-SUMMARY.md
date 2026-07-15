---
id: S04
parent: M001
milestone: M001
provides:
  - ta-submissions-dashboard
  - checkpoint-verification
  - effective-score
requires:
  - slice: S01
    provides: session-roles
  - slice: S03
    provides: consistency-flags
affects:
  []
key_files:
  - app/grading/checkpoints.py
  - app/routers/ta.py
  - app/routers/grading.py
  - app/templates/ta_submissions.html
  - app/templates/_ta_row.html
key_decisions:
  - Effective score computed at read time; submission.total_score stays auto-graded only
  - Checkpoint states are submission-scoped (existing model) and carry forward on resubmit
  - TA landing page is the submissions dashboard; structure view moved to /ta/assignment/{id}/structure
patterns_established:
  - HTMX row-swap fragments (_ta_row.html) for in-place updates
observability_surfaces:
  - S03 consistency flags surfaced per submission on the TA dashboard
drill_down_paths:
  []
duration: ""
verification_result: deferred_uat
completed_at: 2026-07-15
blocker_discovered: false
---

# S04: TA Checkpoint Verification UI

**TA dashboard lists submissions with auto scores and consistency flags; HTMX toggles for the three checkpoint items update the effective total live; verifications survive resubmits**

## What Happened

Added `app/grading/checkpoints.py` (checkpoint extraction + effective-score combination) and `app/routers/ta.py`: submissions dashboard (join Submission×User, newest first), HTMX toggle endpoint that upserts CheckpointState with verified_by/verified_at, and the relocated structure view. TA/instructor role on /assignment/{id} now redirects to the dashboard. Student submit flow carries checkpoint states forward from the previous submission and shows checkpoint status + running total (auto / checkpoints / total-so-far) on the results page. No migration needed — the CheckpointState table existed since S01.

## Verification

57 tests passing (12 new: section extraction, effective-score paths including the exact 100-pt budget, template renders for dashboard/row-fragment/results-checkpoint display). TestClient smoke: route wiring, auth gating on /ta/*.

## Requirements Advanced

- TA checkpoint verification end-to-end (milestone acceptance criterion 5) — DB round-trip pending human UAT.

## Deviations

None.

## Known Limitations

- Dashboard shows all submissions (no per-section filtering yet — single-section dev data makes this moot for M1).
- Toggle endpoint trusts any TA/instructor session for any submission (course-level authorization arrives with real LTI context claims).

## Follow-ups

- S05 will post the effective score (auto + checkpoints) to Canvas via AGS.

## Files Created/Modified

- `app/grading/checkpoints.py` (new), `app/routers/ta.py` (new), `app/routers/grading.py`, `app/main.py`, `app/templates/ta_submissions.html` (new), `app/templates/_ta_row.html` (new), `app/templates/results.html`, `app/templates/base.html`, `tests/test_checkpoints.py` (new)
