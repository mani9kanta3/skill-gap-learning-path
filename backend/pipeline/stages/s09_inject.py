"""
s09: the five labelled edge cases (ARCHITECTURE.md 6).

Ground rules:
- each injected case breaks exactly one rule, so candidates are filtered
  until everything else about the row is valid;
- no record is used by two injectors;
- every foreign key stays valid;
- labels go only into the ground truth list, never into an input table.

Each injector has its own random stream (stage 9, stream n), so changing
one never shifts another. If any candidate pool is smaller than the
count wanted, the run stops with a message, rather than writing fewer
labelled cases than the README promises.
"""

from collections import defaultdict
from datetime import date

from .. import config, ids, rng
from ..rules import schedule
from . import s06_plan
from .common import days, random_date

STREAM = {name: i for i, name in enumerate(config.EDGE_CASE_TYPES)}
FAR_FUTURE = date(2099, 12, 31)


class NotEnoughCandidates(RuntimeError):
    pass


def _need(found, wanted, issue_type):
    if found < wanted:
        raise NotEnoughCandidates(f"{issue_type}: found {found} candidates, need {wanted}.")


def run(tables, plan, simulation):
    count = plan.scale.edge_cases_per_type
    truth = []
    used_enrollments = set()
    used_employees = set()

    # Order matters only for disjointness; each has its own random stream.
    truth += _budget_exceeded(tables, simulation, count, used_enrollments)
    truth += _recommendations(tables, "PREREQUISITE_VIOLATION", count, used_employees)
    truth += _recommendations(tables, "COURSE_UNAVAILABLE", count, used_employees)
    truth += _gap_not_reassessed(tables, simulation, count, used_enrollments)
    truth += _duplicate_completion(tables, simulation, count, used_enrollments)

    order = {name: i for i, name in enumerate(config.EDGE_CASE_TYPES)}
    truth.sort(key=lambda t: (order[t["issue_type"]], t["record_id"]))
    counter = ids.IdCounter(ids.ground_truth_id)
    for row in truth:
        row["case_id"] = counter.next()
    tables["ground_truth"] = [{"case_id": row.pop("case_id"), **row} for row in truth]

    # The simulation appended rows to its own lists; publish them again.
    tables["enrollment"] = simulation.enrollments
    tables["enrollment_event"] = simulation.events
    tables["completion"] = simulation.completions
    return tables


def _truth(issue_type, entity, record_id, employee_id, related, rule, expected, description):
    return {
        "issue_type": issue_type,
        "entity": entity,
        "record_id": record_id,
        "employee_id": employee_id,
        "related_ids": ";".join(related),
        "rule_code": rule,
        "expected_decision": expected,
        "description": description,
    }


# ---------------------------------------------------------------------------
# BUDGET_EXCEEDED: late requests approved over the department limit.
# ---------------------------------------------------------------------------


