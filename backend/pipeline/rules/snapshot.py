"""
BR-20: what the data looked like on a given planning date.

The plan may only use facts that were known on its planning date. The
January run sees Q4 2025 assessments, no completions, empty classes and
full budgets. A preview for 1 July sees July's levels, July's passed
courses, July's seat counts and July's remaining budget.

Both the generator and the API build their inputs with this, so the
point-in-time rule is written once.

Tables are passed as lists of dicts, with dates as datetime.date.
"""

from collections import defaultdict
from dataclasses import dataclass, field

from .. import config


@dataclass
class Catalog:
    """Everything that does not depend on the planning date."""

    courses: dict  # course_id -> dict(course_status, course_level, cost_amount, duration_hours, skill_category)
    course_skills: dict  # course_id -> {skill_id: target_level}
    covering: dict  # skill_id -> [(course_id, target_level)]
    prerequisites: dict  # course_id -> [prerequisite course_ids]
    offerings_by_course: dict  # course_id -> [offering dicts sorted by start_date]
    offerings: dict  # offering_id -> offering dict
    role_targets: dict  # role_id -> [dict(skill_id, target_level, importance)]
    department_limit: dict  # department_code -> limit_amount
    budget_department: dict  # budget_id -> department_code
    employee_department: dict = field(default_factory=dict)  # employee_id -> department_code


def build_catalog(tables, fiscal_year=config.FISCAL_YEAR):
    """
    fiscal_year picks which year's budgets apply. The data holds 2026 only,
    and the API refuses periods outside it, so a 2027 plan can never be
    checked against a 2026 budget.
    """
    courses = {
        row["course_id"]: {
            "course_status": row["course_status"],
            "course_level": row["course_level"],
            "cost_amount": float(row["cost_amount"]),
            "duration_hours": int(row["duration_hours"]),
            "skill_category": row["skill_category"],
        }
        for row in tables["course"]
    }

    course_skills = defaultdict(dict)
    covering = defaultdict(list)
    for row in tables["course_skill"]:
        course_skills[row["course_id"]][row["skill_id"]] = int(row["target_level"])
        covering[row["skill_id"]].append((row["course_id"], int(row["target_level"])))

    prerequisites = defaultdict(list)
    for row in tables["course_prerequisite"]:
        prerequisites[row["course_id"]].append(row["prerequisite_course_id"])

    offerings = {}
    offerings_by_course = defaultdict(list)
    for row in tables["course_offering"]:
        offering = {
            "offering_id": row["offering_id"],
            "course_id": row["course_id"],
            "start_date": row["start_date"],
            "end_date": row["end_date"],
            "capacity": int(row["capacity"]),
        }
        offerings[offering["offering_id"]] = offering
        offerings_by_course[offering["course_id"]].append(offering)
    for course_offerings in offerings_by_course.values():
        course_offerings.sort(key=lambda o: (o["start_date"], o["offering_id"]))

    role_targets = defaultdict(list)
    for row in tables["role_skill_target"]:
        role_targets[row["role_id"]].append(
            {
                "skill_id": row["skill_id"],
                "target_level": int(row["target_level"]),
                "importance": row["importance"],
            }
        )
    for targets in role_targets.values():
        targets.sort(key=lambda t: t["skill_id"])

    # Budgets are set after the January plan (see s07_budgets), so the
    # January run builds its catalog before any budget exists. A missing
    # limit means "not set yet", which the planner treats as unlimited.
    budgets = [row for row in tables.get("budget", ()) if int(row["fiscal_year"]) == fiscal_year]
    department_limit = {row["department_code"]: float(row["limit_amount"]) for row in budgets}
    budget_department = {row["budget_id"]: row["department_code"] for row in tables.get("budget", ())}

    return Catalog(
        courses=courses,
        course_skills=dict(course_skills),
        covering=dict(covering),
        prerequisites=dict(prerequisites),
        offerings_by_course=dict(offerings_by_course),
        offerings=offerings,
        role_targets=dict(role_targets),
        department_limit=department_limit,
        budget_department=budget_department,
        employee_department={e["employee_id"]: e["department_code"] for e in tables.get("employee", ())},
    )


