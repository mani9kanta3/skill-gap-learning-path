"""
Indexes over the loaded tables, built once and shared by the validator,
the detector and the evaluator. Read-only: nothing here changes a row.
"""

from collections import defaultdict
from functools import cached_property

from .. import config
from ..rules import availability


class Context:
    def __init__(self, tables):
        self.t = tables

    def by(self, table, key):
        return {row[key]: row for row in self.t[table]}

    @cached_property
    def employees(self):
        return self.by("employee", "employee_id")

    @cached_property
    def roles(self):
        return self.by("job_role", "role_id")

    @cached_property
    def courses(self):
        return self.by("course", "course_id")

    @cached_property
    def offerings(self):
        return self.by("course_offering", "offering_id")

    @cached_property
    def enrollments(self):
        return self.by("enrollment", "enrollment_id")

    @cached_property
    def budgets(self):
        return self.by("budget", "budget_id")

    @cached_property
    def recommendations(self):
        return self.by("recommendation", "recommendation_id")

    @cached_property
    def offerings_by_course(self):
        result = defaultdict(list)
        for row in self.t["course_offering"]:
            result[row["course_id"]].append(row)
        return result

    @cached_property
    def prerequisites(self):
        result = defaultdict(list)
        for row in self.t["course_prerequisite"]:
            result[row["course_id"]].append(row["prerequisite_course_id"])
        return result

    @cached_property
    def course_skills(self):
        result = defaultdict(dict)
        for row in self.t["course_skill"]:
            result[row["course_id"]][row["skill_id"]] = row
        return result

    @cached_property
    def available(self):
        """BR-04 for the planning period."""
        return {
            course_id
            for course_id, course in self.courses.items()
            if availability.is_available(
                course["course_status"],
                [o["start_date"] for o in self.offerings_by_course.get(course_id, ())],
                config.PERIOD_START,
                config.PERIOD_END,
            )
        }

    @cached_property
    def events_by_enrollment(self):
        result = defaultdict(list)
        for row in self.t["enrollment_event"]:
            result[row["enrollment_id"]].append(row)
        for history in result.values():
            history.sort(key=lambda e: e["event_seq"])
        return result

    @cached_property
    def path_by_employee(self):
        """RECOMMENDED rows per employee, in path order."""
        result = defaultdict(list)
        for row in self.t["recommendation"]:
            if row["decision"] == "RECOMMENDED":
                result[row["employee_id"]].append(row)
        for path in result.values():
            path.sort(key=lambda r: (r["path_sequence"] or 0, r["course_id"]))
        return result

    @cached_property
    def completions_by_enrollment(self):
        result = defaultdict(list)
        for row in self.t["completion"]:
            result[row["enrollment_id"]].append(row)
        for rows in result.values():
            rows.sort(key=lambda c: c["completion_id"])
        return result

    @cached_property
    def first_completions(self):
        """The first completion of each enrollment (lowest completion_id)."""
        return [rows[0] for rows in self.completions_by_enrollment.values()]

    @cached_property
    def post_course_by_completion(self):
        result = defaultdict(list)
        for row in self.t["proficiency_assessment"]:
            if row["assessment_type"] == "POST_COURSE":
                result[row["completion_id"]].append(row)
        return result

    @cached_property
    def approvals(self):
        """One dict per APPROVED event, ready for rules.budget.over_limit_approvals."""
        result = []
        for event in self.t["enrollment_event"]:
            if event["to_status"] != "APPROVED":
                continue
            enrollment = self.enrollments[event["enrollment_id"]]
            result.append(
                {
                    "department_code": self.budgets[enrollment["budget_id"]]["department_code"],
                    "event_on": event["event_on"],
                    "event_id": event["event_id"],
                    "enrollment_id": enrollment["enrollment_id"],
                    "cost": enrollment["cost_amount"],
                }
            )
        return result

    @cached_property
    def passed_by_employee(self):
        """employee -> {course_id: earliest completed_on with PASSED}."""
        result = defaultdict(dict)
        for row in self.t["completion"]:
            if row["result"] != "PASSED":
                continue
            enrollment = self.enrollments[row["enrollment_id"]]
            known = result[enrollment["employee_id"]].get(enrollment["course_id"])
            if known is None or row["completed_on"] < known:
                result[enrollment["employee_id"]][enrollment["course_id"]] = row["completed_on"]
        return result
