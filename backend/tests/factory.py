"""
A tiny hand-made world for the rule tests.

The rule tests need catalogs where I chose every cost, date and seat, so
that "the cheaper course with a too-long chain loses to the dearer one
with no chain" is a fact about the test and not about the random data.
"""

from datetime import date

from pipeline import ids
from pipeline.rules import recommend, schedule, snapshot

PLANNING = date(2026, 1, 5)  # a Monday
PERIOD = (date(2026, 1, 1), date(2026, 12, 31))

S1 = "SKL-000001"
S2 = "SKL-000002"
S3 = "SKL-000003"
ROLE = "ROL-000001"
EMP = "EMP-000001"


def c(n):
    return ids.course_id(n)


class World:
    def __init__(self, limit=10_000_000):
        self.tables = {
            "course": [],
            "course_skill": [],
            "course_prerequisite": [],
            "course_offering": [],
            "role_skill_target": [],
            "budget": [
                {"budget_id": "BUD-ENG-2026", "department_code": "ENG", "fiscal_year": 2026, "limit_amount": limit}
            ],
            "proficiency_assessment": [],
            "completion": [],
            "enrollment": [],
            "enrollment_event": [],
        }
        self.employees = {}
        self._offerings = 0

    def course(self, n, skills, cost=1000, hours=4, starts=(date(2026, 2, 2),), status="ACTIVE",
               level="FOUNDATION", capacity=10, prereqs=()):
        """skills: {skill_id: target_level}."""
        course_id = c(n)
        self.tables["course"].append(
            {
                "course_id": course_id,
                "course_status": status,
                "course_level": level,
                "cost_amount": cost,
                "duration_hours": hours,
                "skill_category": "Software Engineering",
            }
        )
        for skill_id, target in skills.items():
            self.tables["course_skill"].append(
                {"course_id": course_id, "skill_id": skill_id, "target_level": target}
            )
        for p in prereqs:
            self.tables["course_prerequisite"].append(
                {"course_id": course_id, "prerequisite_course_id": c(p)}
            )
        for start in starts:
            self._offerings += 1
            self.tables["course_offering"].append(
                {
                    "offering_id": ids.offering_id(self._offerings),
                    "course_id": course_id,
                    "start_date": start,
                    "end_date": schedule.end_date(start, hours),
                    "capacity": capacity,
                }
            )
        return course_id

    def target(self, skill_id, level, importance="CORE", role=ROLE):
        self.tables["role_skill_target"].append(
            {"role_id": role, "skill_id": skill_id, "target_level": level, "importance": importance}
        )

    def employee(self, employee_id=EMP, levels=None, status="ACTIVE", assessed_on=date(2025, 12, 1)):
        self.employees[employee_id] = {
            "employee_id": employee_id,
            "employment_status": status,
            "target_role_id": ROLE,
            "department_code": "ENG",
        }
        for skill_id, level in (levels or {}).items():
            self.assess(employee_id, skill_id, level, assessed_on)
        return self.employees[employee_id]

    def assess(self, employee_id, skill_id, level, on):
        n = len(self.tables["proficiency_assessment"]) + 1
        self.tables["proficiency_assessment"].append(
            {
                "assessment_id": ids.assessment_id(n),
                "employee_id": employee_id,
                "skill_id": skill_id,
                "assessed_on": on,
                "proficiency_level": level,
                "assessment_score": 0,
            }
        )

    def planner(self, planning_date=PLANNING, allowance=60_000):
        catalog = snapshot.build_catalog(self.tables)
        settings = recommend.Settings(planning_date, PERIOD[0], PERIOD[1], allowance=allowance)
        planner = recommend.Planner(catalog, settings)
        snap = snapshot.build_snapshot(self.tables, catalog, planning_date, *PERIOD)
        ledger = schedule.SeatLedger(snapshot.free_seats(catalog, snap))
        return planner, snap, ledger

    def plan(self, employee_id=EMP, **kwargs):
        planner, snap, ledger = self.planner(**kwargs)
        return planner.recommend(self.employees[employee_id], snap, ledger)


def path_of(rows):
    return [r for r in rows if r["decision"] == "RECOMMENDED"]


def status_of(gap_rows, skill_id):
    return next(g["plan_status"] for g in gap_rows if g["skill_id"] == skill_id)
