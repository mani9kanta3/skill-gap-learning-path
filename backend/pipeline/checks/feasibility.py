"""
Is each proposed (RECOMMENDED) step feasible? Every planning condition,
not just some of them.

    BR-04  the course runs in the planning period, and the planned run starts inside it
    BR-05  prerequisites passed, or planned earlier and ending 14+ days before
    BR-07  the employee's path has at most 4 courses
    BR-08  the planned run is a run of this course, starts 14+ days after the
           planning date and 14+ days after the previous step ends, and the
           plans booked on that run do not exceed its seats
    BR-09  the path's running cost stays within the allowance, and the whole
           path costs no more than the department's limit (in January
           nothing is committed or allocated, so the limit is what is free)

Funding (BR-21) is a separate question with its own metric: a step can be
perfectly feasible and still not be funded.

Returns {recommendation_id: [rule codes it fails]} for the steps that fail.
"""

from collections import Counter, defaultdict
from datetime import timedelta

from .. import config
from ..rules import prerequisites


def failures(ctx):
    gap = timedelta(days=config.SCHEDULE_GAP_DAYS)
    planned_seats = Counter(
        r["planned_offering_id"] for r in ctx.t["recommendation"] if r["decision"] == "RECOMMENDED"
    )
    limits = {b["department_code"]: b["limit_amount"] for b in ctx.t["budget"]}
    failed = defaultdict(list)

    for employee_id, path in ctx.path_by_employee.items():
        violations = prerequisites.path_violations(path, ctx.prerequisites, set())
        department = ctx.employees[employee_id]["department_code"]
        path_total = sum(r["estimated_cost"] for r in path)
        previous_end = None
        for r in path:
            rid = r["recommendation_id"]
            offering = ctx.offerings[r["planned_offering_id"]]
            start = r["planned_start_date"]

            if r["course_id"] not in ctx.available or not config.PERIOD_START <= start <= config.PERIOD_END:
                failed[rid].append("BR-04")
            if r["course_id"] in violations:
                failed[rid].append("BR-05")
            if len(path) > config.MAX_PATH_COURSES:
                failed[rid].append("BR-07")
            if (
                offering["course_id"] != r["course_id"]
                or start < config.PLANNING_DATE + gap
                or (previous_end is not None and start < previous_end + gap)
                or planned_seats[offering["offering_id"]] > offering["capacity"]
            ):
                failed[rid].append("BR-08")
            if r["cumulative_cost"] > config.LEARNING_ALLOWANCE_PER_EMPLOYEE or path_total > limits[department]:
                failed[rid].append("BR-09")
            previous_end = r["planned_end_date"]

    return dict(failed)
