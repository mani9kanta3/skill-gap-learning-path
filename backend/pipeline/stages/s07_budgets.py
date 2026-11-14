"""
s07: department budgets, and the funded plan.

Two steps, kept apart on purpose (ARCHITECTURE.md 4, "Proposed and funded"):

1. Limit. Each department's limit is FUNDING_RATIO x the cost of its
   proposed steps (the RECOMMENDED rows from s06), rounded up to 10,000.
2. Allocation (BR-21). The limit is shared out over those proposed
   steps, everyone's first step before anyone's second. A step that gets money is
   FUNDED; the rest are NOT_FUNDED_BUDGET, or NOT_FUNDED_PREREQUISITE
   when a prerequisite step in the same path was not funded.

So the January data holds two plans: the proposed plan (every RECOMMENDED
row, feasible on dates, seats, prerequisites and the allowance) and the
funded plan (the FUNDED rows, which never cost more than the limit).
Only funded steps can be approved later (BR-11).

Setting the limit from the proposals cannot change the proposals: in
January nothing is committed or allocated yet, so BR-09(b) only asks
whether one employee's whole path costs more than the department's whole
budget. A path never costs more than the 60,000 allowance, and run()
stops if any limit is below that, which proves BR-09(b) changed nothing.
"""

from collections import defaultdict

from .. import config, ids
from ..rules import budget


def run(tables, plan):
    employees = {e["employee_id"]: e for e in tables["employee"]}
    prerequisites = defaultdict(list)
    for row in tables["course_prerequisite"]:
        prerequisites[row["course_id"]].append(row["prerequisite_course_id"])

    proposed = defaultdict(list)
    for row in tables["recommendation"]:
        if row["decision"] == "RECOMMENDED":
            proposed[employees[row["employee_id"]]["department_code"]].append(row)

    rows = []
    status = {}
    for code in config.DEPARTMENT_CODES:
        demand = sum(r["estimated_cost"] for r in proposed[code])
        limit = budget.department_limit(demand, config.FUNDING_RATIO)
        if limit < config.LEARNING_ALLOWANCE_PER_EMPLOYEE:
            raise RuntimeError(
                f"The {code} budget ({limit}) is below one employee's allowance, so BR-09(b) "
                "could have changed the January proposals. Raise FUNDING_RATIO or the scale."
            )
        department_status, _ = budget.allocate(proposed[code], limit, prerequisites)
        status.update(department_status)
        rows.append(
            {
                "budget_id": ids.budget_id(code),
                "department_code": code,
                "fiscal_year": config.FISCAL_YEAR,
                "limit_amount": limit,
                "planned_amount": None,
                "funded_amount": None,
                "committed_amount": None,
                "remaining_amount": None,
                "utilization_pct": None,
                "budget_status": None,
                "currency": config.CURRENCY,
            }
        )

    for row in tables["recommendation"]:
        if row["decision"] == "RECOMMENDED":
            row["funding_status"] = status[row["recommendation_id"]]
    tables["budget"] = rows
    return tables
