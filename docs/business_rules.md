# Business rules

Every rule has a code. The engine, the simulation, the validator, the detector
and the ground truth all refer to these codes. Each rule lives in one function
in `backend/pipeline/rules/`.

## Planning rules (the recommendation engine)

| Code | Rule | Where | Example |
|---|---|---|---|
| BR-01 | Gap against the **target role**: `max(0, target - level)`, level = latest assessment on or before the planning date | `rules/gaps.py` | Target 4, level 2: gap 2. Level 5: gap 0, not -1 |
| BR-02 | Only ACTIVE employees get a plan. ON_LEAVE gaps are `EMPLOYEE_ON_LEAVE` | `rules/recommend.py` | |
| BR-03 | A course *covers* a gap if it is ACTIVE and teaches the skill up to at least the target | `rules/recommend.py` | Target 4: a course that certifies 3 does not cover it |
| BR-04 | A course is *available* if it is ACTIVE and has a run starting inside the planning period | `rules/availability.py` | A course with only 2027 runs is unavailable in 2026 |
| BR-05 | Every prerequisite is PASSED before the course starts, or planned earlier in the path ending at least 14 days before | `rules/prerequisites.py` | F (19 Jan to 1 Feb) then I may start 15 Feb at the earliest |
| BR-06 | Candidates in order: available, cheapest, shortest, lowest course_id | `rules/recommend.py` | |
| BR-07 | At most 4 courses per path. A course goes in with its whole chain or not at all. If a chain does not fit, **the next candidate is tried** | `rules/recommend.py` | A cheap course needing 3 prerequisites loses to a dearer one with none |
| BR-08 | One course at a time, 14 days apart, step 1 at least 14 days after the planning date, earliest run with a free seat. The plan books the seat | `rules/schedule.py` | |
| BR-09 | Path cost within the ₹60,000 allowance, and no course dearer than the department's remaining budget | `rules/budget.py` | Exactly ₹60,000 passes. ₹60,001 is OVER_BUDGET |
| BR-20 | The plan only sees facts dated on or before the planning date | `rules/snapshot.py` | A June assessment is invisible to the January plan |

## Operational rules (the simulation and the validator)

| Code | Rule | Where | Example |
|---|---|---|---|
| BR-10 | Approve only if `seats_approved < capacity`. Checked before budget | `stages/s08_simulate.py` | |
| BR-11 | Approve only if `committed + cost <= limit`. Committed is the running total in `(event_on, event_id)` order | `rules/budget.py` | Committed 90, cost 10, limit 100: approved. Cost 10.01: rejected |
| BR-12 | Lifecycle: REQUESTED, then APPROVED or REJECTED; APPROVED, then IN_PROGRESS or WITHDRAWN; IN_PROGRESS, then COMPLETED or WITHDRAWN | `rules/lifecycle.py` | REQUESTED to COMPLETED is refused |
| BR-13 | One completion per enrollment, only for COMPLETED ones, dated the run's end date | validator | |
| BR-14 | PASSED if attendance >= 75 and exam >= 60 | `rules/outcomes.py` | 74.9% attendance with a 99 exam is FAILED |
| BR-15 | Level = band of the score: 0-19, 20-39, 40-54, 55-69, 70-84, 85-100 give levels 0 to 5 | `rules/outcomes.py` | 69 is level 3, 70 is level 4 |
| BR-16 | A post-course score never goes above the top of the band the course certifies | `rules/outcomes.py` | A course certifying level 3 caps the score at 69 |
| BR-17 | Every gap-closing completion gets a post-course test 3 to 14 days later. Only checked once it is due | validator, detector | |
| BR-18 | No retakes: one recommendation and one enrollment per employee/course pair | dictionary (UNIQUE) | |
| BR-19 | History is append-only. Status and level are always derived from the latest event | `rules/lifecycle.py`, s10 | |

## Budget policy

A department's limit is 62% of what its people planned in January
(`FUNDING_RATIO`), rounded up to ₹10,000. Requests are funded first come, first
served. The gap between plan and funding is where budget rejections come from:
961 requests at full scale.
