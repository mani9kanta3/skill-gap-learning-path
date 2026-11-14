# Skill Gap to Learning Path

Match employee skill gaps to courses, prerequisites, budgets and career pathways,
end to end.

The project has three parts:

1. **A synthetic data generator** (Python, pandas). It builds 5,000 employees,
   500 skills, 1,000 courses and 10,000 enrollments from documented rules with a
   fixed seed. It then plants 250 labelled exceptions and checks every rule again
   on the final data.
2. **An API** (FastAPI on PostgreSQL). It serves the data and can re-plan any
   employee from any date with the same engine the generator used.
3. **A web app** (React). Employees, managers, HR and operations each get a view
   of gaps, paths, enrollments, budgets, exceptions and data quality.

Everything is synthetic. No external dataset and no real person is involved.

---

## Results (full scale, seed 20261022)

| What | Result |
|---|---|
| Validation checks | **150 of 150 pass**: 144 structural checks with zero failing records, plus 6 rule checks matched to ground truth record by record |
| Labelled exceptions found | **250 of 250**, no false alarms. Precision 1.000, recall 1.000 for all five types |
| Clean baseline (no injected cases) | 150 of 150 pass, every check with zero failing records |
| Reproducibility | Two runs give **46 of 46 files byte-identical** (SHA-256) at both scales |
| Exact volumes | 5,000 employees, 500 skills, 1,000 courses, 10,000 enrollments |
| Database and API | Full dataset loaded into PostgreSQL with every constraint and row count verified, then every endpoint and the dashboard checked live |
| Tests | 258 pytest tests pass |

What the data looks like:

| Funnel | Count |
|---|---|
| Proposed course steps (January plan) | 14,610 |
| Funded by department budgets | 12,701 (86.9%) |
| Requested | 10,000 |
| Approved / rejected for budget | 9,769 / 231 |
| Started / withdrawn | 9,594 / 476 |
| Completed / passed | 9,282 / 6,308 |
| Reassessed after a gap-closing course | 6,316 |

Attending, passing and learning are kept apart, as the brief asks:

- 96.8% of started courses are completed.
- 68.0% of completions pass.
- Only 52.1% of reassessed gap-closing courses actually close the gap.

Proposed steps that pass every planning check (availability, prerequisites, path
size, schedule and seats, allowance and department budget): 99.3%. Every step the
engine made passes; the only failures are the 100 planted exceptions.

---

## Quick start

You need Python 3.12, Node 20 or later, and PostgreSQL. Generated data is already
in `output/`, so steps 2 and 3 are optional.

```bash
# 1. Backend environment (from backend/)
cd backend
python -m venv venv
venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt

# 2. Generate and validate (writes output/starter and output/full)
python -m pipeline.run --scale starter
python -m pipeline.run --scale full --docs

# 3. Prove reproducibility and run the tests
python -m scripts.check_reproducibility --scale full
pytest

# 4. Load into Postgres (copy ../.env.example to backend/.env and fill it in first)
python -m scripts.create_tables --reset
python -m scripts.load_data --scale full

# 5. Start the API: http://localhost:8000/docs
uvicorn app.main:app --reload
```

```bash
# 6. Start the web app (from frontend/): http://localhost:5173
cd frontend
npm install
copy .env.example .env         # macOS/Linux: cp .env.example .env
npm run dev
```

Useful extras:

```bash
python -m pipeline.run --scale starter --no-inject --out ../output/_baseline   # the clean baseline
npm run lint                                                                  # frontend lint
```

**Generator command:** `python -m pipeline.run --scale starter|full`
**Fixed seed:** `20261022`, in `backend/pipeline/config.py`
**Scale:** starter is exactly 10% of full (500 / 50 / 100 / 1,000, with 5 cases per edge type). The same code runs both.

---

## How it works

The full design, every rule and every decision is in
[ARCHITECTURE.md](ARCHITECTURE.md). In short:

```
s01 reference   departments, 5-level career ladders, skills, role skill targets
s02 employees   current role, target role (25% on a promotion path), manager
s03 proficiency baseline skill test per skill, Q4 2025
s04 catalog     courses, the skills they teach and to which level, prerequisites
s05 offerings   course runs with dates and seats (some courses only run in 2027)
s06 plan        January planning run: the recommendation engine, per employee
s07 budgets     department limit = 85% of proposed demand, then allocated to
                proposed steps: the funded plan
s08 simulate    the whole of 2026 as one event queue: requests, approvals,
                starts, withdrawals, completions with exam results, post-course tests
s09 inject      the five labelled exception types, with ground truth kept apart
s10 finalize    assessment IDs and every derived value, recomputed from source rows
then            write CSV/JSON/SQL, read the CSVs back, validate, detect, evaluate
```

**The recommendation engine** (`backend/pipeline/rules/recommend.py`) closes an
employee's gaps against their target role, CORE skills and the biggest gaps first.
For each gap it tries the candidate courses, cheapest first. A candidate is only
accepted if it passes four checks:

1. It runs in the planning period.
2. The whole prerequisite chain fits in a path of at most 4 courses.
3. The **total** cost (the path so far, every new prerequisite and the candidate)
   fits the employee's ₹60,000 allowance and the department money still free.
