# Project Knowledge

Append-only register of project-specific rules, patterns, and lessons learned.
Agents read this before every unit. Add entries when you discover something worth remembering.
## Rules

| # | Scope | Rule | Why | Added |
|---|-------|------|-----|-------|
| R1 | grading | Never deduct points for R1-consistency mismatches — flag for TA only | Instructor policy (D003) | 2026-07-15 |
| R2 | tests | Tests must run without a database (pure logic + Jinja render smoke) | Suite stays fast (<2s) and CI-free of Postgres | 2026-07-15 |

## Patterns

| # | Pattern | Where | Notes |
|---|---------|-------|-------|
| P1 | Data table schema: `tables{}` with rows/columns/cells; form inputs `t_{table}_{row}_{col}` | answer_keys/lab01.json, app/grading/tables.py | Cell grading policy lives in the key: expected+tolerance → numerical; bare cell → precision/completeness |
| P2 | HTMX row-swap fragments for in-place updates | app/templates/_ta_row.html | Endpoint returns the fragment, hx-target the row, hx-swap outerHTML |
| P3 | External integrations live in app/services/ with injectable httpx transport | app/services/ags.py | MockTransport in tests; retry transient-only (5xx/429/network) |
| P4 | Answer-key numeric rigor fields: `precision` (decimal places) and `sig_figs` | app/grading/numerical.py | Both permissive toward extra precision |

## Lessons Learned

| # | What Happened | Root Cause | Fix | Scope |
|---|--------------|------------|-----|-------|
| L1 | Assignment docx files are answer *sheets* — Lab08 pre-lab carries no given values, Lab01 R1 has no ground truth | Problem parameters live in the lab manual; raw-data tables are student-measured | Provisional keys marked `_provisional` + consistency-vs-own-data grading; instructor confirms nominals | answer keys |
| L2 | S02 gave measurement fields 1 pt each, silently breaking the 100-pt budget once tables landed | Point allocations weren't reconciled against the printed grade total | Zeroed them (D006); test asserts questions+tables+checkpoints == total_points | lab01 |
