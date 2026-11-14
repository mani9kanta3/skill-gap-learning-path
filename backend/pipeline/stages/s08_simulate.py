"""
s08: one discrete-event simulation of 2026 (ARCHITECTURE.md 5.3).

Requests, decisions, starts, withdrawals, completions with their results,
and post-course reassessments all come out of one priority queue, in date
order. So when a later step is requested, the pass/fail result of its
prerequisite already exists. The review found that keeping completions in
a later stage broke exactly that.

Event and completion IDs are handed out at the moment each row is written,
so their numbers follow the processing order. The budget order used by
events, (event_on, event_id), is therefore exactly the order the
simulation decided in.

s09 reuses the same Simulation object to push its injected requests
through the same code, so an injected row is built the same way as a
normal one apart from the one rule it breaks.
"""

import heapq
from collections import defaultdict
from .. import config, ids, rng
from ..rules import budget, lifecycle, outcomes, snapshot
from .common import days, random_date, uniform_int

# Same-day order (5.3): finish things before starting new ones.
COMPLETE, WITHDRAW, START, DECIDE, REQUEST = range(5)


class TargetNotReached(RuntimeError):
    pass


class Simulation:
    def __init__(self, tables, plan, random):
        self.tables = tables
        self.plan = plan
        self.random = random
        self.catalog = snapshot.build_catalog(tables)
        self.employees = {e["employee_id"]: e for e in tables["employee"]}
        self.primary = {
            row["course_id"]: row["skill_id"]
            for row in tables["course_skill"]
            if row["skill_role"] == "PRIMARY"
        }
        self.budget_by_department = {b["department_code"]: b["budget_id"] for b in tables["budget"]}

        self.paths = defaultdict(list)
        for row in tables["recommendation"]:
            if row["decision"] == "RECOMMENDED":
                self.paths[row["employee_id"]].append(row)
        for path in self.paths.values():
            path.sort(key=lambda r: r["path_sequence"])

        # Score history per (employee, skill): [(date, score, level)], for
        # "level as of a date" lookups.
        self.history = defaultdict(list)
        for row in tables["proficiency_assessment"]:
            self.history[(row["employee_id"], row["skill_id"])].append(
                (row["assessed_on"], row["assessment_score"], row["proficiency_level"])
            )
        for entries in self.history.values():
            entries.sort()

        self.enrollments = []
        self.events = []
        self.completions = []
        self.state = {}  # enrollment_id -> working state
        self.event_ids = ids.IdCounter(ids.event_id)
        self.completion_ids = ids.IdCounter(ids.completion_id)
        self.seats = defaultdict(int)
        self.committed = defaultdict(float)
        self.passed = defaultdict(set)
        self.requests = 0
        self.target = plan.baseline_enrollments
        self.queue = []
        self.pushed = 0

    # ---------- queue ----------

    def push(self, on, kind, employee_id, key, payload):
        if on > config.AS_OF_DATE:
            return  # nothing is dated after the snapshot
        self.pushed += 1
        heapq.heappush(self.queue, (on, kind, employee_id, key, self.pushed, payload))

    def run_queue(self):
        handlers = {
            REQUEST: self.on_request,
            DECIDE: self.on_decide,
            START: self.on_start,
            WITHDRAW: self.on_withdraw,
            COMPLETE: self.on_complete,
        }
        while self.queue:
            on, kind, _, _, _, payload = heapq.heappop(self.queue)
            handlers[kind](on, payload)

    # ---------- lookups ----------

    def level_on(self, employee_id, skill_id, on):
        """(score, level) of the latest assessment on or before `on`, or None."""
        latest = None
        for assessed_on, score, level in self.history.get((employee_id, skill_id), ()):
            if assessed_on <= on:
                latest = (score, level)
            else:
                break
        return latest

    def primary_skill(self, course_id):
        """(PRIMARY skill_id, its target_level) of a course."""
        primary = self.primary[course_id]
        return primary, self.catalog.course_skills[course_id][primary]

    # ---------- the employee's path ----------

    def start(self):
        for employee_id in sorted(self.paths):
            self.schedule_from(employee_id, 0, None)
        self.run_queue()
        if self.requests < self.target:
            raise TargetNotReached(
                f"The simulation made {self.requests} enrollments but needs {self.target} "
                f"({self.target - self.requests} missing). Adjust the calibration knobs in config.py."
            )

    def schedule_from(self, employee_id, index, lower_bound):
        """Request the next step from `index` on, after `lower_bound` (5.3 step 2)."""
        path = self.paths[employee_id]
        while index < len(path):
            step = path[index]
            earlier = {r["course_id"] for r in path[:index]}
            needed = [p for p in self.catalog.prerequisites.get(step["course_id"], ()) if p in earlier]
            if any(p not in self.passed[employee_id] for p in needed):
                index += 1  # BR-05: an in-path prerequisite was not PASSED
                continue
            # Funded steps are usually requested. Some employees also ask for
            # a step the budget did not fund; HR will reject it (BR-11).
            chance = (
                config.REQUEST_PROBABILITY
                if step["funding_status"] == "FUNDED"
                else config.UNFUNDED_REQUEST_PROBABILITY
            )
            if self.random.random() >= chance:
                index += 1  # the employee chose not to take this one
                continue
            lead = uniform_int(self.random, *config.REQUEST_LEAD_DAYS)
            requested_on = step["planned_start_date"] - days(lead)
            if lower_bound is not None:
                requested_on = max(requested_on, lower_bound + days(1))
            requested_on = max(requested_on, config.PLANNING_DATE + days(1))
            if requested_on > config.REQUEST_HORIZON:
                return  # later steps are later still
            self.push(requested_on, REQUEST, employee_id, step["path_sequence"], (employee_id, index, False))
            return

    # ---------- handlers ----------

    def write_event(self, state, to_status, on, reason=None):
        state["event_seq"] += 1
        self.events.append(
            {
                "event_id": self.event_ids.next(),
                "enrollment_id": state["enrollment"]["enrollment_id"],
                "event_seq": state["event_seq"],
                "from_status": state["status"],
                "to_status": to_status,
                "event_on": on,
                "actor": lifecycle.actor_for(to_status, reason),
                "reason_code": reason,
            }
        )
        state["status"] = to_status

    def on_request(self, on, payload):
        employee_id, index, injected = payload
        if not injected:
            if self.requests >= self.target:
                return
            self.requests += 1
        rec = self.paths[employee_id][index] if not injected else index
        employee = self.employees[employee_id]
        enrollment = {
            "enrollment_id": ids.enrollment_id(employee_id, rec["course_id"]),
            "employee_id": employee_id,
            "course_id": rec["course_id"],
            "offering_id": rec["planned_offering_id"],
            "recommendation_id": rec["recommendation_id"],
            "budget_id": self.budget_by_department[employee["department_code"]],
            "requested_on": on,
            "cost_amount": self.catalog.courses[rec["course_id"]]["cost_amount"],
            "current_status": None,
            "last_event_on": None,
        }
        self.enrollments.append(enrollment)
        state = {
            "enrollment": enrollment,
            "rec": rec,
            "index": None if injected else index,
            "injected": injected,
            "offering": self.catalog.offerings[rec["planned_offering_id"]],
            "department": employee["department_code"],
            "event_seq": 0,
            "status": None,
            "withdraw_on": None,
        }
        self.state[enrollment["enrollment_id"]] = state
        self.write_event(state, "REQUESTED", on)
        decide_on = on + days(uniform_int(self.random, *config.DECISION_DELAY_DAYS))
        self.push(decide_on, DECIDE, employee_id, rec["path_sequence"], state)

    def on_decide(self, on, state):
        offering = state["offering"]
        cost = state["enrollment"]["cost_amount"]
        department = state["department"]
        limit = self.catalog.department_limit[department]

        if self.seats[offering["offering_id"]] >= offering["capacity"]:  # BR-10
            self.write_event(state, "REJECTED", on, "NO_SEATS")
            self.after_terminal(state, on)
            return
        # BR-11: only a FUNDED step may be approved. Injected BUDGET_EXCEEDED
        # cases are approved regardless; that is the one rule they break.
        funding = state["rec"]["funding_status"]
        if not state["injected"] and not budget.can_approve(funding, self.committed[department], cost, limit):
            self.write_event(state, "REJECTED", on, "BUDGET_EXHAUSTED")
            self.after_terminal(state, on)
            return

        self.write_event(state, "APPROVED", on)
        self.seats[offering["offering_id"]] += 1
        self.committed[department] += cost

        if not state["injected"] and self.random.random() < config.WITHDRAW_PROBABILITY:
            state["withdraw_on"] = random_date(self.random, on + days(1), offering["end_date"] - days(1))

        key = state["rec"]["path_sequence"]
        employee_id = state["enrollment"]["employee_id"]
        if state["withdraw_on"] is not None and state["withdraw_on"] < offering["start_date"]:
            self.push(state["withdraw_on"], WITHDRAW, employee_id, key, state)
        else:
            self.push(offering["start_date"], START, employee_id, key, state)

    def on_start(self, on, state):
        self.write_event(state, "IN_PROGRESS", on)
        key = state["rec"]["path_sequence"]
        employee_id = state["enrollment"]["employee_id"]
        if state["withdraw_on"] is not None:
            self.push(state["withdraw_on"], WITHDRAW, employee_id, key, state)
        else:
            self.push(state["offering"]["end_date"], COMPLETE, employee_id, key, state)

    def on_withdraw(self, on, state):
        reason = "PERSONAL" if self.random.random() < 0.5 else "WORKLOAD"
        self.write_event(state, "WITHDRAWN", on, reason)
        self.after_terminal(state, on)

    def on_complete(self, on, state):
        self.write_event(state, "COMPLETED", on)
        enrollment = state["enrollment"]
        employee_id, course_id = enrollment["employee_id"], enrollment["course_id"]

        # Completion result (5.3 step 6, BR-14).
        primary, primary_target = self.primary_skill(course_id)
        pre = self.level_on(employee_id, primary, on)
        pre_level = pre[1] if pre else 0
        mean = outcomes.final_score_mean(pre_level, primary_target)
        final_score = outcomes.clip(
            outcomes.round_half_up(self.random.normal(mean, config.FINAL_SCORE_SD)), 0, 100
        )
        attendance = round(100 * float(self.random.beta(*config.ATTENDANCE_BETA)), 1)
        result = outcomes.completion_result(attendance, final_score)
        completion = {
            "completion_id": self.completion_ids.next(),
            "enrollment_id": enrollment["enrollment_id"],
            "completed_on": on,
            "attendance_pct": attendance,
            "final_score": final_score,
            "result": result,
        }
        self.completions.append(completion)
        if result == "PASSED":
            self.passed[employee_id].add(course_id)

        # Reassessment (5.3 step 7, BR-15, BR-16, BR-17): CLOSES_GAP only.
        rec = state["rec"]
        if rec["reason_code"] == "CLOSES_GAP":
            assessed_on = on + days(uniform_int(self.random, *config.REASSESSMENT_DELAY_DAYS))
            noise = float(self.random.normal(0, config.POST_SCORE_NOISE_SD))
            if assessed_on <= config.AS_OF_DATE:
                skill_id = rec["target_skill_id"]
                pre_score = self.level_on(employee_id, skill_id, on)[0]
                score = outcomes.post_course_score(
                    pre_score,
                    final_score,
                    result,
                    noise,
                    self.catalog.course_skills[course_id][skill_id],
                )
                level = outcomes.band(score)
                self.tables["proficiency_assessment"].append(
                    {
                        "assessment_id": None,
                        "employee_id": employee_id,
                        "skill_id": skill_id,
                        "assessment_type": "POST_COURSE",
                        "assessed_on": assessed_on,
                        "assessment_score": score,
                        "proficiency_level": level,
                        "assessor_type": "SKILL_TEST",
                        "completion_id": completion["completion_id"],
                    }
                )
                entries = self.history[(employee_id, skill_id)]
                entries.append((assessed_on, score, level))
                entries.sort()

        self.after_terminal(state, on)

    def after_terminal(self, state, on):
        if state["injected"]:
            return
        self.schedule_from(state["enrollment"]["employee_id"], state["index"] + 1, on)

    # ---------- used by s09 ----------

    def inject_request(self, rec, requested_on):
        """Push one injected request through the normal handlers."""
        self.push(requested_on, REQUEST, rec["employee_id"], rec["path_sequence"] or 0, (rec["employee_id"], rec, True))


def run(tables, plan):
    simulation = Simulation(tables, plan, rng.stage_rng(rng.SIMULATE))
    simulation.start()
    tables["enrollment"] = simulation.enrollments
    tables["enrollment_event"] = simulation.events
    tables["completion"] = simulation.completions
    return simulation

