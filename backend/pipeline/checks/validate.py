"""
The validator (ARCHITECTURE.md 7.1).

Every check returns the IDs that fail it, never just a count.

- STRUCTURAL checks must fail on nothing at all.
- RULE checks are matched to ground truth record by record: the set of
  (issue_type, record_id) they fail must equal the ground truth set for
  that type exactly. A count that happens to match is not enough.

With injection switched off the ground truth is empty, so every RULE
check must also fail on nothing: that is the clean-baseline proof.
"""

from collections import Counter, defaultdict
from datetime import timedelta

from .. import config, dictionary, ids
from ..rules import budget, gaps, lifecycle, outcomes, recommend, schedule, snapshot
from . import detect

SAMPLE = 10


class Validator:
    def __init__(self, ctx, ground_truth, plan):
        self.ctx = ctx
        self.t = ctx.t
        self.plan = plan
        self.results = []
        self.truth = defaultdict(set)
        for row in ground_truth:
            self.truth[row["issue_type"]].add(row["record_id"])

    # ---------- recording ----------

    def structural(self, check_id, table, failing, rule_code=None):
        failing = sorted(set(failing))
        self.results.append(
            {
                "check_id": check_id,
                "rule_code": rule_code,
                "table_name": table,
                "kind": "STRUCTURAL",
                "failing_count": len(failing),
                "expected_count": 0,
                "status": "PASS" if not failing else "FAIL",
                "failing_ids": failing,
                "unexpected_ids": failing,
                "missed_ids": [],
            }
        )

    def rule(self, check_id, table, failing, expected, rule_code):
        failing, expected = set(failing), set(expected)
        unexpected = sorted(failing - expected)
        missed = sorted(expected - failing)
        self.results.append(
            {
                "check_id": check_id,
                "rule_code": rule_code,
                "table_name": table,
                "kind": "RULE",
                "failing_count": len(failing),
                "expected_count": len(expected),
                "status": "PASS" if not unexpected and not missed else "FAIL",
                "failing_ids": sorted(failing),
                "unexpected_ids": unexpected,
                "missed_ids": missed,
            }
        )

    # ---------- run everything ----------

    def run(self):
        self.columns()
        self.foreign_keys()
        self.counts()
        self.reference_data()
        self.catalog()
        self.employees_and_skills()
        self.recommendations()
        self.enrollments_and_events()
        self.completions_and_assessments()
        self.derived()
        self.rule_checks()
        self.leakage()
        return self.results

    # ---------- column-level checks from the dictionary ----------

    @staticmethod
    def key_of(table, row):
        return "|".join(str(row[k]) for k in table.primary_key)

    def columns(self):
        for name in dictionary.EXPORTED_TABLES:
            table = dictionary.table(name)
            rows = self.t[name]
            keys = Counter(self.key_of(table, r) for r in rows)
            self.structural(f"primary_key.{name}", name, [k for k, n in keys.items() if n > 1])

            required, enums, ranges, formats = [], [], [], []
            for row in rows:
                key = self.key_of(table, row)
                for col in table.columns:
                    value = row[col.name]
                    if value is None:
                        if col.required:
                            required.append(f"{key}:{col.name}")
                        continue
                    if col.enum is not None and value not in col.enum:
                        enums.append(f"{key}:{col.name}={value}")
                    if col.minimum is not None and value < col.minimum:
                        ranges.append(f"{key}:{col.name}={value}")
                    if col.maximum is not None and value > col.maximum:
                        ranges.append(f"{key}:{col.name}={value}")
                    if col.pattern is not None and not ids.matches(col.pattern, value):
                        formats.append(f"{key}:{col.name}={value}")
            self.structural(f"required.{name}", name, required)
            self.structural(f"enums.{name}", name, enums)
            self.structural(f"ranges.{name}", name, ranges)
            self.structural(f"formats.{name}", name, formats)

            for group in table.unique:
                seen = Counter(tuple(r[c] for c in group) for r in rows)
                duplicates = ["|".join(map(str, k)) for k, n in seen.items() if n > 1]
                rule_code = "BR-18" if group == ("employee_id", "course_id") else None
                self.structural(f"unique.{name}.{'+'.join(group)}", name, duplicates, rule_code)

    def foreign_keys(self):
        for name in dictionary.EXPORTED_TABLES:
            table = dictionary.table(name)
            failing = []
            for col in table.columns:
                if not col.references:
                    continue
                target_table, _, target_column = col.references.partition(".")
                targets = {r[target_column] for r in self.t[target_table]}
                for row in self.t[name]:
                    value = row[col.name]
                    if value is not None and value not in targets:
                        failing.append(f"{self.key_of(table, row)}:{col.name}={value}")
            self.structural(f"foreign_keys.{name}", name, failing)

    def counts(self):
        scale = self.plan.scale
        expected = {
            "department": len(config.DEPARTMENTS),
            "job_role": len(config.DEPARTMENTS) * config.ROLES_PER_DEPARTMENT,
            "skill": scale.skills,
            "employee": scale.employees,
            "course": scale.courses,
            # 10,000 at full scale: the simulation's share plus the
            # injected budget cases (none when injection is off).
            "enrollment": self.plan.baseline_enrollments + len(self.truth["BUDGET_EXCEEDED"]),
            "budget": len(config.DEPARTMENTS),
        }
        failing = [f"{n}={len(self.t[n])}, expected {c}" for n, c in expected.items() if len(self.t[n]) != c]
        self.structural("row_counts", "*", failing)

    # ---------- reference data ----------

    def reference_data(self):
        roles = self.ctx.roles
        failing = []
        for role in roles.values():
            nxt = role["next_role_id"]
            if role["career_level"] == 5:
                if nxt is not None:
                    failing.append(role["role_id"])
            elif nxt is None or roles[nxt]["department_code"] != role["department_code"] or roles[nxt]["career_level"] != role["career_level"] + 1:
                failing.append(role["role_id"])
        self.structural("ladder.next_role", "job_role", failing)

        targets = defaultdict(dict)
        importance = defaultdict(Counter)
        for row in self.t["role_skill_target"]:
            targets[row["role_id"]][row["skill_id"]] = row["target_level"]
            importance[row["role_id"]][row["importance"]] += 1
        count_fail = [
            r["role_id"]
            for r in roles.values()
            if len(targets[r["role_id"]]) != config.LADDER_BASE_SKILLS + r["career_level"]
            or importance[r["role_id"]]["CORE"] != config.CORE_SKILL_COUNT
        ]
        self.structural("ladder.target_count", "role_skill_target", count_fail)

        down = []
        for role in roles.values():
            nxt = role["next_role_id"]
            if nxt is None:
                continue
            for skill_id, level in targets[role["role_id"]].items():
                if targets[nxt].get(skill_id, -1) < level:
                    down.append(f"{role['role_id']}->{nxt}:{skill_id}")
        self.structural("ladder.targets_never_go_down", "role_skill_target", down)

    # ---------- catalog ----------

    def catalog(self):
        ctx = self.ctx
        cost, duration, primary, category, targets = [], [], [], [], []
        skills = {s["skill_id"]: s for s in self.t["skill"]}
        for course in ctx.courses.values():
            cid = course["course_id"]
            if course["cost_amount"] != course["duration_hours"] * config.HOURLY_RATE[course["delivery_mode"]]:
                cost.append(cid)
            low, high = config.DURATION_RANGE[course["course_level"]]
            if course["duration_hours"] % config.HOURS_PER_WEEK or not low <= course["duration_hours"] <= high:
                duration.append(cid)
            rows = ctx.course_skills.get(cid, {})
            prim = [r for r in rows.values() if r["skill_role"] == "PRIMARY"]
            if len(prim) != 1:
                primary.append(cid)
                continue
            p = prim[0]
            if skills[p["skill_id"]]["skill_category"] != course["skill_category"]:
                category.append(cid)
            if p["target_level"] not in config.PRIMARY_TARGET_LEVELS[course["course_level"]]:
                targets.append(cid)
            for r in rows.values():
                if r["skill_role"] == "SECONDARY" and r["target_level"] != max(1, p["target_level"] - 1):
                    targets.append(f"{cid}:{r['skill_id']}")
        self.structural("course.cost_is_hours_x_rate", "course", cost)
        self.structural("course.duration_by_level", "course", duration)
        self.structural("course.one_primary_skill", "course_skill", primary)
        self.structural("course.category_is_primary_category", "course", category)
        self.structural("course.target_levels_by_level", "course_skill", targets)

        order = {"FOUNDATION": 0, "INTERMEDIATE": 1, "ADVANCED": 2}
        bad = []
        for row in self.t["course_prerequisite"]:
            a, b = ctx.courses[row["course_id"]], ctx.courses[row["prerequisite_course_id"]]
            if a["course_id"] == b["course_id"] or a["skill_category"] != b["skill_category"] or order[b["course_level"]] >= order[a["course_level"]]:
                bad.append(f"{a['course_id']}<-{b['course_id']}")
        self.structural("prerequisite.same_category_lower_level", "course_prerequisite", bad)

        offering_bad = []
        for o in self.t["course_offering"]:
            course = ctx.courses[o["course_id"]]
            if o["start_date"].weekday() != 0:
                offering_bad.append(f"{o['offering_id']}:not a Monday")
            if o["end_date"] != schedule.end_date(o["start_date"], course["duration_hours"]):
                offering_bad.append(f"{o['offering_id']}:end_date")
            if o["capacity"] != config.CAPACITY[course["delivery_mode"]]:
                offering_bad.append(f"{o['offering_id']}:capacity")
            if course["course_status"] != "ACTIVE":
                offering_bad.append(f"{o['offering_id']}:retired course")
        self.structural("offering.dates_and_capacity", "course_offering", offering_bad)

    # ---------- employees and baseline ----------

    def employees_and_skills(self):
        ctx = self.ctx
        roles = ctx.roles
        bad = []
        for e in ctx.employees.values():
            role = roles[e["role_id"]]
            if e["department_code"] != role["department_code"]:
                bad.append(f"{e['employee_id']}:department")
            if e["target_role_id"] not in (e["role_id"], role["next_role_id"]):
                bad.append(f"{e['employee_id']}:target_role")
            if not config.HIRE_DATE_FROM <= e["hire_date"] <= config.HIRE_DATE_TO:
                bad.append(f"{e['employee_id']}:hire_date")
            manager = e["manager_id"]
            if role["career_level"] == 5:
                if manager is not None:
                    bad.append(f"{e['employee_id']}:manager")
            else:
                m = ctx.employees.get(manager)
                if (
                    m is None
                    or m["employee_id"] == e["employee_id"]
                    or m["department_code"] != e["department_code"]
                    or roles[m["role_id"]]["career_level"] <= role["career_level"]
                ):
                    bad.append(f"{e['employee_id']}:manager")
        self.structural("employee.role_department_manager", "employee", bad)

        targets = defaultdict(set)
        for row in self.t["role_skill_target"]:
            targets[row["role_id"]].add(row["skill_id"])
        have = defaultdict(set)
        for row in self.t["employee_skill"]:
            have[row["employee_id"]].add(row["skill_id"])
        coverage = [
            e["employee_id"]
            for e in ctx.employees.values()
            if have[e["employee_id"]] != targets[e["role_id"]] | targets[e["target_role_id"]]
        ]
        self.structural("employee_skill.covers_current_and_target_role", "employee_skill", coverage)

        baseline = {}
        bad_baseline = []
        for a in self.t["proficiency_assessment"]:
            if a["assessment_type"] != "BASELINE":
                continue
            key = (a["employee_id"], a["skill_id"])
            if key in baseline:
                bad_baseline.append(f"{key}:twice")
            baseline[key] = a
            if not config.BASELINE_ASSESSMENT_FROM <= a["assessed_on"] <= config.BASELINE_ASSESSMENT_TO:
                bad_baseline.append(f"{a['assessment_id']}:date")
            if a["assessed_on"] <= ctx.employees[a["employee_id"]]["hire_date"]:
                bad_baseline.append(f"{a['assessment_id']}:before hire")
            if a["completion_id"] is not None:
                bad_baseline.append(f"{a['assessment_id']}:completion_id")
        for row in self.t["employee_skill"]:
            a = baseline.get((row["employee_id"], row["skill_id"]))
            if a is None or a["proficiency_level"] != row["baseline_level"]:
                bad_baseline.append(f"{row['employee_id']}|{row['skill_id']}:baseline_level")
        self.structural("baseline.one_per_skill_dated_q4_2025", "proficiency_assessment", bad_baseline)

    # ---------- recommendations ----------

    def recommendations(self):
        ctx = self.ctx
        shape = []
        for r in self.t["recommendation"]:
            rid = r["recommendation_id"]
            if ids.split_pair(rid) != (r["employee_id"], r["course_id"]):
                shape.append(f"{rid}:id does not match the pair")
            if (r["planning_date"], r["period_start"], r["period_end"]) != (config.PLANNING_DATE, config.PERIOD_START, config.PERIOD_END):
                shape.append(f"{rid}:planning date or period")
            if r["decision"] == "RECOMMENDED":
                if r["reason_code"] not in dictionary.RECOMMENDED_REASONS:
                    shape.append(f"{rid}:reason")
                if r["path_sequence"] is None or r["planned_offering_id"] is None:
                    shape.append(f"{rid}:missing path fields")
                elif ctx.offerings[r["planned_offering_id"]]["course_id"] != r["course_id"]:
                    shape.append(f"{rid}:planned offering is another course")
                if (r["reason_code"] == "PREREQUISITE_FOR") != (r["required_for_course_id"] is not None):
                    shape.append(f"{rid}:required_for")
                if ctx.employees[r["employee_id"]]["employment_status"] != "ACTIVE":
                    shape.append(f"{rid}:employee not ACTIVE (BR-02)")
            else:
                if r["reason_code"] not in dictionary.NOT_RECOMMENDED_REASONS:
                    shape.append(f"{rid}:reason")
                if any(r[c] is not None for c in ("path_sequence", "planned_offering_id", "required_for_course_id", "cumulative_cost")):
                    shape.append(f"{rid}:path fields set on NOT_RECOMMENDED")
        self.structural("recommendation.row_shape", "recommendation", shape)

        # Path shape (BR-07, BR-08, BR-09a), including injected rows.
        gap = timedelta(days=config.SCHEDULE_GAP_DAYS)
        path_bad = []
        for employee_id, path in ctx.path_by_employee.items():
            if len(path) > config.MAX_PATH_COURSES:
                path_bad.append(f"{employee_id}:{len(path)} courses")
            if [r["path_sequence"] for r in path] != list(range(1, len(path) + 1)):
                path_bad.append(f"{employee_id}:path_sequence")
            previous_end = None
            for r in path:
                start = r["planned_start_date"]
                if start is None:
                    continue
                if start < config.PLANNING_DATE + gap:
                    path_bad.append(f"{r['recommendation_id']}:starts too soon after planning")
                if previous_end is not None and start < previous_end + gap:
                    path_bad.append(f"{r['recommendation_id']}:less than 14 days after the previous step")
                previous_end = r["planned_end_date"]
            if path and path[-1]["cumulative_cost"] > config.LEARNING_ALLOWANCE_PER_EMPLOYEE:
                path_bad.append(f"{employee_id}:over the learning allowance")
        self.structural("recommendation.path_shape", "recommendation", path_bad, "BR-07")

        # Recommendations close the gaps they target (BR-03).
        targets = {(r["role_id"], r["skill_id"]): r["target_level"] for r in self.t["role_skill_target"]}
        closes = []
        for r in self.t["recommendation"]:
            if r["decision"] != "RECOMMENDED" or r["reason_code"] != "CLOSES_GAP":
                continue
            employee = ctx.employees[r["employee_id"]]
            target = targets.get((employee["target_role_id"], r["target_skill_id"]))
            row = ctx.course_skills.get(r["course_id"], {}).get(r["target_skill_id"])
            if target is None or row is None or row["target_level"] < target:
                closes.append(r["recommendation_id"])
        self.structural("recommendation.closes_its_gap", "recommendation", closes, "BR-03")

        self.engine_reconciliation()

    def engine_reconciliation(self):
        """
        Re-run the January plan on the input data. Every row it produces must
        be in the table unchanged. The only extra rows allowed are the
        injected PREREQUISITE_VIOLATION and COURSE_UNAVAILABLE ones.
        """
        catalog = snapshot.build_catalog(self.t)
        settings = recommend.Settings(config.PLANNING_DATE, config.PERIOD_START, config.PERIOD_END)
        planner = recommend.Planner(catalog, settings)
        snap = snapshot.build_snapshot(self.t, catalog, config.PLANNING_DATE, config.PERIOD_START, config.PERIOD_END)
        ledger = schedule.SeatLedger(snapshot.free_seats(catalog, snap))

        fields = ("decision", "reason_code", "target_skill_id", "required_for_course_id", "path_sequence", "planned_offering_id")
        stored = self.ctx.recommendations
        engine_ids = set()
        changed = []
        for employee in sorted(self.t["employee"], key=lambda e: e["employee_id"]):
            rows, _ = planner.recommend(employee, snap, ledger)
            for row in rows:
                engine_ids.add(row["recommendation_id"])
                mine = stored.get(row["recommendation_id"])
                if mine is None or any(mine[f] != row[f] for f in fields):
                    changed.append(row["recommendation_id"])
        self.structural("recommendation.engine_rows_unchanged", "recommendation", changed)
        self.engine_ids = engine_ids & set(stored)

        extra = set(stored) - engine_ids
        expected = self.truth["PREREQUISITE_VIOLATION"] | self.truth["COURSE_UNAVAILABLE"]
        self.rule("recommendation.only_injected_rows_added", "recommendation", extra, expected, None)

    # ---------- enrollments and events ----------

    def enrollments_and_events(self):
        ctx = self.ctx
        bad = []
        for e in self.t["enrollment"]:
            eid = e["enrollment_id"]
            if ids.split_pair(eid) != (e["employee_id"], e["course_id"]):
                bad.append(f"{eid}:id does not match the pair")
            rec = ctx.recommendations.get(e["recommendation_id"])
            if rec is None or (rec["employee_id"], rec["course_id"], rec["decision"]) != (e["employee_id"], e["course_id"], "RECOMMENDED"):
                bad.append(f"{eid}:recommendation")
            elif rec["planned_offering_id"] != e["offering_id"]:
                bad.append(f"{eid}:offering is not the planned one")
            offering = ctx.offerings[e["offering_id"]]
            if offering["course_id"] != e["course_id"]:
                bad.append(f"{eid}:offering course")
            department = ctx.employees[e["employee_id"]]["department_code"]
            if e["budget_id"] != ids.budget_id(department):
                bad.append(f"{eid}:budget")
            if not config.PERIOD_START <= e["requested_on"] <= config.PERIOD_END:
                bad.append(f"{eid}:requested outside the period")
            if e["requested_on"] > offering["start_date"] - timedelta(days=config.MIN_REQUEST_LEAD_DAYS):
                bad.append(f"{eid}:requested less than 7 days before start")
        self.structural("enrollment.links_and_dates", "enrollment", bad)

        life = []
        for e in self.t["enrollment"]:
            history = ctx.events_by_enrollment.get(e["enrollment_id"], [])
            for problem in lifecycle.sequence_problems(history):
                life.append(f"{e['enrollment_id']}:{problem}")
            if history and history[0]["event_on"] != e["requested_on"]:
                life.append(f"{e['enrollment_id']}:first event is not on requested_on")
            offering = ctx.offerings[e["offering_id"]]
            for ev in history:
                if not config.PERIOD_START <= ev["event_on"] <= config.AS_OF_DATE:
                    life.append(f"{ev['event_id']}:outside the period")
                expected_actor = lifecycle.actor_for(ev["to_status"], ev["reason_code"]) if (
                    ev["to_status"] != "REJECTED" or ev["reason_code"] in dictionary.REJECTION_REASONS
                ) else None
                if ev["actor"] != expected_actor:
                    life.append(f"{ev['event_id']}:actor")
                reasons = {"REJECTED": dictionary.REJECTION_REASONS, "WITHDRAWN": dictionary.WITHDRAWAL_REASONS}
                allowed = reasons.get(ev["to_status"])
                if (allowed is None and ev["reason_code"] is not None) or (allowed is not None and ev["reason_code"] not in allowed):
                    life.append(f"{ev['event_id']}:reason_code")
                if ev["to_status"] in ("APPROVED", "REJECTED") and ev["event_on"] >= offering["start_date"]:
                    life.append(f"{ev['event_id']}:decided on or after the start")
                if ev["to_status"] == "IN_PROGRESS" and ev["event_on"] != offering["start_date"]:
                    life.append(f"{ev['event_id']}:start date")
                if ev["to_status"] == "COMPLETED" and ev["event_on"] != offering["end_date"]:
                    life.append(f"{ev['event_id']}:end date")
        self.structural("enrollment_event.lifecycle", "enrollment_event", life, "BR-12")

        # BR-10: seats at approval never exceed capacity.
        approved = Counter()
        for a in ctx.approvals:
            approved[ctx.enrollments[a["enrollment_id"]]["offering_id"]] += 1
        seats = [o for o, n in approved.items() if n > ctx.offerings[o]["capacity"]]
        self.structural("offering.approved_within_capacity", "course_offering", seats, "BR-10")

        # BR-05 at enrollment: an in-path prerequisite PASSED before the start.
        prereq = []
        for e in self.t["enrollment"]:
            if not any(ev["to_status"] == "APPROVED" for ev in ctx.events_by_enrollment[e["enrollment_id"]]):
                continue
            path_courses = {r["course_id"] for r in ctx.path_by_employee.get(e["employee_id"], ())}
            start = ctx.offerings[e["offering_id"]]["start_date"]
            passed = ctx.passed_by_employee.get(e["employee_id"], {})
            for p in ctx.prerequisites.get(e["course_id"], ()):
                if p in path_courses and not (p in passed and passed[p] < start):
                    prereq.append(f"{e['enrollment_id']}:{p}")
        self.structural("enrollment.prerequisites_passed_before_start", "enrollment", prereq, "BR-05")

    # ---------- completions and assessments ----------

    def completions_and_assessments(self):
        ctx = self.ctx
        bad = []
        for c in self.t["completion"]:
            e = ctx.enrollments[c["enrollment_id"]]
            if e["current_status"] != "COMPLETED":
                bad.append(f"{c['completion_id']}:enrollment not COMPLETED")
            if c["completed_on"] != ctx.offerings[e["offering_id"]]["end_date"] or c["completed_on"] > config.AS_OF_DATE:
                bad.append(f"{c['completion_id']}:completed_on")
            if c["result"] != outcomes.completion_result(c["attendance_pct"], c["final_score"]):
                bad.append(f"{c['completion_id']}:result (BR-14)")
        missing = [e["enrollment_id"] for e in self.t["enrollment"] if e["current_status"] == "COMPLETED" and e["enrollment_id"] not in ctx.completions_by_enrollment]
        bad += [f"{m}:COMPLETED without a completion" for m in missing]
        self.structural("completion.matches_enrollment", "completion", bad, "BR-13")

        completions = {c["completion_id"]: c for c in self.t["completion"]}
        band, cap, post = [], [], []
        for a in self.t["proficiency_assessment"]:
            if a["proficiency_level"] != outcomes.band(a["assessment_score"]):
                band.append(a["assessment_id"])
            if a["assessment_type"] != "POST_COURSE":
                continue
            c = completions.get(a["completion_id"])
            if c is None:
                post.append(f"{a['assessment_id']}:no completion")
                continue
            e = ctx.enrollments[c["enrollment_id"]]
            rec = ctx.recommendations[e["recommendation_id"]]
            if rec["reason_code"] != "CLOSES_GAP" or a["skill_id"] != rec["target_skill_id"] or a["employee_id"] != e["employee_id"]:
                post.append(f"{a['assessment_id']}:not the CLOSES_GAP target skill")
            low, high = config.REASSESSMENT_DELAY_DAYS
            if not c["completed_on"] + timedelta(days=low) <= a["assessed_on"] <= c["completed_on"] + timedelta(days=high) or a["assessed_on"] > config.AS_OF_DATE:
                post.append(f"{a['assessment_id']}:date")
            if a["assessor_type"] != "SKILL_TEST":
                post.append(f"{a['assessment_id']}:assessor")
            course_target = ctx.course_skills[e["course_id"]][a["skill_id"]]["target_level"]
            if a["assessment_score"] > outcomes.band_top(course_target):
                cap.append(a["assessment_id"])
        self.structural("assessment.level_is_band_of_score", "proficiency_assessment", band, "BR-15")
        self.structural("assessment.post_course_cap", "proficiency_assessment", cap, "BR-16")
        self.structural("assessment.post_course_links_and_dates", "proficiency_assessment", post, "BR-17")

    # ---------- derived values ----------

    def derived(self):
        ctx = self.ctx
        # Offerings.
        planned = Counter(r["planned_offering_id"] for r in self.t["recommendation"] if r["decision"] == "RECOMMENDED")
        approved = Counter(ctx.enrollments[a["enrollment_id"]]["offering_id"] for a in ctx.approvals)
        seats = [
            o["offering_id"]
            for o in self.t["course_offering"]
            if o["seats_planned"] != planned[o["offering_id"]]
            or o["seats_approved"] != approved[o["offering_id"]]
            or o["seats_planned"] > o["capacity"]
        ]
        self.structural("derived.offering_seats", "course_offering", seats)

        # Recommendations.
        rec_bad = []
        running = {}
        for employee_id, path in ctx.path_by_employee.items():
            total = 0
            for r in path:
                total += ctx.courses[r["course_id"]]["cost_amount"]
                running[r["recommendation_id"]] = total
        for r in self.t["recommendation"]:
            if r["estimated_cost"] != ctx.courses[r["course_id"]]["cost_amount"]:
                rec_bad.append(f"{r['recommendation_id']}:estimated_cost")
            if r["decision"] == "RECOMMENDED":
                o = ctx.offerings[r["planned_offering_id"]]
                if (r["planned_start_date"], r["planned_end_date"]) != (o["start_date"], o["end_date"]):
                    rec_bad.append(f"{r['recommendation_id']}:planned dates")
                if abs(r["cumulative_cost"] - running[r["recommendation_id"]]) > 0.005:
                    rec_bad.append(f"{r['recommendation_id']}:cumulative_cost")
        self.structural("derived.recommendation_costs_and_dates", "recommendation", rec_bad)

        # Enrollments.
        enr_bad = []
        for e in self.t["enrollment"]:
            history = ctx.events_by_enrollment[e["enrollment_id"]]
            if e["cost_amount"] != ctx.courses[e["course_id"]]["cost_amount"]:
                enr_bad.append(f"{e['enrollment_id']}:cost")
            if e["current_status"] != lifecycle.current_status(history) or e["last_event_on"] != history[-1]["event_on"]:
                enr_bad.append(f"{e['enrollment_id']}:status")
        self.structural("derived.enrollment_status_and_cost", "enrollment", enr_bad)

        # Budgets.
        employees = ctx.employees
        planned_cost = defaultdict(float)
        for r in self.t["recommendation"]:
            if r["decision"] == "RECOMMENDED":
                planned_cost[employees[r["employee_id"]]["department_code"]] += r["estimated_cost"]
        engine_cost = defaultdict(float)
        for rid in self.engine_ids:
            r = ctx.recommendations[rid]
            if r["decision"] == "RECOMMENDED":
                engine_cost[employees[r["employee_id"]]["department_code"]] += r["estimated_cost"]
        committed = defaultdict(float)
        for a in ctx.approvals:
            committed[a["department_code"]] += a["cost"]
        budget_bad = []
        for b in self.t["budget"]:
            code = b["department_code"]
            expected_status = "EXCEEDED" if committed[code] > b["limit_amount"] else "WITHIN_LIMIT"
            checks = [
                abs(b["planned_amount"] - planned_cost[code]) < 0.005,
                abs(b["committed_amount"] - committed[code]) < 0.005,
                abs(b["remaining_amount"] - (b["limit_amount"] - committed[code])) < 0.005,
                abs(b["utilization_pct"] - round(100 * committed[code] / b["limit_amount"], 2)) < 0.005,
                b["budget_status"] == expected_status,
                b["budget_id"] == ids.budget_id(code),
                # The limit is set from the January plan itself (s07), so
                # it is recomputed from the rows the engine produces.
                b["limit_amount"] == budget.department_limit(engine_cost[code], config.FUNDING_RATIO),
            ]
            if not all(checks):
                budget_bad.append(b["budget_id"])
        self.structural("derived.budget_totals", "budget", budget_bad)

        # Employee skills.
        latest = {}
        for a in self.t["proficiency_assessment"]:
            if a["assessed_on"] > config.AS_OF_DATE:
                continue
            key = (a["employee_id"], a["skill_id"])
            if key not in latest or (a["assessed_on"], a["assessment_id"]) > (latest[key]["assessed_on"], latest[key]["assessment_id"]):
                latest[key] = a
        es_bad = []
        for row in self.t["employee_skill"]:
            last = latest.get((row["employee_id"], row["skill_id"]))
            if last is None or (row["current_level"], row["last_assessment_id"], row["last_assessed_on"]) != (
                last["proficiency_level"], last["assessment_id"], last["assessed_on"]
            ):
                es_bad.append(f"{row['employee_id']}|{row['skill_id']}")
        self.structural("derived.employee_skill_current", "employee_skill", es_bad)

        # Skill gaps (BR-01) and their plan status.
        catalog = snapshot.build_catalog(self.t)
        planner = recommend.Planner(catalog, recommend.Settings(config.PLANNING_DATE, config.PERIOD_START, config.PERIOD_END))
        snap = snapshot.build_snapshot(self.t, catalog, config.PLANNING_DATE, config.PERIOD_START, config.PERIOD_END)
        rows_by_employee = defaultdict(list)
        for r in self.t["recommendation"]:
            rows_by_employee[r["employee_id"]].append(r)
        stored = {(g["employee_id"], g["skill_id"]): g for g in self.t["skill_gap"]}
        current = {(r["employee_id"], r["skill_id"]): r["current_level"] for r in self.t["employee_skill"]}
        gap_bad = []
        expected_keys = set()
        for employee in self.t["employee"]:
            for g in planner.gap_rows(employee, snap, rows_by_employee[employee["employee_id"]]):
                key = (employee["employee_id"], g["skill_id"])
                expected_keys.add(key)
                s = stored.get(key)
                level = current[key]
                want = {
                    "target_role_id": employee["target_role_id"],
                    "target_level": g["target_level"],
                    "planning_level": g["planning_level"],
                    "planning_gap": g["planning_gap"],
                    "current_level": level,
                    "current_gap": gaps.gap(g["target_level"], level),
                    "plan_status": g["plan_status"],
                    "gap_status": gaps.gap_status(g["planning_gap"], gaps.gap(g["target_level"], level)),
                }
                if s is None or any(s[k] != v for k, v in want.items()):
                    gap_bad.append("|".join(key))
        gap_bad += ["|".join(k) for k in set(stored) - expected_keys]
        self.structural("derived.skill_gap", "skill_gap", gap_bad, "BR-01")

    # ---------- the five RULE checks ----------

    def rule_checks(self):
        tables = {
            "PREREQUISITE_VIOLATION": "recommendation",
            "COURSE_UNAVAILABLE": "recommendation",
            "BUDGET_EXCEEDED": "enrollment",
            "DUPLICATE_COMPLETION": "completion",
            "GAP_NOT_REASSESSED": "completion",
        }
        for issue_type, (rule_code, detector) in detect.DETECTORS.items():
            found = detector(self.ctx)
            self.rule(f"rule.{issue_type.lower()}", tables[issue_type], found, self.truth[issue_type], rule_code)

    def leakage(self):
        words = ("issue", "anomaly", "label", "ground_truth", "injected")
        bad = [
            f"{name}.{column}"
            for name in dictionary.EXPORTED_TABLES
            for column in (self.t[name][0].keys() if self.t[name] else ())
            if any(w in column for w in words)
        ]
        self.structural("leakage.no_label_columns_in_input", "*", bad)


def validate(ctx, ground_truth, plan):
    return Validator(ctx, ground_truth, plan).run()