4. Every course can be placed one after another, 14 days apart, in a run with a
   free seat.

A failed check moves on to the next candidate. If every candidate fails, the
reason is recorded. It only uses facts known on its planning date. The API's
preview runs the same code for any date.

**Proposed and funded are two separate plans.** The January run makes a
*proposed* plan before any budget exists. Each department's limit is then set to
85% of what its people proposed. That limit is shared out over the proposed steps,
everyone's first course before anyone's second, which gives the *funded* plan.
Only funded steps can be approved. Asking for an unfunded step is rejected for
budget, which happens 231 times at full scale.

The Budgets page keeps two questions apart:

- **Is the department over-committed?** Obligations are the funded steps plus any
  approvals outside the funded plan. When they pass the limit, the badge reads
  **"Over-committed by ₹X"**, and hovering it shows the reason.
- **How much has been spent?** "Spent so far" counts approved enrollments to date.
  "Not yet spent" is the limit minus that.

A department can be over-committed while most of its money is not spent yet,
because funded courses later in the year will use it.

**Learning outcomes come from evidence.** Each completion has an exam score and
attendance, which decide pass or fail. A gap-closing course is then followed by
a post-course skill test. The proficiency level is read from fixed score bands,
and a course can never certify above the level it teaches.

---

## Edge cases (ground truth in `output/<scale>/ground_truth/`)

| Type | Rule broken | How it appears | Count (full / starter) |
|---|---|---|---|
| Recommendation violates prerequisite | BR-05 | A RECOMMENDED course whose prerequisite is neither passed nor planned earlier | 50 / 5 |
| Course unavailable in planning period | BR-04 | A RECOMMENDED course that only runs in 2027 | 50 / 5 |
| Budget exceeded | BR-11 | An enrollment approved for a step the department budget did not fund, so the department owes more than its limit | 50 / 5 |
| Completion counted twice | BR-13 | A second completion row for the same enrollment, same date and values | 50 / 5 |
| Skill gap remains after course without reassessment | BR-17 | A completed gap-closing course with no post-course test, so the gap is still open | 50 / 5 |

Each injected record breaks exactly one rule. A test proves that each one is
caught by its own detector and by no other. Ground truth is never stored in an
input table. More detail is in [docs/edge_cases.md](docs/edge_cases.md).

---

## What is in the repository

```
ARCHITECTURE.md        design, data model, rules, edge cases, checks, build order
docs/                  data dictionary (generated), business rules, edge cases, provenance
backend/pipeline/      generator: config, dictionary, rules/, stages/, checks/, export, run
backend/app/           FastAPI: config, db, queries (raw SQL), schemas, main
backend/scripts/       create_tables, load_data, check_reproducibility
backend/tests/         258 tests: rules on hand-made data, the whole pipeline, leakage, reproducibility, API request rules
frontend/src/          React dashboard: sidebar + top bar shell; pages Dashboard, Employees,
                       Employee profile (tabs + re-plan), Courses, Course detail, Budgets,
                       Exceptions, Validation
output/starter/        csv/, json/, sql/ (schema + seed), ground_truth/, reports/, manifest.json
output/full/           the same at full scale
output/reproducibility/  two-run comparison reports (row counts + SHA-256 per file)
```

Every dataset folder has:

- `manifest.json`: seed, scale, every parameter, and a row count and SHA-256 for every file.
- `reports/validation_summary.md`: every check, with failing, expected, unexpected and missed IDs.
- `reports/evaluation.md`: detection scores, the funnel, outcomes and budgets.
- `sql/schema.sql` and `sql/seed.sql`: a portable alternative to the loader (`psql -f schema.sql -f seed.sql`).

---

## Who uses what

| Actor | Page |
|---|---|
| Employee / candidate | Employee detail: gaps, path, enrollments, results, path preview |
| Manager | Employees filtered by manager ID (a shareable link), then each person |
| HR partner | Budgets (planned vs funded vs committed), Exceptions |
| IT / operations partner | Evaluation (validation and detection), the loader |
| System administrator | The generator, the reproducibility script, this README |

---

## Data provenance and lawful use

All data is generated by this repository. Names and skill words come from short
lists written for the project (`backend/pipeline/vocab.py`). No external dataset
was downloaded, scraped or transformed, so there is nothing to license and no
personal data. See [docs/provenance.md](docs/provenance.md).

## Known trade-offs

- Injected events and completions take the next free `EVT` and `CMP` numbers, so
  the highest numbers include injected rows. IDs are not features, and the detector
  never looks at ID order. Recommendation and enrollment IDs are built from the
  employee/course pair, so injected ones look exactly like normal ones.
- `COURSE_UNAVAILABLE` is both an exception type and a normal reason the engine
  gives when it turns a course down. In the input data it is only ever that reason.
- Plans book seats, so seat rejections (`NO_SEATS`) do not happen in the generated
  year. The rule is still enforced at approval and covered by tests.
- The API caches the tables the path preview needs on first use. Restart it after
  loading a different dataset.