@dataclass
class Snapshot:
    planning_date: object
    period_start: object
    period_end: object
    levels: dict = field(default_factory=dict)  # (employee_id, skill_id) -> level
    scores: dict = field(default_factory=dict)  # (employee_id, skill_id) -> score
    passed: dict = field(default_factory=lambda: defaultdict(set))  # employee_id -> course_ids
    blocked: dict = field(default_factory=lambda: defaultdict(set))  # employee_id -> course_ids
    busy_until: dict = field(default_factory=dict)  # employee_id -> date
    spent: dict = field(default_factory=lambda: defaultdict(float))  # employee_id -> money
    committed: dict = field(default_factory=lambda: defaultdict(float))  # department -> money
    seats_approved: dict = field(default_factory=lambda: defaultdict(int))  # offering_id -> count
    # Money allocated to FUNDED steps that are still open on the date (not
    # yet decided, start still ahead), per department and per employee.
    reserved: dict = field(default_factory=lambda: defaultdict(float))
    reserved_by_employee: dict = field(default_factory=lambda: defaultdict(float))

    def department_free(self, catalog, employee):
        """
        BR-09(b): limit - committed - money allocated to other people's open
        funded steps. The employee's own open steps are left out, because a
        re-plan for them replaces those steps.
        """
        department = employee["department_code"]
        limit = catalog.department_limit.get(department, float("inf"))
        others = self.reserved.get(department, 0.0) - self.reserved_by_employee.get(employee["employee_id"], 0.0)
        return limit - self.committed.get(department, 0.0) - others


def build_snapshot(tables, catalog, planning_date, period_start, period_end):
    """
    The state of the world at the end of planning_date.

    Needs proficiency_assessment, completion, enrollment and
    enrollment_event in `tables` (any may be empty).
    """
    snap = Snapshot(planning_date, period_start, period_end)

    # Latest assessment on or before the date. Ties on the same day go to
    # the later assessment id, so the answer never depends on row order.
    latest = {}
    for row in tables.get("proficiency_assessment", ()):
        if row["assessed_on"] > planning_date:
            continue
        key = (row["employee_id"], row["skill_id"])
        rank = (row["assessed_on"], row.get("assessment_id") or "")
        if key not in latest or rank > latest[key][0]:
            latest[key] = (rank, int(row["proficiency_level"]), int(row["assessment_score"]))
    for key, (_, level, score) in latest.items():
        snap.levels[key] = level
        snap.scores[key] = score

    enrollments = {row["enrollment_id"]: row for row in tables.get("enrollment", ())}

    for row in tables.get("completion", ()):
        if row["completed_on"] <= planning_date and row["result"] == "PASSED":
            enrollment = enrollments[row["enrollment_id"]]
            snap.passed[enrollment["employee_id"]].add(enrollment["course_id"])

    for row in enrollments.values():
        if row["requested_on"] <= planning_date:
            snap.blocked[row["employee_id"]].add(row["course_id"])

    decided = set()
    events = defaultdict(list)
    for row in tables.get("enrollment_event", ()):
        if row["event_on"] <= planning_date:
            events[row["enrollment_id"]].append(row)

    for enrollment_id, history in events.items():
        enrollment = enrollments[enrollment_id]
        approved = [e for e in history if e["to_status"] == "APPROVED"]
        if approved:
            cost = float(enrollment["cost_amount"])
            snap.seats_approved[enrollment["offering_id"]] += 1
            department = catalog.budget_department[enrollment["budget_id"]]
            snap.committed[department] += cost
            if period_start <= approved[0]["event_on"] <= period_end:
                snap.spent[enrollment["employee_id"]] += cost

        last = max(history, key=lambda e: e["event_seq"])["to_status"]
        if any(e["to_status"] in ("APPROVED", "REJECTED") for e in history):
            decided.add(enrollment_id)
        if last in ("APPROVED", "IN_PROGRESS"):
            end = catalog.offerings[enrollment["offering_id"]]["end_date"]
            employee = enrollment["employee_id"]
            snap.busy_until[employee] = max(end, snap.busy_until.get(employee, end))

    # Open funded allocations (BR-21). A step stops holding money once its
    # enrollment is decided (approved money is in `committed` instead) or
    # once its planned start is no longer ahead.
    by_recommendation = {e.get("recommendation_id"): e["enrollment_id"] for e in enrollments.values()}
    for row in tables.get("recommendation", ()):
        if row.get("funding_status") != "FUNDED" or row["planned_start_date"] <= planning_date:
            continue
        if by_recommendation.get(row["recommendation_id"]) in decided:
            continue
        department = catalog.employee_department.get(row["employee_id"])
        if department is None:
            continue
        cost = float(row["estimated_cost"])
        snap.reserved[department] += cost
        snap.reserved_by_employee[row["employee_id"]] += cost

    return snap


def free_seats(catalog, snapshot):
    """capacity - seats approved by the planning date, for every offering."""
    return {
        offering_id: offering["capacity"] - snapshot.seats_approved.get(offering_id, 0)
        for offering_id, offering in catalog.offerings.items()
    }