def _budget_exceeded(tables, simulation, count, used_enrollments):
    issue = "BUDGET_EXCEEDED"
    random = rng.stage_rng(rng.INJECT, STREAM[issue])
    catalog = simulation.catalog
    enrolled = {(e["employee_id"], e["course_id"]) for e in simulation.enrollments}
    last_decision = max(
        e["event_on"] for e in simulation.events if e["to_status"] in ("APPROVED", "REJECTED")
    )
    request_from = last_decision + days(1)
    request_to = request_from + days(config.BUDGET_INJECTION_WINDOW_DAYS - 1)
    earliest_start = request_from + days(config.MIN_REQUEST_LEAD_DAYS)

    remaining = {
        code: catalog.department_limit[code] - simulation.committed[code]
        for code in config.DEPARTMENT_CODES
    }

    by_department = defaultdict(list)
    for employee_id in sorted(simulation.paths):
        path = simulation.paths[employee_id]
        department = simulation.employees[employee_id]["department_code"]
        earlier = set()
        for rec in path:
            course = rec["course_id"]
            needed = [p for p in catalog.prerequisites.get(course, ()) if p in earlier]
            earlier.add(course)
            offering = catalog.offerings[rec["planned_offering_id"]]
            if (
                (employee_id, course) not in enrolled
                and rec["planned_start_date"] >= earliest_start
                and all(p in simulation.passed[employee_id] for p in needed)
                and simulation.seats[offering["offering_id"]] < offering["capacity"]
                # Over the limit no matter which injected approval lands first.
                and catalog.courses[course]["cost_amount"] > remaining[department]
            ):
                by_department[department].append(rec)

    for department in by_department:
        order = random.permutation(len(by_department[department]))
        by_department[department] = [by_department[department][i] for i in order]

    chosen = []
    departments = sorted(by_department, key=lambda d: (remaining[d], d))
    taken_seats = defaultdict(int)
    while len(chosen) < count and any(by_department[d] for d in departments):
        for department in departments:
            if len(chosen) == count:
                break
            while by_department[department]:
                rec = by_department[department].pop(0)
                offering = catalog.offerings[rec["planned_offering_id"]]
                # Each employee at most once, and never past an offering's capacity.
                if any(r["employee_id"] == rec["employee_id"] for r in chosen):
                    continue
                if simulation.seats[offering["offering_id"]] + taken_seats[offering["offering_id"]] >= offering["capacity"]:
                    continue
                taken_seats[offering["offering_id"]] += 1
                chosen.append(rec)
                break
    _need(len(chosen), count, issue)

    simulation.random = random
    for rec in chosen:
        latest = min(request_to, rec["planned_start_date"] - days(config.MIN_REQUEST_LEAD_DAYS))
        simulation.inject_request(rec, random_date(random, request_from, latest))
    simulation.run_queue()

    truth = []
    for rec in chosen:
        enrollment_id = ids.enrollment_id(rec["employee_id"], rec["course_id"])
        used_enrollments.add(enrollment_id)
        department = simulation.employees[rec["employee_id"]]["department_code"]
        cost = catalog.courses[rec["course_id"]]["cost_amount"]
        truth.append(
            _truth(
                issue,
                "enrollment",
                enrollment_id,
                rec["employee_id"],
                [ids.budget_id(department), rec["planned_offering_id"]],
                "BR-11",
                "REJECTED:BUDGET_EXHAUSTED",
                f"Approved for {cost:,.0f} when {department} had {remaining[department]:,.0f} "
                "left after every normal approval.",
            )
        )
    return truth


# ---------------------------------------------------------------------------
# PREREQUISITE_VIOLATION and COURSE_UNAVAILABLE: extra RECOMMENDED rows.
# ---------------------------------------------------------------------------


