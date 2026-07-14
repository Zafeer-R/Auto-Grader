# Decisions Register

<!-- Append-only. Never edit or remove existing rows.
     To reverse a decision, add a new row that supersedes it.
     Read this file at the start of any planning or research phase. -->

| # | When | Scope | Decision | Choice | Rationale | Revisable? | Made By |
|---|------|-------|----------|--------|-----------|------------|---------|
| D001 |  | architecture | Answer key storage format for M1 | JSON files in answer_keys/ directory, section-based schema with questions, tolerances, precision rules, and point allocations | Flexible enough for lab report and pre-lab formats; machine-readable for grading engine; hand-authorable by power user. DB-backed answer keys deferred to M3 authoring UI. | Yes | human |
| D002 |  | architecture | Grading execution model | Synchronous grading on submit, no async queue | Deterministic numerical grading is fast (&lt;100ms per submission). Async queue adds complexity without benefit until M2 introduces LLM inference. | Yes | collaborative |
| D003 |  | architecture | Data table consistency checking policy | Flag inconsistencies (R2 vs R1 cross-check) but do not deduct points | Instructor preference. Consistency checks help TAs spot issues but should not auto-penalize students. | Yes | human |
| D004 |  | architecture | Report question input format | Two separate fields (value + uncertainty) rather than single combined text field | Cleaner for students, more reliable grading, easier to give partial credit per component. String fallback parsing retained for API flexibility. | Yes | agent |
| D005 |  | architecture | LTI authentication for local development | Dev-mode bypass via /dev/launch endpoint, gated behind DEBUG=true config flag | Real LTI 1.3 OIDC/JWKS auth blocked on UTD Canvas admin creating a developer key. Dev bypass unblocks all other development and testing. | Yes | collaborative |
