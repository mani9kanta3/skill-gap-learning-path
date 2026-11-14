"""
Budget rules.

- department_limit: the policy that sets a department's limit.
- BR-09: the planning checks. The employee's allowance, and the
  department money still free on the planning date. Both are checked
  against the TOTAL cost: what is already on the path, plus every new
  prerequisite, plus the candidate. Checking each course on its own
  would let two 7,000 courses through when only 10,000 is free.
- BR-21: allocate a department's limit to proposed steps (the funded plan).
- BR-11: only a funded step may be approved.
"""

import math

from .. import config


def department_limit(proposed_demand, funding_ratio):
    """proposed demand x funding ratio, rounded up to the next 10,000."""
    # Round to cents first: 2965200 x 0.62 is 1838424.0000000002 in floating
    # point, and that stray fraction must not decide which 10,000 we land on.
    raw = round(proposed_demand * funding_ratio, 2)
    step = config.BUDGET_ROUNDING
    return math.ceil(raw / step) * step


def within_allowance(spent, path_cost, extra_cost, allowance=config.LEARNING_ALLOWANCE_PER_EMPLOYEE):
    """BR-09(a): spent this period + already on the path + the new courses fits the allowance."""
    return spent + path_cost + extra_cost <= allowance


def fits_department(path_cost, extra_cost, department_free):
    """
    BR-09(b): the path's whole cost fits the department money still free.

    department_free = limit - committed - money already allocated to other
    open funded steps, all as of the planning date (see snapshot.py).
    """
    return path_cost + extra_cost <= department_free


def allocate(steps, limit, prerequisites):
    """
    BR-21: share one department's limit out over its proposed steps.

    steps: RECOMMENDED rows of one department. Everyone's first step is
    funded before anyone's second, and so on (within a round: earliest
    planned start, then employee_id). That way as many people as possible
    get their path started, instead of a few people getting all four
    courses while others get none. A step is
      NOT_FUNDED_PREREQUISITE  if an earlier step of the same path that it
                               needs (a prerequisite) was not funded,
      FUNDED                   if it fits what is left of the limit,
      NOT_FUNDED_BUDGET        otherwise.

    Returns {recommendation_id: status} and the total funded.
    """
    status = {}
    allocated = 0.0
    funded_courses = {}
    ordered = sorted(steps, key=lambda r: (r["path_sequence"], r["planned_start_date"], r["employee_id"]))
    in_path = {}
    for row in steps:
        in_path.setdefault(row["employee_id"], set()).add(row["course_id"])

    for row in ordered:
        employee = row["employee_id"]
        needed = [p for p in prerequisites.get(row["course_id"], ()) if p in in_path[employee]]
        if any(p not in funded_courses.get(employee, set()) for p in needed):
            status[row["recommendation_id"]] = "NOT_FUNDED_PREREQUISITE"
        elif allocated + row["estimated_cost"] <= limit:
            allocated += row["estimated_cost"]
            funded_courses.setdefault(employee, set()).add(row["course_id"])
            status[row["recommendation_id"]] = "FUNDED"
        else:
            status[row["recommendation_id"]] = "NOT_FUNDED_BUDGET"
    return status, allocated


def can_approve(funding_status, committed, cost, limit):
    """
    BR-11: approve only a FUNDED step. Because funded steps never add up
    to more than the limit, approvals can then never overspend it; the
    running-total test is kept as a second guard.
    """
    return funding_status == "FUNDED" and committed + cost <= limit


def obligations(funded_amount, approved_outside_plan):
    """What the department owes: every funded step plus anything approved outside the funded plan."""
    return funded_amount + approved_outside_plan
