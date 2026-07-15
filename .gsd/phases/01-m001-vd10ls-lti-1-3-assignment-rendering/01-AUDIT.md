# M001 Milestone Audit

**Audited:** 2026-07-15 (end of autonomous run S03→S06)
**Status:** code_complete — human UAT deferred by user; 2 external blockers prevent full milestone closure

## Slice Status

| Slice | Disk | Tests | Human UAT |
|-------|------|-------|-----------|
| S01 LTI launch + tracer | ✓ complete | pass | done (retroactive) |
| S02 Full Lab01 Q1-Q4 | ✓ complete | pass | done (retroactive) |
| S03 Data tables R1-R3 | ✓ complete | pass (12 new) | deferred → 01-03-UAT.md |
| S04 TA checkpoints | ✓ complete | pass (12 new) | deferred → 01-04-UAT.md |
| S05 AGS passback | ✓ complete | pass (13 new) | deferred + partially blocked → 01-05-UAT.md |
| S06 Lab08 pre-lab | ✓ complete | pass (18 new) | deferred → 01-06-UAT.md |

Test suite: 33 → 88 passing. Working tree clean, all work committed (feat + docs pairs per slice).

## Final Integrated Acceptance (from 01-CONTEXT.md)

| Criterion | Verdict | Evidence / gap |
|-----------|---------|----------------|
| 1. Lab01 renders all gradeable types as interactive fields | ✓ code-complete | 19 questions + 3 table grids (64 inputs); human UAT pending |
| 2. Lab08 renders + grades via same engine | ✓ code-complete* | Zero template/router changes needed; *expected values provisional (D008) |
| 3. Numerical tolerance/precision/sig-fig rules | ✓ code-complete | precision (decimal places) + sig_figs both supported; exact sig-fig rules await instructor confirmation |
| 4. Data tables per-cell + consistency flagging | ✓ code-complete | Flag-only per D003; nominal values need instructor confirmation (D007) |
| 5. TA checkpoint verification end-to-end | ✓ code-complete | Toggle → effective score; carry-forward on resubmit; DB round-trip UAT pending |
| 6. AGS passback with manual posting policy | ◆ blocked externally | Client + retry + status tracking done against spec/mocks; live Canvas needs UTD dev key |
| 7. Concurrent submissions don't corrupt data | ◆ untested | Row-per-submission design has no shared mutable state, but no load test was run — candidate for post-key integration testing |

## External Blockers (both known at kickoff)

1. **UTD Canvas developer key** — blocks real OIDC/JWKS launch (`/lti/launch` placeholder) and live AGS posting (dry_run demoable today; live is config-only + launch claim extraction).
2. **Instructor confirmations** — Lab01 tile nominals/tolerances, Lab08 given values (`_provisional`), exact sig-fig rules, and whether measurement-uncertainty fields should stay 0 pts (D006).

## Recommendation

Do NOT archive the milestone yet. Order of operations:
1. Run the deferred human UATs (S03→S06 checklists, ~20 min with Postgres up)
2. Chase the Canvas dev key; when it lands: implement real launch (store AGS claim), flip AGS_MODE=live, run 01-05-UAT blocked section in a Canvas test course
3. Get instructor sign-off on the four items above
4. Then archive M001 and open M002

## Tech Debt (non-blocking)

- Pre-existing lint: unused imports in `app/routers/lti.py` (will be used by real launch), `app/main.py` StaticFiles, long lines in `dev.py`, unused variable in `numerical.py`
- AGS token fetched per post (no caching) — fine at UTD scale
- `.gsd/REQUIREMENTS.md` referenced by PROJECT.md but never created by the original setup
