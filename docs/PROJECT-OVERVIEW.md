# Auto-Grader: Physics Lab Auto-Grading System

Auto-grading system for physics lab assignments at UTD, integrated into Canvas LMS as an LTI 1.3 tool. Students complete assignments interactively inside Canvas, submissions are auto-graded, and scores are posted to the gradebook via AGS with manual posting policy (held until instructor release).

## Tech Stack

- **Backend:** Python + FastAPI
- **Database:** PostgreSQL
- **Frontend (in-Canvas):** Jinja2 templates / HTMX (server-rendered, runs in LTI iframe)
- **ML (M2):** Local LLM inference (e.g., Ollama) or sentence-transformers
- **Deployment:** University-managed infrastructure (UTD)

## Canvas Integration

- UTD uses Canvas Cloud (Instructure-hosted)
- LTI 1.3 with OIDC login, JWKS, developer key registration
- AGS for grade passback with manual posting policy
- Students edit and submit directly in Canvas iframe

## Grading Engine

- Sub-question level scoring with roll-up to question totals
- Numerical answers: expected value + tolerance/precision rules
- Data tables: grade against answer key + flag internal consistency (R2 vs R1 cross-check) -- flagging only, not score penalty
- Checkpoint items (Lab Safety Training, Check Boxes): TA verifies through tool interface, not student self-report
- Short-answer reasoning: auto-graded via local mechanism (M2)
- Calculation work: text area for typed work + optional image upload of handwritten work

## Answer Key Format

- JSON-based, authored manually by power user (M1)
- Full authoring UI deferred to M3

## Assignment Format Priority

1. Full lab report first (Lab 1 style, ~100 points)
2. Pre-lab format second (Lab 8 style, ~30 points)

## FERPA Constraints

- Pseudonymous user identifiers from LTI launch
- No external AI services
- Audit logging, data retention/deletion controls
- Tool qualifies as school official under FERPA

## Milestone Structure

| Milestone | Scope |
|-----------|-------|
| **M1** | LTI 1.3 + Assignment Rendering + Numerical/Tabular Grading |
| **M2** | Short-Answer & Reasoning Auto-Grading (local inference) |
| **M3** | Assignment Authoring & Rubric Management (instructor UI) |
| **M4** | FERPA Compliance & Administration |
