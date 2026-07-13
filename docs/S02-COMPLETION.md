# S02: Full Numerical + ID Grading (Lab01 Q1-Q4)

**Status:** Complete
**Completed:** 2026-07-13
**Parent:** S01 (`419d298`)

## What Was Built

Expanded the grading engine from 6 questions (9 pts, Q1 only) to 19 questions (48 auto-gradeable pts across Q1-Q4), covering the full Lab01 assignment structure. Added two new question types (`report`, `short_answer`), section-based answer key organization, precision enforcement, and section-grouped UI rendering.

## Changes from S01

### Answer Key (`answer_keys/lab01.json`)

Restructured from flat question list to section-based layout:

- **`sections[]`** — defines section ordering, titles, point totals, types (`checkpoint` for TA-verified items), and per-section instructions
- **19 questions across 6 sections:** Q1 (9 pts), Q2 (15 pts), Q3 (12 pts), Q4 (10 pts), Measurement (2 pts), plus 2 checkpoint sections (20 pts, TA-graded)
- **Total auto-gradeable:** 42 pts (of 48 question pts; 6 pts deferred to TA for Q4_2 short answer)
- **Total assignment:** 100 pts (including 20 pts checkpoints + 24 pts data tables + 24 pts analyses, handled in S03+)

New question properties: `section` (groups into UI sections), `precision` (required decimal places), `hint` (display instructions), `unit` (display label).

### Grading Engine (`app/grading/engine.py`)

Three new functions:

- **`grade_report(question_def, student_answer)`** — Grades value and uncertainty as two independent components, each worth half points. Accepts dict input (`{"value": "3.81", "error": "0.01"}`) or falls back to string parsing (`"3.81 +/- 0.01"` or `"3.81 +- 0.01"` or `"3.81 ± 0.01"`). Each component independently checks value tolerance and precision.
- **`grade_short_answer(question_def, student_answer)`** — Records the answer but scores 0.0 with feedback "will be graded by your TA". Placeholder until M2 adds local LLM grading.
- **`grade_question()`** — Updated to dispatch `report` and `short_answer` types, and to accept `str | dict` input for report questions.

### Router (`app/routers/grading.py`)

- Form field collection now handles report question two-field inputs: `q_{id}_value` and `q_{id}_error` are assembled into `{"value": ..., "error": ...}` dicts before grading
- Section metadata passed to templates for grouped rendering

### Templates

**`assignment.html`:**
- Section-grouped layout with headers, point badges, and per-section instructions
- Checkpoint sections render as info badges (TA-verified, no student input)
- Report questions render as two side-by-side fields (value + `+-` + error) with unit labels
- Short answer questions render as textareas
- Hints displayed below inputs when present

**`results.html`:**
- Section-grouped result display with per-section subtotal scores
- "Pending TA review" badges for short answer and checkpoint questions
- Report results show value and uncertainty feedback separately

**`ta_dashboard.html`:**
- Updated to use section-based layout matching answer key structure
- Shows question types, point values, and checkpoint indicators

**`base.html`:**
- Added CSS for sections, report two-field layout, checkpoint badges, textareas, hints, and TA review indicators

### Answer Key Schema (new fields)

```json
{
  "sections": [
    {"id": "q1", "title": "Question 1", "points": 9},
    {"id": "checkpoint1", "title": "Check Box #1", "type": "checkpoint", "points": 10}
  ],
  "questions": {
    "q2_5": {
      "type": "report",
      "section": "q2",
      "expected_value": 3.81,
      "expected_error": 0.01,
      "value_tolerance": 0.50,
      "error_tolerance": 0.50,
      "precision": 2,
      "points": 3,
      "unit": "cm"
    },
    "q4_2": {
      "type": "short_answer",
      "section": "q4",
      "points": 6,
      "grading": "deferred_m2"
    }
  }
}
```

## Test Coverage

33 tests in `tests/test_grading.py` (up from 18 in S01):

| Test Class | Count | What's Tested |
|-----------|-------|---------------|
| `TestGradeNumerical` | 12 | Exact match, tolerance boundaries, empty/non-numeric, precision validation (pass/fail/trailing zeros/extra decimals), negative values |
| `TestGradeQuestion` | 6 | Identification (correct/wrong/case-insensitive/multi-accepted), numerical dispatch, unknown type |
| `TestGradeReport` | 7 | Both correct, partial (value only/error only), both wrong, empty, string fallback (`+/-` and `+-`), precision enforcement |
| `TestGradeShortAnswer` | 2 | Answer recorded with TA feedback, empty answer |
| `TestGradeSubmission` | 6 | Full/partial/missing submissions, report in submission, full Lab01 answer key validation (42/48 auto-graded), total max verification |

## Decisions Made During S02

1. **Report questions use two separate fields** — Value and uncertainty as independent inputs rather than a single "3.81 +/- 0.01" text field. Cleaner for students, more reliable grading, easier to give partial credit.
2. **Short answer deferred to M2** — Q4(2) requires local LLM grading. Engine records the answer and scores 0.0 until TA or LLM grades it.
3. **Section-based answer key structure** — Questions grouped by section with ordering, instructions, and point totals. Supports checkpoint sections (TA-verified) and future data table sections.
4. **Wide tolerances for calculated values** — Q2/Q3 expected values depend on student measurement data (not known in advance). Tolerances set wide (e.g., +/-0.50 cm) to accept reasonable answers from different datasets.

## What's NOT Built Yet

- Data tables R1/R2/R3 (editable grids with per-cell grading) — S03
- TA checkpoint verification UI — S04
- AGS grade passback to Canvas — S05
- Lab08 pre-lab — S06
- Local LLM short-answer grading — M2
