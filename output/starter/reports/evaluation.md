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
| recommended | 1399 |
| requested | 1000 |
| approved | 915 |
| rejected | 85 |
| started | 903 |
| withdrawn | 40 |
| completed | 874 |
| passed | 664 |
| reassessed | 540 |

## Attendance, passing and learning are different numbers

- Completed, of started: 96.8%
- Passed, of completed: 76.0%
- Gap closed, of reassessed gap-closing courses: 54.3%
- Average level uplift after a PASSED course: 1.26
- Average level uplift after a FAILED course: 0.25
- Reassessment coverage of due completions: 99.1%

## Recommendations

- RECOMMENDED rows: 1399
- Feasible (BR-04 and BR-05 hold): 99.3%
- Planning gaps: 2244, of which PLANNED: 60.7%

## Budgets

| Department | Limit | Planned | Committed | Utilization | Budget rejections |
|---|---|---|---|---|---|
| ENG | 1,840,000 | 3,013,200 | 1,450,800 | 78.85% | 0 |
| DAT | 1,390,000 | 2,252,800 | 1,392,000 | 100.14% | 9 |
| ITS | 1,010,000 | 1,623,600 | 1,017,600 | 100.75% | 17 |
| SAL | 1,310,000 | 2,102,000 | 1,312,400 | 100.18% | 0 |
| MKT | 1,010,000 | 1,626,000 | 769,200 | 76.16% | 0 |
| FIN | 1,070,000 | 1,720,800 | 1,089,600 | 101.83% | 7 |
| HRM | 560,000 | 909,200 | 555,200 | 99.14% | 15 |
| OPS | 1,670,000 | 2,698,000 | 1,693,200 | 101.39% | 37 |
