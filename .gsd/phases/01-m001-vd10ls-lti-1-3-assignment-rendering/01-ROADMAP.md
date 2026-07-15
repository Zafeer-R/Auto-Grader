# M001: LTI 1.3 + Assignment Rendering + Numerical and Tabular Grading

**Vision:** Core platform for physics lab auto-grading at UTD. Canvas LTI integration, interactive assignment rendering, deterministic grading (numerical, identification, data tables), TA checkpoint verification, and AGS grade passback. Covers Lab01 full report and Lab08 pre-lab formats.

## Success Criteria

- Student launches Lab01 from Canvas, fills all gradeable fields, submits, receives correct score breakdown
- TA verifies checkpoint items and score updates accordingly
- Grades post to Canvas gradebook via AGS with manual posting policy
- Lab08 pre-lab renders and grades correctly using the same engine
- 33+ unit tests pass covering all grading types

## Slices

- [x] **S01: LTI Launch + Single Question Grading Tracer** `risk:low` `depends:[]`
  > After this: Student launches via dev launch, sees Lab01 Q1, submits, gets scored feedback

- [x] **S02: Full Numerical + ID Grading (Lab01 Q1-Q4)** `risk:low` `depends:[S01]`
  > After this: Student fills all 19 questions across Q1-Q4, submits, gets section-grouped scored results

- [x] **S03: Data Table Grading (R1, R2, R3)** `risk:high` `depends:[S02]`
  > After this: Student fills data tables R1, R2, R3 as editable grids, submits, gets per-cell grading with consistency flags

- [x] **S04: TA Checkpoint Verification UI** `risk:medium` `depends:[S01]`
  > After this: TA opens dashboard, sees student submissions, toggles checkpoint items, student score updates

- [x] **S05: AGS Grade Passback to Canvas** `risk:high` `depends:[S02,S04]` *(live Canvas activation pending UTD dev key)*
  > After this: After grading + checkpoint verification, score posts to Canvas gradebook (held until instructor release)

- [x] **S06: Lab08 Pre-lab Format** `risk:low` `depends:[S03]` *(expected values provisional pending instructor)*
  > After this: Student launches Lab08 pre-lab, fills in answers, submits, gets scored feedback using same engine

## Boundary Map

Not provided.
