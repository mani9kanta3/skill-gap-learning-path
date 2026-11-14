# Edge cases

The generator first builds a clean baseline. A run with `--no-inject` passes
every check with zero failing records. Then `stages/s09_inject.py` adds five
kinds of labelled exception.

## Ground rules

- **One rule per case.** Candidates are filtered until everything else about the
  record is valid. A test checks that each labelled record is caught by its own
  detector and by no other.
- **No record is used twice.** Each injector skips records and employees used by
  another.
- **Foreign keys stay valid.** These are broken business rules, not broken joins,
  so Postgres loads them, and the validator has to find them.
- **Labels stay out of the input.** They are written only to
  `ground_truth/ground_truth.csv|json` and loaded into the separate `eval`
  schema. A test checks that no input column or value carries a label.
- **Each injector has its own seeded random stream**, so changing one never
  shifts another.
- **No silent shortfall.** If any candidate pool is too small, the run stops with
  a message instead of writing fewer cases.

## The five types

| Type | Rule | Injected as | Filters that keep it to one rule | Expected decision |
|---|---|---|---|---|
| PREREQUISITE_VIOLATION | BR-05 | An extra RECOMMENDED `CLOSES_GAP` row for one of the employee's real gaps (unplanned gaps first, planned gaps as a fallback). Added after the budget was allocated, so it is NOT_FUNDED_BUDGET | The course is available. The path stays at 4 courses or fewer. The cost fits the allowance. The run has a free seat and starts at least 14 days after the previous step. Only a prerequisite is missing | NOT_RECOMMENDED: prerequisite not planned |
| COURSE_UNAVAILABLE | BR-04 | The same, for an ACTIVE course whose only runs are in 2027 | Its prerequisites, if any, are already earlier in the path, so only availability is broken. Otherwise as above | NOT_RECOMMENDED: COURSE_UNAVAILABLE |
| BUDGET_EXCEEDED | BR-11 | A new enrollment, approved, for a NOT_FUNDED_BUDGET step nobody requested | It uses the planned run (seat already booked), and its prerequisites are passed. A step is only left unfunded when it costs more than what was still unallocated, so approving it always pushes the department's obligations past its limit. Normal approvals are judged on their own funding, so this never changes how a normal row is judged | REJECTED: BUDGET_EXHAUSTED |
| DUPLICATE_COMPLETION | BR-13 | A second completion row for a completed enrollment | Same date, attendance, score and result as the original, so only "one per enrollment" breaks | Count once |
| GAP_NOT_REASSESSED | BR-17 | The post-course test of a gap-closing completion is removed before assessment IDs exist | Due (at least 14 days before the snapshot). The gap was still open before the course. No later completion of that employee touches the same skill, so no later score depended on it | Post-course assessment due |

## How the match is checked

`checks/validate.py` runs each rule on the final data and compares the failing
`(issue_type, record_id)` set with ground truth **by ID**:

- unexpected = failing but not labelled,
- missed = labelled but not failing.

Both must be empty. `checks/detect.py` runs the same rules without reading ground
truth, and `checks/evaluate.py` scores it:

- precision, recall and F1 per type,
- 1.000 for all five at both scales.

A separate check re-runs the January engine. The only rows in `recommendation`
that the engine did not produce must be exactly the 100 injected ones.