def _recommendations(tables, issue, count, used_employees):
    random = rng.stage_rng(rng.INJECT, STREAM[issue])
    planner, snap, _ = s06_plan.january_planner(tables)
    catalog = planner.catalog

    rows_by_employee = defaultdict(list)
    for row in tables["recommendation"]:
        rows_by_employee[row["employee_id"]].append(row)

    # Seats left after every plan (and earlier injections) booked theirs.
    planned = defaultdict(int)
    for row in tables["recommendation"]:
        if row["decision"] == "RECOMMENDED":
            planned[row["planned_offering_id"]] += 1
    ledger = schedule.SeatLedger(
        {o: offering["capacity"] - planned[o] for o, offering in catalog.offerings.items()}
    )

    employees = sorted(
        e["employee_id"] for e in tables["employee"] if e["employment_status"] == "ACTIVE"
    )
    employees = [employees[i] for i in random.permutation(len(employees))]
    by_id = {e["employee_id"]: e for e in tables["employee"]}

    truth = []
    for employee_id in employees:
        if len(truth) == count:
            break
        if employee_id in used_employees:
            continue
        rows = rows_by_employee[employee_id]
        path = sorted((r for r in rows if r["decision"] == "RECOMMENDED"), key=lambda r: r["path_sequence"])
        if len(path) >= config.MAX_PATH_COURSES:
            continue  # the injected row must keep the path at 4 or fewer

        employee = by_id[employee_id]
        rowed = {r["course_id"] for r in rows}
        in_path = {r["course_id"] for r in path}
        path_cost = sum(r["estimated_cost"] for r in path)
        slot = (
            schedule.next_slot(path[-1]["planned_end_date"])
            if path
            else schedule.first_slot(config.PLANNING_DATE)
        )

        made = None
        for target in planner.targets(employee):
            level = snap.levels.get((employee_id, target["skill_id"]), 0)
            if planner.plan_status(employee, target, level, rows) in ("PLANNED", "NO_GAP"):
                continue
            for course_id in planner.covering_courses(target["skill_id"], target["target_level"]):
                if course_id in rowed:
                    continue
                prerequisites = catalog.prerequisites.get(course_id, ())
                if issue == "PREREQUISITE_VIOLATION":
                    fits = course_id in planner.available and any(p not in in_path for p in prerequisites)
                    period_end = config.PERIOD_END
                else:
                    fits = course_id not in planner.available and not prerequisites
                    period_end = FAR_FUTURE  # its only offerings are next year
                if not fits:
                    continue
                cost = catalog.courses[course_id]["cost_amount"]
                if path_cost + cost > config.LEARNING_ALLOWANCE_PER_EMPLOYEE:
                    continue
                placement = schedule.place([course_id], slot, period_end, catalog.offerings_by_course, ledger)
                if placement is None:
                    continue
                offering = placement[0][1]
                ledger.book(offering["offering_id"])
                made = planner.row(
                    employee_id, course_id, target["skill_id"], "RECOMMENDED", "CLOSES_GAP", offering=offering
                )
                made["path_sequence"] = len(path) + 1
                made["cumulative_cost"] = path_cost + cost
                break
            if made:
                break

        if made is None:
            continue
        tables["recommendation"].append(made)
        used_employees.add(employee_id)
        if issue == "PREREQUISITE_VIOLATION":
            missing = sorted(p for p in catalog.prerequisites[made["course_id"]] if p not in in_path)
            truth.append(
                _truth(
                    issue,
                    "recommendation",
                    made["recommendation_id"],
                    employee_id,
                    [made["course_id"]] + missing,
                    "BR-05",
                    "NOT_RECOMMENDED:PREREQUISITE_NOT_PLANNED",
                    f"Recommends {made['course_id']} without its prerequisite {', '.join(missing)} "
                    "being passed or planned earlier in the path.",
                )
            )
        else:
            truth.append(
                _truth(
                    issue,
                    "recommendation",
                    made["recommendation_id"],
                    employee_id,
                    [made["course_id"], made["planned_offering_id"]],
                    "BR-04",
                    "NOT_RECOMMENDED:COURSE_UNAVAILABLE",
                    f"Recommends {made['course_id']}, which has no offering starting in the "
                    f"planning period; the planned run starts {made['planned_start_date']}.",
                )
            )

    _need(len(truth), count, issue)
    return truth


# ---------------------------------------------------------------------------
# GAP_NOT_REASSESSED: a due reassessment that never happened.
# ---------------------------------------------------------------------------


