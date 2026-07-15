---
id: S05
parent: M001
milestone: M001
provides:
  - ags-client
  - grade-passback-tracking
  - ta-grade-posting
requires:
  - slice: S02
    provides: grading-engine
  - slice: S04
    provides: effective-score
affects:
  []
key_files:
  - app/services/ags.py
  - app/models/passback.py
  - alembic/versions/b7d41f08c2a9_add_grade_passbacks.py
  - app/routers/ta.py
key_decisions:
  - Passback trigger is explicit TA action (Post / Post All), not automatic on toggle
  - Effective score recomputed at post time; Post All posts latest submission per student
  - dry_run mode is the dev default — full flow demoable without Canvas
  - Retry policy — 3 attempts, exponential backoff, transient-only (5xx/429/network); 4xx immediate
patterns_established:
  - app/services/ for external integrations
observability_surfaces:
  - Per-submission passback chips (pending/posted/dry run/failed+error) on TA dashboard
drill_down_paths:
  []
duration: ""
verification_result: deferred_uat
completed_at: 2026-07-15
blocker_discovered: true
---

# S05: AGS Grade Passback to Canvas

**AGS score passback implemented end-to-end against the spec — token via JWT-assertion client_credentials, score POST, retry with backoff, per-submission status tracking, TA posting UI — with live Canvas activation pending the UTD developer key**

## What Happened

Built `app/services/ags.py` (AGSClient): signed RS256 client assertion → platform token endpoint → POST `{lineitem}/scores` with the AGS score payload (FullyGraded/Completed). Transient failures retry 3× with exponential backoff; 4xx rejects immediately; exhaustion raises AGSError with the last error. Added `GradePassback` model + Alembic migration `b7d41f08c2a9` (one row per submission): submit records a pending intent (lineitem from the session AGS claim, effective score at that moment); the TA dashboard posts effective scores recomputed at send time via per-row Post/Retry buttons and a Post All Grades action (latest submission per student). Status chips show pending / posted ✓ / dry run / failed ⚠ with the error in a tooltip. Dev launches inject a fake lineitem so the whole flow works in dry_run without Canvas.

## Verification

70 tests passing (13 new): payload + token-request shape against a mocked httpx transport, retry-then-succeed, retry exhaustion, 4xx no-retry (score and token), network-error retries, dry_run/disabled/unconfigured modes, dashboard chip renders. TestClient: auth gating on posting endpoints. Migration chain verified (`alembic history`).

## Requirements Advanced

- AGS grade passback with manual posting policy (milestone acceptance criterion 6) — code-complete; live round-trip blocked externally.

## Blocker

- **Live Canvas AGS cannot be exercised until the UTD Canvas admin issues an LTI 1.3 developer key** (known milestone risk, tracked since kickoff). Activation is config-only: set `AGS_MODE=live`, `LTI_TOKEN_URL`, `LTI_CLIENT_ID`, `LTI_TOOL_PRIVATE_KEY`, and implement the real launch (which stores the per-assignment AGS lineitem claim in the session, replacing the dev-injected one).

## Deviations

None from plan.

## Known Limitations

- Access token fetched per post (no caching) — fine at UTD scale, revisit if posting whole sections at once becomes slow.
- The placeholder `/lti/launch` does not yet extract the real AGS claim (same developer-key blocker).

## Follow-ups

- When the dev key lands: real OIDC launch + JWKS validation, store AGS claim, flip AGS_MODE=live, UAT against Canvas test course.

## Files Created/Modified

- `app/services/ags.py` + `app/services/__init__.py` (new), `app/models/passback.py` (new), `app/models/__init__.py`, `alembic/versions/b7d41f08c2a9_add_grade_passbacks.py` (new), `app/config.py`, `.env.example`, `app/routers/{ta,grading,dev}.py`, `app/templates/{_ta_row,ta_submissions,base}.html`, `tests/test_ags.py` (new)
