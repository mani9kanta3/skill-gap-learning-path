"""
The anomaly detector. It reads input tables only and never opens ground
truth. Each issue type is one documented rule, applied the same way to
every row; the validator uses these same functions for its RULE checks.

Every function returns {record_id: evidence}.
"""

from datetime import timedelta

from .. import config
from ..rules import budget, prerequisites


def prerequisite_violations(ctx):
    """BR-05 on RECOMMENDED rows, with passes known by the planning date."""
    found = {}
    for employee_id, path in ctx.path_by_employee.items():
        passed = {
            course
            for course, on in ctx.passed_by_employee.get(employee_id, {}).items()
            if on <= config.PLANNING_DATE
        }
        violations = prerequisites.path_violations(path, ctx.prerequisites, passed)
        for row in path:
            if row["course_id"] in violations:
                missing = ", ".join(violations[row["course_id"]])
                found[row["recommendation_id"]] = (
                    f"{row['course_id']} is planned without {missing} passed or planned "
                    "at least 14 days earlier in the path"
                )
    return found


def unavailable_courses(ctx):
    """BR-04 on RECOMMENDED rows: course unavailable, or planned outside the period."""
    found = {}
    for path in ctx.path_by_employee.values():
        for row in path:
            outside = not (config.PERIOD_START <= row["planned_start_date"] <= config.PERIOD_END)
            if row["course_id"] not in ctx.available or outside:
                found[row["recommendation_id"]] = (
                    f"{row['course_id']} has no offering starting in the planning period; "
                    f"planned start {row['planned_start_date']}"
                )
    return found


def budget_overruns(ctx):
    """BR-11 replayed per department in (event_on, event_id) order."""
    limits = {b["department_code"]: b["limit_amount"] for b in ctx.t["budget"]}
    flagged = budget.over_limit_approvals(ctx.approvals, limits)
    found = {}
    for enrollment_id, before in flagged.items():
        enrollment = ctx.enrollments[enrollment_id]
        department = ctx.budgets[enrollment["budget_id"]]["department_code"]
        found[enrollment_id] = (
            f"approved {enrollment['cost_amount']:,.2f} with {before:,.2f} already committed "
            f"against a {department} limit of {limits[department]:,.2f}"
        )
    return found


def duplicate_completions(ctx):
    """BR-13: every completion after the first one of the same enrollment."""
    found = {}
    for enrollment_id, rows in ctx.completions_by_enrollment.items():
        for extra in rows[1:]:
            found[extra["completion_id"]] = f"second completion of {enrollment_id}, first is {rows[0]['completion_id']}"
    return found


def missing_reassessments(ctx):
    """
    BR-17: a due CLOSES_GAP completion with no POST_COURSE assessment.

    Only the first completion of each enrollment is looked at, so a
    duplicate completion is never counted again under this type.
    """
    due_by = config.AS_OF_DATE - timedelta(days=config.REASSESSMENT_DELAY_DAYS[1])
    found = {}
    for completion in ctx.first_completions:
        enrollment = ctx.enrollments[completion["enrollment_id"]]
        rec = ctx.recommendations[enrollment["recommendation_id"]]
        if rec["reason_code"] != "CLOSES_GAP" or completion["completed_on"] > due_by:
            continue
        if not ctx.post_course_by_completion.get(completion["completion_id"]):
            found[completion["completion_id"]] = (
                f"completed {completion['completed_on']}, no post-course assessment of "
                f"{rec['target_skill_id']} by {completion['completed_on'] + timedelta(days=14)}"
            )
    return found


DETECTORS = {
    "PREREQUISITE_VIOLATION": ("BR-05", prerequisite_violations),
    "COURSE_UNAVAILABLE": ("BR-04", unavailable_courses),
    "BUDGET_EXCEEDED": ("BR-11", budget_overruns),
    "DUPLICATE_COMPLETION": ("BR-13", duplicate_completions),
    "GAP_NOT_REASSESSED": ("BR-17", missing_reassessments),
}


def detect(ctx):
    """Rows for eval.detected_issue."""
    rows = []
    for issue_type, (rule_code, detector) in DETECTORS.items():
        for record_id, evidence in sorted(detector(ctx).items()):
            rows.append(
                {"issue_type": issue_type, "record_id": record_id, "rule_code": rule_code, "evidence": evidence}
            )
    return rows
