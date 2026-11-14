"""
The recommendation engine (ARCHITECTURE.md 5.2). BR-01 to BR-09, BR-20.

It is a pure function of (employee, catalog, snapshot, seat ledger,
settings). The January planning run in s07 calls it for every employee,
the validator calls it again to reconcile the stored plan, and the API's
preview calls it for one employee on any date. All three get identical
answers for identical inputs.

The shape of the search, for each gap:

    candidates in BR-06 order
      -> check availability, path size, budget, schedule (in that order)
      -> the first candidate that passes all four goes on the path
      -> a failure only moves on to the next candidate
      -> if every candidate fails, one NOT_RECOMMENDED row records why
"""

from dataclasses import dataclass

from .. import config, ids
from . import availability, budget, gaps, prerequisites, schedule


@dataclass(frozen=True)
class Settings:
    planning_date: object
    period_start: object
    period_end: object
    allowance: float = config.LEARNING_ALLOWANCE_PER_EMPLOYEE
    max_path: int = config.MAX_PATH_COURSES


class Planner:
    """The catalog plus the period's availability, worked out once per run."""

    def __init__(self, catalog, settings):
        self.catalog = catalog
        self.settings = settings
        self.available = {
            course_id
            for course_id, course in catalog.courses.items()
            if availability.is_available(
                course["course_status"],
                [o["start_date"] for o in catalog.offerings_by_course.get(course_id, ())],
                settings.period_start,
                settings.period_end,
            )
        }

    # ---------- small lookups ----------

    def cost(self, course_id):
        return self.catalog.courses[course_id]["cost_amount"]

    def rank_key(self, course_id):
        """BR-06: available first, then cheapest, then shortest, then lowest id."""
        course = self.catalog.courses[course_id]
        return (
            0 if course_id in self.available else 1,
            course["cost_amount"],
            course["duration_hours"],
            course_id,
        )

    def covers(self, course_id, skill_id, target_level):
        """BR-03."""
        course = self.catalog.courses[course_id]
        level = self.catalog.course_skills.get(course_id, {}).get(skill_id)
        return course["course_status"] == "ACTIVE" and level is not None and level >= target_level

    def covering_courses(self, skill_id, target_level):
        """Every ACTIVE course that covers the gap, in BR-06 order."""
        found = {
            course_id
            for course_id, _ in self.catalog.covering.get(skill_id, ())
            if self.covers(course_id, skill_id, target_level)
        }
        return sorted(found, key=self.rank_key)

    def targets(self, employee):
        """The target role's skills with the employee's level at the planning date."""
        return self.catalog.role_targets.get(employee["target_role_id"], [])

    # ---------- the engine ----------

    def recommend(self, employee, snapshot, ledger):
        """
        Plan one employee. Returns (rows, gap_rows).

        rows: recommendation dicts (RECOMMENDED path + NOT_RECOMMENDED rows).
        gap_rows: one dict per target-role skill with its plan_status.
        The ledger is updated with the seats this plan books.
        """
        employee_id = employee["employee_id"]
        s = self.settings

        if employee["employment_status"] != "ACTIVE":  # BR-02
            return [], self.gap_rows(employee, snapshot, [])

        passed = snapshot.passed.get(employee_id, set())
        blocked = snapshot.blocked.get(employee_id, set())
        spent = snapshot.spent.get(employee_id, 0.0)
        department = employee["department_code"]
        department_remaining = (
            self.catalog.department_limit.get(department, float("inf"))
            - snapshot.committed.get(department, 0.0)
        )

        path = []  # dicts in path order
        rows_by_course = {}  # course_id -> row, RECOMMENDED or NOT_RECOMMENDED
        slot = schedule.first_slot(s.planning_date, snapshot.busy_until.get(employee_id))

        # BR-01 ordering: CORE first, bigger gap first, then skill_id.
        open_gaps = []
        for target in self.targets(employee):
            level = snapshot.levels.get((employee_id, target["skill_id"]), 0)
            size = gaps.gap(target["target_level"], level)
            if size > 0:
                open_gaps.append((0 if target["importance"] == "CORE" else 1, -size, target["skill_id"], target))
        open_gaps.sort(key=lambda g: g[:3])

        for _, _, skill_id, target in open_gaps:
            target_level = target["target_level"]

            # 2a: something already on the path covers it.
            if any(self.covers(step["course_id"], skill_id, target_level) for step in path):
                continue

            # 2b: candidates. Courses already enrolled in (BR-18) or already
            # holding a row for this employee cannot get another one.
            candidates = [
                c
                for c in self.covering_courses(skill_id, target_level)
                if c not in blocked and c not in rows_by_course
            ]
            if not candidates:
                continue

            in_path = {step["course_id"] for step in path}
            failures = []
            placed_ok = False

            for candidate in candidates:
                needed = prerequisites.chain(candidate, self.catalog.prerequisites, passed, in_path)
                chain_ids = [course for course, _ in needed]
                reason = self.check_candidate(
                    candidate,
                    chain_ids,
                    blocked,
                    path,
                    spent,
                    department_remaining,
                    slot,
                    ledger,
                )
                if isinstance(reason, str):
                    failures.append((candidate, reason))
                    continue

                # Every check passed: append the chain and the candidate.
                placement = reason
                required_for = dict(needed)
                for course_id, offering in placement:
                    if course_id in rows_by_course:
                        # The monotonic argument in ARCHITECTURE.md says this
                        # cannot happen. If it ever does, stop loudly rather
                        # than write a second row for the pair.
                        raise RuntimeError(f"{employee_id} already has a row for {course_id}.")
                    ledger.book(offering["offering_id"])
                    is_candidate = course_id == candidate
                    step = self.row(
                        employee_id,
                        course_id,
                        skill_id,
                        "RECOMMENDED",
                        "CLOSES_GAP" if is_candidate else "PREREQUISITE_FOR",
                        required_for=None if is_candidate else required_for[course_id],
                        offering=offering,
                    )
                    path.append(step)
                    rows_by_course[course_id] = step
                slot = schedule.next_slot(placement[-1][1]["end_date"])
                placed_ok = True
                break

            if not placed_ok:
                # 2d: one row for the best-ranked candidate, with its reason.
                best, reason = failures[0]
                rows_by_course[best] = self.row(employee_id, best, skill_id, "NOT_RECOMMENDED", reason)

        # Path order and running cost.
        cumulative = spent
        for sequence, step in enumerate(path, start=1):
            step["path_sequence"] = sequence
            cumulative += step["estimated_cost"]
            step["cumulative_cost"] = cumulative - spent

        rows = sorted(
            rows_by_course.values(),
            key=lambda r: (r["path_sequence"] is None, r["path_sequence"] or 0, r["course_id"]),
        )
        return rows, self.gap_rows(employee, snapshot, rows)

    def check_candidate(self, candidate, chain_ids, blocked, path, spent, department_remaining, slot, ledger):
        """
        Run the four checks in order. Returns a reason string on the first
        failure, or the placement (list of (course_id, offering)) on success.
        """
        s = self.settings

        # 1. Availability (BR-04). A prerequisite that was already enrolled
        #    in but never passed can never be taken again (BR-18), so it is
        #    as unavailable as a retired one.
        if candidate not in self.available:
            return "COURSE_UNAVAILABLE"
        if any(c not in self.available or c in blocked for c in chain_ids):
            return "PREREQUISITE_UNAVAILABLE"

        # 2. Path size (BR-07): the whole chain fits, or the candidate is out.
        if len(path) + len(chain_ids) + 1 > s.max_path:
            return "PATH_LIMIT"

        # 3. Budget (BR-09).
        new_costs = [self.cost(c) for c in chain_ids + [candidate]]
        path_cost = sum(step["estimated_cost"] for step in path)
        if not budget.within_allowance(spent, path_cost, sum(new_costs), s.allowance):
            return "OVER_BUDGET"
        if not budget.fits_department(new_costs, department_remaining):
            return "OVER_BUDGET"

        # 4. Schedule and seats (BR-08). Placing the chain before the
        #    candidate, 14 days apart, also proves each prerequisite ends
        #    before its dependent starts (BR-05).
        placement = schedule.place(
            chain_ids + [candidate],
            slot,
            s.period_end,
            self.catalog.offerings_by_course,
            ledger,
        )
        if placement is None:
            return "NO_SCHEDULE"
        return placement

    def row(self, employee_id, course_id, skill_id, decision, reason, required_for=None, offering=None):
        s = self.settings
        return {
            "recommendation_id": ids.recommendation_id(employee_id, course_id),
            "employee_id": employee_id,
            "course_id": course_id,
            "target_skill_id": skill_id,
            "required_for_course_id": required_for,
            "decision": decision,
            "reason_code": reason,
            "path_sequence": None,
            "planned_offering_id": offering["offering_id"] if offering else None,
            "planned_start_date": offering["start_date"] if offering else None,
            "planned_end_date": offering["end_date"] if offering else None,
            "estimated_cost": self.cost(course_id),
            "cumulative_cost": None,
            "planning_date": s.planning_date,
            "period_start": s.period_start,
            "period_end": s.period_end,
        }

    # ---------- plan_status (5.2, also used by s10) ----------

    def gap_rows(self, employee, snapshot, rows):
        """One row per target-role skill, with planning level, gap and plan_status."""
        employee_id = employee["employee_id"]
        result = []
        for target in self.targets(employee):
            level = snapshot.levels.get((employee_id, target["skill_id"]), 0)
            result.append(
                {
                    "employee_id": employee_id,
                    "skill_id": target["skill_id"],
                    "target_level": target["target_level"],
                    "planning_level": level,
                    "planning_gap": gaps.gap(target["target_level"], level),
                    "plan_status": self.plan_status(employee, target, level, rows),
                }
            )
        return result

    def plan_status(self, employee, target, level, rows):
        """
        The status of one gap, derived only from the employee's rows.

        EMPLOYEE_ON_LEAVE, then NO_GAP, then PLANNED if a RECOMMENDED course
        covers it, then NO_COURSE if no ACTIVE course covers it, otherwise
        the reason on the NOT_RECOMMENDED row of the highest-ranked covering
        course that has one.
        """
        skill_id, target_level = target["skill_id"], target["target_level"]
        if employee["employment_status"] != "ACTIVE":
            return "EMPLOYEE_ON_LEAVE"
        if gaps.gap(target_level, level) == 0:
            return "NO_GAP"
        if any(
            r["decision"] == "RECOMMENDED" and self.covers(r["course_id"], skill_id, target_level)
            for r in rows
        ):
            return "PLANNED"
        not_recommended = {r["course_id"]: r for r in rows if r["decision"] == "NOT_RECOMMENDED"}
        for course_id in self.covering_courses(skill_id, target_level):
            if course_id in not_recommended:
                return not_recommended[course_id]["reason_code"]
        return "NO_COURSE"
