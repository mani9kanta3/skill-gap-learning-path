"""
s10: assessment IDs, then every derived column from the final rows.

Derived values are never generated on their own. Everything here is
recomputed from source rows after injection, so totals, statuses and
gaps always reflect the data as it was finally written (step 6 of the
brief). The validator then recomputes them again independently.
"""

from collections import defaultdict

from .. import config, ids
from ..rules import gaps, lifecycle, schedule
from . import s06_plan


def run(tables, plan):
    _assessment_ids(tables)
    _courses_and_offerings(tables)
    _recommendations(tables)
    _enrollments(tables)
    _budgets(tables)
    _employee_skills(tables)
    _skill_gaps(tables)
    return tables


def _assessment_ids(tables):
    """Numbered once, here, after injection (ARCHITECTURE.md 3.2)."""
    rows = sorted(
        tables["proficiency_assessment"],
        key=lambda a: (
            a["assessed_on"],
            a["employee_id"],
            a["skill_id"],
            a["assessment_type"],
            a["completion_id"] or "",
        ),
    )
    counter = ids.IdCounter(ids.assessment_id)
    for row in rows:
        row["assessment_id"] = counter.next()
    tables["proficiency_assessment"] = rows


def _courses_and_offerings(tables):
    courses = {c["course_id"]: c for c in tables["course"]}
    for course in tables["course"]:
        course["cost_amount"] = course["duration_hours"] * config.HOURLY_RATE[course["delivery_mode"]]

    planned = defaultdict(int)
    for row in tables["recommendation"]:
        if row["decision"] == "RECOMMENDED":
            planned[row["planned_offering_id"]] += 1
    approved = defaultdict(int)
    enrollment_offering = {e["enrollment_id"]: e["offering_id"] for e in tables["enrollment"]}
    for event in tables["enrollment_event"]:
        if event["to_status"] == "APPROVED":
            approved[enrollment_offering[event["enrollment_id"]]] += 1

    for offering in tables["course_offering"]:
        course = courses[offering["course_id"]]
        offering["end_date"] = schedule.end_date(offering["start_date"], course["duration_hours"])
        offering["seats_planned"] = planned[offering["offering_id"]]
        offering["seats_approved"] = approved[offering["offering_id"]]


def _recommendations(tables):
    courses = {c["course_id"]: c for c in tables["course"]}
    offerings = {o["offering_id"]: o for o in tables["course_offering"]}
    by_employee = defaultdict(list)
    for row in tables["recommendation"]:
        row["estimated_cost"] = courses[row["course_id"]]["cost_amount"]
        if row["decision"] == "RECOMMENDED":
            offering = offerings[row["planned_offering_id"]]
            row["planned_start_date"] = offering["start_date"]
            row["planned_end_date"] = offering["end_date"]
            by_employee[row["employee_id"]].append(row)
        else:
            row["planned_start_date"] = row["planned_end_date"] = row["cumulative_cost"] = None
    for path in by_employee.values():
        running = 0
        for row in sorted(path, key=lambda r: r["path_sequence"]):
            running += row["estimated_cost"]
            row["cumulative_cost"] = running
    tables["recommendation"].sort(key=lambda r: r["recommendation_id"])


def _enrollments(tables):
    courses = {c["course_id"]: c for c in tables["course"]}
    events = defaultdict(list)
    for event in tables["enrollment_event"]:
        events[event["enrollment_id"]].append(event)
    for enrollment in tables["enrollment"]:
        history = events[enrollment["enrollment_id"]]
        enrollment["cost_amount"] = courses[enrollment["course_id"]]["cost_amount"]
        enrollment["current_status"] = lifecycle.current_status(history)
        enrollment["last_event_on"] = max(history, key=lambda e: e["event_seq"])["event_on"]


def _budgets(tables):
    employees = {e["employee_id"]: e for e in tables["employee"]}
    planned = defaultdict(float)
    for row in tables["recommendation"]:
        if row["decision"] == "RECOMMENDED":
            planned[employees[row["employee_id"]]["department_code"]] += row["estimated_cost"]

    approved = {e["enrollment_id"] for e in tables["enrollment_event"] if e["to_status"] == "APPROVED"}
    committed = defaultdict(float)
    budget_department = {b["budget_id"]: b["department_code"] for b in tables["budget"]}
    for enrollment in tables["enrollment"]:
        if enrollment["enrollment_id"] in approved:
            committed[budget_department[enrollment["budget_id"]]] += enrollment["cost_amount"]

    for row in tables["budget"]:
        code = row["department_code"]
        row["planned_amount"] = planned[code]
        row["committed_amount"] = committed[code]
        row["remaining_amount"] = row["limit_amount"] - committed[code]
        row["utilization_pct"] = round(100 * committed[code] / row["limit_amount"], 2)
        row["budget_status"] = "EXCEEDED" if committed[code] > row["limit_amount"] else "WITHIN_LIMIT"


def _latest_by_pair(assessments, on_or_before):
    latest = {}
    for row in assessments:
        if row["assessed_on"] > on_or_before:
            continue
        key = (row["employee_id"], row["skill_id"])
        rank = (row["assessed_on"], row["assessment_id"])
        if key not in latest or rank > (latest[key]["assessed_on"], latest[key]["assessment_id"]):
            latest[key] = row
    return latest


def _employee_skills(tables):
    latest = _latest_by_pair(tables["proficiency_assessment"], config.AS_OF_DATE)
    for row in tables["employee_skill"]:
        last = latest[(row["employee_id"], row["skill_id"])]
        row["current_level"] = last["proficiency_level"]
        row["last_assessment_id"] = last["assessment_id"]
        row["last_assessed_on"] = last["assessed_on"]


def _skill_gaps(tables):
    """
    One row per target-role skill. plan_status comes from the same
    function the engine uses, applied to the final recommendation rows.
    """
    planner, snap, _ = s06_plan.january_planner(tables)
    current = {(r["employee_id"], r["skill_id"]): r["current_level"] for r in tables["employee_skill"]}
    rows_by_employee = defaultdict(list)
    for row in tables["recommendation"]:
        rows_by_employee[row["employee_id"]].append(row)

    result = []
    for employee in sorted(tables["employee"], key=lambda e: e["employee_id"]):
        for gap_row in planner.gap_rows(employee, snap, rows_by_employee[employee["employee_id"]]):
            level = current[(employee["employee_id"], gap_row["skill_id"])]
            current_gap = gaps.gap(gap_row["target_level"], level)
            result.append(
                {
                    "employee_id": employee["employee_id"],
                    "skill_id": gap_row["skill_id"],
                    "target_role_id": employee["target_role_id"],
                    "target_level": gap_row["target_level"],
                    "planning_level": gap_row["planning_level"],
                    "planning_gap": gap_row["planning_gap"],
                    "current_level": level,
                    "current_gap": current_gap,
                    "plan_status": gap_row["plan_status"],
                    "gap_status": gaps.gap_status(gap_row["planning_gap"], current_gap),
                }
            )
    tables["skill_gap"] = result
