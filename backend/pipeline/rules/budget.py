"""
Budget rules: the department limit (policy), BR-09 (planning) and BR-11
(approval).
"""

import math

from .. import config


def department_limit(planned_demand, funding_ratio):
    """planned demand x funding ratio, rounded up to the next 10,000."""
    # Round to cents first: 2965200 x 0.62 is 1838424.0000000002 in floating
    # point, and that stray fraction must not decide which 10,000 we land on.
    raw = round(planned_demand * funding_ratio, 2)
    step = config.BUDGET_ROUNDING
    return math.ceil(raw / step) * step


def within_allowance(spent, path_cost, extra_cost, allowance=config.LEARNING_ALLOWANCE_PER_EMPLOYEE):
    """BR-09(a): everything already spent or planned, plus the new courses, fits."""
    return spent + path_cost + extra_cost <= allowance


def fits_department(costs, department_remaining):
    """BR-09(b): no single course costs more than the department has left."""
    return all(cost <= department_remaining for cost in costs)


def can_approve(committed, cost, limit):
    """BR-11: approve only if the running total stays within the limit. Equal is fine."""
    return committed + cost <= limit


def over_limit_approvals(approvals, limits):
    """
    BR-11 replayed over finished data.

    approvals: dicts with department_code, event_on, event_id, enrollment_id
    and cost, one per APPROVED event. They are walked per department in
    (event_on, event_id) order, which is the order the simulation decided
    them in. Returns {enrollment_id: committed_before} for every approval
    that broke the limit.
    """
    committed = {code: 0.0 for code in limits}
    flagged = {}
    for row in sorted(approvals, key=lambda r: (r["event_on"], r["event_id"])):
        code = row["department_code"]
        before = committed[code]
        if not can_approve(before, row["cost"], limits[code]):
            flagged[row["enrollment_id"]] = before
        committed[code] = before + row["cost"]
    return flagged
