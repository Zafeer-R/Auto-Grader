---
id: S06
parent: M001
milestone: M001
provides:
  - sig-fig-grading
  - lab08-answer-key
  - second-assignment-format-proof
requires:
  - slice: S03
    provides: grading-engine-data-tables
affects:
  []
key_files:
  - app/grading/numerical.py
  - answer_keys/lab08.json
  - tests/test_lab08.py
key_decisions:
  - Sig-fig counting is permissive on ambiguous integer trailing zeros; extra precision accepted
  - Lab08 expected values are a self-consistent placeholder problem marked _provisional (pre-lab sheet has no given values)
  - Derivation questions modeled as short_answer/deferred_m2 (same class as Lab01 calculation attachments)
patterns_established:
  - sig_figs answer-key field alongside precision
observability_surfaces:
  - none
drill_down_paths:
  []
duration: ""
verification_result: deferred_uat
completed_at: 2026-07-15
blocker_discovered: false
---

# S06: Lab08 Pre-lab Format

**Lab08 pre-lab (30 pts: 2 TA-graded derivations + 12 numerical quantities at 3 sig figs) renders and grades through the unchanged engine — proving the answer-key format generalizes; sig-fig validation added to the numerical grader**

## What Happened

Extracted Lab08_Pre-lab.docx (including OMML math runs): Grade /30 — Question (1) two "show the relations" derivations [4+4], Questions (2)/(3) twelve computed rotational-motion quantities [16+6] all "to 3 sig. figs." Added `count_sig_figs()` + `sig_figs` parameter to `grade_numerical` (leading zeros never count, decimal trailing zeros count, ambiguous integer trailing zeros permissive, ≥N accepted). The docx contains no given values or figures, so `answer_keys/lab08.json` ships a self-consistent placeholder problem (uniform disk M=2.00 kg R=0.100 m, hanging mass 0.500 kg falling 1.00 m, g=9.80; part 3 drops an identical disk onto the spinning disk) with given parameters embedded in section instructions — marked `_provisional` at the top of the JSON. No template or router changes were needed: the second format rendered and graded through the existing paths, which was the point of the slice.

## Verification

88 tests passing (18 new): sig-fig counting parametrized edge cases, sig-fig grading paths ("0.01" fails / "0.0100" passes a 3-sig-fig requirement), physics consistency of the key itself (τ=TR, U=K_h+K_d, L conserved, ω and KE halve), all-correct submission → 22/30 auto-gradeable, template renders via the standard assignment/results templates.

## Requirements Advanced

- Second assignment format grades via the same engine (milestone acceptance criteria 2, and 3's sig-fig clause).

## Deviations

- **Expected values are placeholders.** The pre-lab answer sheet has no problem parameters (they live in the lab manual, not the repo). The key is internally consistent and demoable but the instructor must confirm or replace the numbers — recorded as D008.

## Known Limitations

- Sig-fig rules ("at least N", permissive integer trailing zeros) implement the plainest reading of "Express to 3 sig. figs." — the milestone context lists exact sig-fig rules as an open instructor question.

## Follow-ups

- Instructor: supply the real Lab08 pre-lab given values (or confirm the placeholder problem).

## Files Created/Modified

- `app/grading/numerical.py`, `app/grading/engine.py`, `answer_keys/lab08.json` (new), `tests/test_lab08.py` (new)
