"""
BR-05: prerequisite chains and the prerequisite check.
"""

from datetime import timedelta

from .. import config


def chain(course_id, prerequisites, passed, in_path):
    """
    Every prerequisite still needed before course_id, prerequisites first.

    prerequisites: course_id -> list of prerequisite course_ids.
    A prerequisite that is already PASSED or already in the path is not
    needed, and neither are its own prerequisites. Ties go by course_id.

    Returns a list of (course_id, required_for_course_id).
    """
    needed = []
    seen = set()

    def visit(course):
        for prerequisite in sorted(prerequisites.get(course, ())):
            if prerequisite in passed or prerequisite in in_path or prerequisite in seen:
                continue
            seen.add(prerequisite)
            visit(prerequisite)
            needed.append((prerequisite, course))

    visit(course_id)
    return needed


def path_violations(path, prerequisites, passed):
    """
    BR-05 at planning time, for one employee's RECOMMENDED rows.

    path: dicts with course_id, path_sequence, planned_start_date and
    planned_end_date. A prerequisite is satisfied if it was PASSED (by the
    planning date), or if it is earlier in the path and ends at least 14
    days before this course starts.

    Returns {course_id: [missing prerequisite course_ids]}.
    """
    gap = timedelta(days=config.SCHEDULE_GAP_DAYS)
    by_course = {step["course_id"]: step for step in path}
    violations = {}
    for step in path:
        missing = []
        for prerequisite in sorted(prerequisites.get(step["course_id"], ())):
            if prerequisite in passed:
                continue
            earlier = by_course.get(prerequisite)
            ok = (
                earlier is not None
                and earlier["path_sequence"] < step["path_sequence"]
                and earlier["planned_end_date"] + gap <= step["planned_start_date"]
            )
            if not ok:
                missing.append(prerequisite)
        if missing:
            violations[step["course_id"]] = missing
    return violations
