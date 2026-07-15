---
id: S03
parent: M001
milestone: M001
provides:
  - grading-engine-data-tables
  - r1-stats-derivation
  - consistency-flags
  - editable-grid-ui
requires:
  - slice: S02
    provides: section-based-answer-key
affects:
  []
key_files:
  - app/grading/tables.py
  - app/grading/engine.py
  - answer_keys/lab01.json
  - app/templates/assignment.html
  - app/templates/results.html
  - tests/test_grading.py
key_decisions:
  - R1 is raw student data — completeness-checked only (0 pts, TA verifies via Check Box #2)
  - Cell grading policy lives in answer key (expected+tolerance → numerical; bare → precision+completeness)
  - Consistency vs student's own R1 data flags but never deducts (D003)
  - Measurement uncertainty fields corrected to 0 pts to restore exact 100-pt budget
patterns_established:
  - Data table schema (tables{} with rows/columns/cells, form inputs t_{table}_{row}_{col})
observability_surfaces:
  - Consistency flags surfaced on results page and stored in grade_result JSONB
drill_down_paths:
  []
duration: ""
verification_result: deferred_uat
completed_at: 2026-07-15
blocker_discovered: false
---

# S03: Data Table Grading (R1, R2, R3)

**Added data table grading: R1 raw data grid (completeness), R2 statistics and R3 volume/density grids graded per-cell (24 pts) with consistency flags derived from the student's own R1 data**

## What Happened

Extracted the real table structure from Lab01_Report.docx: R1 (Trial 1-5 × Length/Width/Thickness/Mass) is raw student-collected data with no ground truth; R2 [12] and R3 [12] are the "Analyses" tables. Built `app/grading/tables.py`: R1 stats derivation (mean, sample SD, SEOM=SD/√5, error=max(SEOM, instrument uncertainty)), R3 propagation (V=LWT, min/max bounds, uncertainty=(hi−lo)/2), per-cell grading, and consistency flagging. Cells with nominal `expected`+`tolerance` in the answer key grade numerically (mean/volume/density anchored to the standard Al tile ≈ 2.70 g/cm³); statistic cells grade for a parseable value at required precision (0.001 cm / 0.01 g for R2; 0.01 for R3). Every derived cell also cross-checks against the value recomputed from the student's own R1 data — mismatches flag for TA review, never deduct (D003). Grids render as HTML tables of inputs named `t_{table}_{row}_{col}`; results page shows per-cell ✓/✗ plus ⚠ badges and a flags panel. Committed as one feat commit.

## Verification

45 unit tests passing (12 new: stats derivation, R3 propagation, consistent full-score path, flag-without-deduction, precision enforcement, nominal enforcement, empty/garbage cells, missing-R1 degradation). Template smoke test: 64 form inputs render, flags appear on results page, TA dashboard shows table structure.

## Requirements Advanced

- Data table grading with consistency flagging (milestone acceptance criterion 4).

## New Requirements Surfaced

None.

## Deviations

- **Measurement uncertainty fields (meas_balance, meas_calipers) corrected from 1 pt to 0 pts.** The report sheet allocates them no points; with tables added, the budget now reconciles exactly: questions 46 + tables 24 + TA checkpoints 30 = 100. Supersedes the implicit S02 allocation — recorded as D006, revisable if the instructor wants those fields credited.

## Known Limitations

- Nominal expected values for R2/R3 mean cells (5.08/2.54/0.64 cm, 22.3 g, 8.26 cm³, 2.70 g/cm³) are hand-authored estimates of the standard tile — instructor should confirm/tune in `answer_keys/lab01.json`.
- Consistency tolerance is max(2 units of last required digit, 2% relative) — may need tuning after real student data.

## Follow-ups

- Pre-existing lint debt (unused imports in lti.py, long lines in dev.py) noted for a cleanup pass.

## Files Created/Modified

- `app/grading/tables.py` (new), `app/grading/engine.py`, `answer_keys/lab01.json`, `app/routers/grading.py`, `app/templates/{assignment,results,ta_dashboard,base}.html`, `tests/test_grading.py`
