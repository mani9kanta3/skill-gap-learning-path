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
| recommended | 13421 |
| requested | 10000 |
| approved | 9039 |
| rejected | 961 |
| started | 8884 |
| withdrawn | 461 |
| completed | 8534 |
| passed | 5773 |
| reassessed | 5744 |

## Attendance, passing and learning are different numbers

- Completed, of started: 96.1%
- Passed, of completed: 67.7%
- Gap closed, of reassessed gap-closing courses: 52.8%
- Average level uplift after a PASSED course: 1.22
- Average level uplift after a FAILED course: 0.24
- Reassessment coverage of due completions: 99.1%

## Recommendations

- RECOMMENDED rows: 13421
- Feasible (BR-04 and BR-05 hold): 99.2%
- Planning gaps: 22181, of which PLANNED: 46.5%

## Budgets

| Department | Limit | Planned | Committed | Utilization | Budget rejections |
|---|---|---|---|---|---|
| ENG | 12,160,000 | 20,148,400 | 12,210,800 | 100.42% | 280 |
| DAT | 9,520,000 | 15,456,000 | 9,581,200 | 100.64% | 48 |
| ITS | 12,520,000 | 20,314,000 | 12,612,800 | 100.74% | 45 |
| SAL | 9,560,000 | 15,425,600 | 9,627,200 | 100.70% | 172 |
| MKT | 6,580,000 | 11,392,800 | 6,610,400 | 100.46% | 26 |
| FIN | 8,910,000 | 14,388,000 | 9,018,800 | 101.22% | 29 |
| HRM | 5,560,000 | 8,978,400 | 5,630,000 | 101.26% | 54 |
| OPS | 11,880,000 | 19,300,800 | 11,942,000 | 100.52% | 307 |
