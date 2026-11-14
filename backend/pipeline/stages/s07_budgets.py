"""
s07: one budget per department, limit only. The totals are derived in s10.

limit = FUNDING_RATIO x planned demand, rounded up to 10,000.

Why budgets come after the January plan: the limit is set from what the
plan asks for. That does not make the plan depend on itself. In January
nothing is committed yet, so BR-09(b) only asks "is any single course
dearer than the whole department budget?". run() checks that every limit
is above the dearest course, which proves BR-09(b) could not have
changed a single January decision. (It does bind in mid-year previews.)
"""

from .. import config, ids
from ..rules import budget


def run(tables, plan):
    employees = {e["employee_id"]: e for e in tables["employee"]}
    demand = {code: 0.0 for code in config.DEPARTMENT_CODES}
    for row in tables["recommendation"]:
        if row["decision"] == "RECOMMENDED":
            demand[employees[row["employee_id"]]["department_code"]] += row["estimated_cost"]

    dearest = max(course["cost_amount"] for course in tables["course"])
    rows = []
    for code in config.DEPARTMENT_CODES:
        limit = budget.department_limit(demand[code], config.FUNDING_RATIO)
        if limit < dearest:
            raise RuntimeError(
                f"The {code} budget ({limit}) is below the dearest course ({dearest}), so "
                "BR-09(b) could have changed the January plan. Raise FUNDING_RATIO or the scale."
            )
        rows.append(
            {
                "budget_id": ids.budget_id(code),
                "department_code": code,
                "fiscal_year": config.FISCAL_YEAR,
                "limit_amount": limit,
                "planned_amount": None,
                "committed_amount": None,
                "remaining_amount": None,
                "utilization_pct": None,
                "budget_status": None,
                "currency": config.CURRENCY,
            }
        )
    tables["budget"] = rows
    return tables