def _gap_not_reassessed(tables, simulation, count, used_enrollments):
    issue = "GAP_NOT_REASSESSED"
    random = rng.stage_rng(rng.INJECT, STREAM[issue])
    catalog = simulation.catalog
    due_by = config.AS_OF_DATE - days(config.REASSESSMENT_DELAY_DAYS[1])

    targets = {}
    for row in tables["role_skill_target"]:
        targets[(row["role_id"], row["skill_id"])] = row["target_level"]

    post = {a["completion_id"]: a for a in tables["proficiency_assessment"] if a["assessment_type"] == "POST_COURSE"}
    enrollment_by_id = {e["enrollment_id"]: e for e in simulation.enrollments}
    state = simulation.state

    completions_by_employee = defaultdict(list)
    for completion in simulation.completions:
        enrollment = enrollment_by_id[completion["enrollment_id"]]
        completions_by_employee[enrollment["employee_id"]].append((completion, enrollment))

    candidates = []
    for completion in simulation.completions:
        enrollment = enrollment_by_id[completion["enrollment_id"]]
        rec = state[enrollment["enrollment_id"]]["rec"]
        if (
            enrollment["enrollment_id"] in used_enrollments
            or rec["reason_code"] != "CLOSES_GAP"
            or completion["completed_on"] > due_by
            or completion["completion_id"] not in post
        ):
            continue
        employee_id, skill_id = enrollment["employee_id"], rec["target_skill_id"]
        # No later completion of this employee may touch the same skill, so
        # no later score was built on the assessment we remove.
        later = any(
            other["completed_on"] > completion["completed_on"]
            and skill_id in catalog.course_skills[other_enrollment["course_id"]]
            for other, other_enrollment in completions_by_employee[employee_id]
        )
        if later:
            continue
        # Without the reassessment, the gap must still be open.
        before = simulation.level_on(employee_id, skill_id, completion["completed_on"])
        target = targets[(simulation.employees[employee_id]["target_role_id"], skill_id)]
        if before[1] >= target:
            continue
        candidates.append((completion, enrollment, skill_id))

    _need(len(candidates), count, issue)
    picks = sorted(random.choice(len(candidates), size=count, replace=False).tolist())

    removed = set()
    truth = []
    for index in picks:
        completion, enrollment, skill_id = candidates[index]
        removed.add(completion["completion_id"])
        used_enrollments.add(enrollment["enrollment_id"])
        truth.append(
            _truth(
                issue,
                "completion",
                completion["completion_id"],
                enrollment["employee_id"],
                [enrollment["enrollment_id"], skill_id],
                "BR-17",
                "POST_COURSE_ASSESSMENT_DUE",
                f"Completed {completion['completed_on']} with result {completion['result']}; no "
                f"post-course assessment of {skill_id}, so the gap is still open and unchecked.",
            )
        )

    # Dropped before assessment IDs exist (s10), so no hole in the numbering.
    tables["proficiency_assessment"] = [
        a for a in tables["proficiency_assessment"] if a["completion_id"] not in removed
    ]
    return truth


# ---------------------------------------------------------------------------
# DUPLICATE_COMPLETION: the same completion counted twice.
# ---------------------------------------------------------------------------


def _duplicate_completion(tables, simulation, count, used_enrollments):
    issue = "DUPLICATE_COMPLETION"
    random = rng.stage_rng(rng.INJECT, STREAM[issue])
    enrollment_by_id = {e["enrollment_id"]: e for e in simulation.enrollments}
    candidates = [c for c in simulation.completions if c["enrollment_id"] not in used_enrollments]
    _need(len(candidates), count, issue)
    picks = sorted(random.choice(len(candidates), size=count, replace=False).tolist())

    truth = []
    for index in picks:
        original = candidates[index]
        # Exactly the same date and values: only "one completion per
        # enrollment" (BR-13) is broken, not the date rule.
        copy = dict(original, completion_id=simulation.completion_ids.next())
        simulation.completions.append(copy)
        used_enrollments.add(original["enrollment_id"])
        truth.append(
            _truth(
                issue,
                "completion",
                copy["completion_id"],
                enrollment_by_id[original["enrollment_id"]]["employee_id"],
                [original["completion_id"], original["enrollment_id"]],
                "BR-13",
                "COUNT_ONCE",
                f"Second completion for {original['enrollment_id']}; duplicates {original['completion_id']}.",
            )
        )
    return truth
