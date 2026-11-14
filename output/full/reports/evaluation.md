# Evaluation: full

Every number below is computed from the generated input tables. Ground truth is
used only for the detection scores. The full list is in `metrics.json`.

## Detection (detector vs ground truth, matched by record ID)

| Issue type | Labelled | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| PREREQUISITE_VIOLATION | 50 | 50 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| COURSE_UNAVAILABLE | 50 | 50 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| BUDGET_EXCEEDED | 50 | 50 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| DUPLICATE_COMPLETION | 50 | 50 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| GAP_NOT_REASSESSED | 50 | 50 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| ALL | 250 | 250 | 0 | 0 | 1.000 | 1.000 | 1.000 |

## Funnel

| Step | Count |
|---|---|
| recommended | 14610 |
| requested | 10000 |
| approved | 9769 |
| rejected | 231 |
| started | 9594 |
| withdrawn | 476 |
| completed | 9282 |
| passed | 6308 |
| reassessed | 6316 |

## Attendance, passing and learning are different numbers

- Completed, of started: 96.8%
- Passed, of completed: 68.0%
- Gap closed, of reassessed gap-closing courses: 52.1%
- Average level uplift after a PASSED course: 1.23
- Average level uplift after a FAILED course: 0.23
- Reassessment coverage of due completions: 99.2%

## Recommendations

- Proposed steps (RECOMMENDED rows): 14610
- Feasible on every planning check (BR-04, 05, 07, 08, 09): 99.3%
- Funded by the department budget (BR-21): 86.9%
- Feasible and funded: 86.9%
- Planning gaps: 22181, of which PLANNED: 51.4%

## Budgets

| Department | Limit | Proposed | Funded | Committed | Utilization | Budget rejections |
|---|---|---|---|---|---|---|
| ENG | 23,890,000 | 28,542,800 | 23,888,800 | 16,490,400 | 69.03% | 5 |
| DAT | 17,370,000 | 20,556,800 | 17,368,000 | 11,815,200 | 68.02% | 65 |
| ITS | 14,360,000 | 17,080,000 | 14,360,000 | 11,025,200 | 76.78% | 57 |
| SAL | 13,590,000 | 16,231,200 | 13,588,000 | 9,615,200 | 70.75% | 0 |
| MKT | 9,430,000 | 11,186,400 | 9,428,800 | 7,598,400 | 80.58% | 27 |
| FIN | 10,140,000 | 12,017,200 | 10,136,800 | 7,747,200 | 76.40% | 8 |
| HRM | 7,960,000 | 9,396,800 | 7,956,800 | 4,846,400 | 60.88% | 24 |
| OPS | 21,010,000 | 24,792,400 | 21,008,000 | 16,444,800 | 78.27% | 45 |
