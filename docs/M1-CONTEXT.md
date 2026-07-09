# M1: LTI 1.3 + Assignment Rendering + Numerical/Tabular Grading

**Status:** Ready for planning (slice decomposition next)
**Date:** 2026-07-08

## Why This Milestone

Physics labs at UTD are graded manually by TAs, which is slow, inconsistent, and doesn't scale. M1 establishes the core platform: Canvas integration via LTI 1.3, rendering assignments in-browser, and auto-grading the deterministic question types (numerical, data tables, identification). This is the foundation everything else builds on.

## User-Visible Outcome

When complete:
- **Student** launches the tool from a Canvas assignment, sees the lab rendered as an interactive form, fills in numerical answers and data tables, submits, and receives instant scored feedback
- **TA** opens the tool for a section, sees a dashboard of submissions, verifies checkpoint items (safety training, caliper test, data check), and releases grades
- **Instructor** sees aggregated scores posted to Canvas gradebook (held until manual release)

**Entry point:** Canvas LTI launch (iframe)
**Environment:** Browser, Canvas Cloud
**Live dependencies:** Canvas LTI 1.3 (OIDC, JWKS), PostgreSQL, AGS grade passback

## Question Types In Scope

| Type | Example | Grading Logic | Points |
|------|---------|---------------|--------|
| **Numerical fill-in** | "Uncertainty of stopwatch is ___ s" | Expected value +/- tolerance, sig fig rules | Variable |
| **Identification** | "Which set has random errors only (A/B/C)?" | Exact match from option set | 1-4 |
| **Calculated value** | Mean diameter, SEOM, volume, density | Expected value +/- tolerance, precision rules (e.g. "to 0.01 cm") | 3 each |
| **Data table** | Table R1 (5 trials x 4 measurements), R2, R3 | Per-cell numerical grading + consistency flag (R2 values derived from R1) | 12 each |
| **TA checkpoint** | Lab Safety Training, Check Box #1/#2 | Binary pass/fail set by TA, not student | 10 each |
| **Short-answer reasoning** | "Write TWO reasons why..." | **Deferred to M2** (local LLM) | -- |
| **Calculation work** | "Attach calculation details" | **Deferred to M2** (image + text) | -- |

## Completion Criteria

- **Contract complete:** Unit tests pass for grading engine (numerical tolerance, table consistency, score roll-up); LTI launch/auth integration tests pass against mock Canvas
- **Integration complete:** Full round-trip works -- Canvas launch -> render assignment -> student submits -> grading runs -> score appears in Canvas gradebook (held)
- **Operational complete:** Concurrent student submissions don't corrupt data; TA checkpoint flow works without race conditions

## Final Integrated Acceptance

To call M1 done, we must prove:
1. A student can launch Lab01 from Canvas, fill in all gradeable fields, submit, and receive a correct score breakdown
2. A TA can verify checkpoint items and the score updates accordingly
3. Grades post to Canvas gradebook via AGS with manual posting policy
4. A second assignment format (Lab08 pre-lab) renders and grades correctly using the same engine

## Architectural Decisions

### Answer Key Schema -- JSON per assignment
- **Decision:** Each assignment has a JSON answer key defining questions, sub-questions, expected values, tolerances, precision rules, and point allocations
- **Rationale:** Flexible enough for both lab report and pre-lab formats; machine-readable for grading engine; hand-authorable by power user in M1
- **Alternatives:** YAML (less tooling support), database-only (harder to version/review)

### Grading Engine -- Synchronous per-submission
- **Decision:** Grade synchronously on submit; no queue needed at M1 scale
- **Rationale:** Deterministic numerical grading is fast (<100ms). Async queue adds complexity without benefit until M2 (LLM inference)

### Data Table Consistency -- Flag only, no penalty
- **Decision:** Cross-check derived values (R2 from R1, R3 from R2) and flag inconsistencies but don't deduct points
- **Rationale:** Instructor preference; consistency checks help TAs spot issues but shouldn't auto-penalize

## Error Handling Strategy

- **LTI launch failures:** Show clear error page with "contact your TA" messaging; log full OIDC/JWT details server-side
- **Grading errors:** Never silently swallow; return per-question error states ("could not grade -- answer key missing for Q3") rather than zero scores
- **AGS passback failures:** Retry with exponential backoff; surface failure in TA dashboard; never silently drop grades

## Risks and Unknowns

- **Canvas LTI 1.3 dev key registration** -- UTD Canvas admin must create a developer key; process/timeline unknown
- **iframe CSP restrictions** -- Canvas may restrict what runs in the LTI iframe; need to verify HTMX works
- **Sig fig / precision grading edge cases** -- rounding rules vary by question; answer key schema must be expressive enough
- **Table consistency check logic** -- "R2 derived from R1" depends on the specific formula; need per-assignment consistency rules

## Scope

### In Scope
- LTI 1.3 launch, OIDC auth, JWKS validation
- Assignment rendering (Lab01 full report, Lab08 pre-lab)
- Numerical/identification grading engine
- Data table grading with consistency flagging
- TA checkpoint verification UI
- Score roll-up and AGS grade passback
- JSON answer key format + manual authoring
- Student submission storage (PostgreSQL)
- Basic TA dashboard (view submissions, verify checkpoints)

### Out of Scope / Non-Goals (M1)
- Short-answer / reasoning grading (M2)
- Calculation work / image upload grading (M2)
- Assignment authoring UI (M3)
- FERPA audit logging / data retention (M4)
- Multi-institution support
- Offline / mobile-optimized rendering

## Technical Constraints

- Must run in Canvas Cloud iframe (Instructure-hosted, no self-hosted Canvas)
- No external AI/cloud services (FERPA)
- Python 3.11+ / FastAPI
- PostgreSQL (university-managed)
- All auth via LTI 1.3 -- no separate user accounts

## Integration Points

- **Canvas LMS** -- LTI 1.3 launch (OIDC + JWKS), AGS grade passback, Deep Linking (future)
- **PostgreSQL** -- submissions, answer keys, checkpoint state, user sessions

## Testing Requirements

- **Unit tests:** Grading engine (numerical tolerance, table cell grading, consistency checks, score roll-up, sig fig validation)
- **Integration tests:** LTI launch flow (mock Canvas OIDC/JWKS), AGS passback
- **E2E:** Full submission flow in browser (can use test LTI consumer)

## Acceptance Criteria

1. Lab01 full report renders all gradeable question types as interactive form fields
2. Lab08 pre-lab renders and grades using the same engine
3. Numerical grading handles tolerance, precision, and sig fig rules correctly
4. Data tables grade per-cell with consistency flagging
5. TA checkpoint verification works end-to-end
6. Grades post to Canvas gradebook via AGS with manual posting policy
7. Concurrent submissions don't corrupt data

## Open Questions

- Canvas dev key registration process at UTD -- need admin contact and timeline
- Exact sig fig rules per question type -- need to confirm with instructor
- Table consistency formulas -- need per-assignment derivation rules documented
