# Evaluation: starter

Every number below is computed from the generated input tables. Ground truth is
used only for the detection scores. The full list is in `metrics.json`.

## Detection (detector vs ground truth, matched by record ID)

| Issue type | Labelled | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| PREREQUISITE_VIOLATION | 5 | 5 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| COURSE_UNAVAILABLE | 5 | 5 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| BUDGET_EXCEEDED | 5 | 5 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| DUPLICATE_COMPLETION | 5 | 5 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| GAP_NOT_REASSESSED | 5 | 5 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| ALL | 25 | 25 | 0 | 0 | 1.000 | 1.000 | 1.000 |

## Funnel

| Step | Count |
|---|---|
| recommended | 1385 |
| requested | 1000 |
| approved | 971 |
| rejected | 29 |
| started | 956 |
| withdrawn | 42 |
| completed | 928 |
| passed | 680 |
| reassessed | 520 |

## Attendance, passing and learning are different numbers

- Completed, of started: 97.1%
- Passed, of completed: 73.3%
- Gap closed, of reassessed gap-closing courses: 50.4%
- Average level uplift after a PASSED course: 1.27
- Average level uplift after a FAILED course: 0.25
- Reassessment coverage of due completions: 99.1%

## Recommendations

- Proposed steps (RECOMMENDED rows): 1385
- Feasible on every planning check (BR-04, 05, 07, 08, 09): 99.3%
- Funded by the department budget (BR-21): 86.6%
- Feasible and funded: 86.6%
- Planning gaps: 2244, of which PLANNED: 59.5%

## Budgets

| Department | Limit | Proposed | Funded | Committed | Utilization | Budget rejections |
|---|---|---|---|---|---|---|
| ENG | 2,570,000 | 3,028,800 | 2,563,600 | 1,591,600 | 61.93% | 1 |
| DAT | 1,620,000 | 1,921,600 | 1,620,000 | 1,344,000 | 82.96% | 9 |
| ITS | 1,390,000 | 1,656,400 | 1,385,200 | 921,200 | 66.27% | 0 |
| SAL | 2,280,000 | 2,680,400 | 2,273,200 | 1,456,400 | 63.88% | 7 |
| MKT | 1,120,000 | 1,318,400 | 1,108,800 | 630,000 | 56.25% | 4 |
| FIN | 1,250,000 | 1,500,000 | 1,249,600 | 1,200,000 | 96.00% | 2 |
| HRM | 780,000 | 909,600 | 773,600 | 641,600 | 82.26% | 0 |
| OPS | 2,170,000 | 2,560,000 | 2,164,800 | 1,701,200 | 78.40% | 6 |
