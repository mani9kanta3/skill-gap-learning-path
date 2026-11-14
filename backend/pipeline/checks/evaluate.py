"""
Business metrics and detector accuracy (ARCHITECTURE.md 7.3).

pandas is used here for the group-by style summaries. Every number is
computed from the loaded input tables; ground truth is only used for
the detection scores.
"""

from collections import Counter

import pandas as pd

from .. import config
from . import feasibility


def _metric(rows, group, name, value, dimension="ALL"):
    rows.append({"metric_group": group, "metric_name": name, "dimension": dimension, "value": round(float(value), 4)})


def _rate(part, whole):
    return part / whole if whole else 0.0


def evaluate(ctx, ground_truth, detected):
    t = ctx.t
    rows = []

    # ---------- detection: per-record precision / recall ----------
    truth = {(g["issue_type"], g["record_id"]) for g in ground_truth}
    found = {(d["issue_type"], d["record_id"]) for d in detected}
    for issue_type in config.EDGE_CASE_TYPES + ("ALL",):
        keep = (lambda k: True) if issue_type == "ALL" else (lambda k, it=issue_type: k[0] == it)
        tr = {k for k in truth if keep(k)}
        fo = {k for k in found if keep(k)}
        tp, fp, fn = len(tr & fo), len(fo - tr), len(tr - fo)
        precision = _rate(tp, tp + fp) if (tp + fp) else (1.0 if not tr else 0.0)
        recall = _rate(tp, tp + fn) if (tp + fn) else 1.0
        f1 = _rate(2 * precision * recall, precision + recall)
        for name, value in (("tp", tp), ("fp", fp), ("fn", fn), ("precision", precision), ("recall", recall), ("f1", f1)):
            _metric(rows, "detection", name, value, issue_type)

    # ---------- gap coverage ----------
    gaps = pd.DataFrame(t["skill_gap"])
    open_gaps = gaps[gaps["planning_gap"] > 0]
    for status, n in open_gaps["plan_status"].value_counts().sort_index().items():
        _metric(rows, "gap_coverage", "share_of_planning_gaps", _rate(n, len(open_gaps)), status)
    _metric(rows, "gap_coverage", "planning_gaps", len(open_gaps))
    _metric(rows, "gap_coverage", "average_planning_gap", open_gaps["planning_gap"].mean() if len(open_gaps) else 0)

    # ---------- proposed plan: feasibility on every planning condition ----------
    recommended = [r for r in t["recommendation"] if r["decision"] == "RECOMMENDED"]
    failing = feasibility.failures(ctx)
    _metric(rows, "feasibility", "recommended_rows", len(recommended))
    _metric(rows, "feasibility", "share_feasible_all_checks", _rate(len(recommended) - len(failing), len(recommended)))
    by_rule = Counter(code for codes in failing.values() for code in codes)
    for code in ("BR-04", "BR-05", "BR-07", "BR-08", "BR-09"):
        _metric(rows, "feasibility", "steps_failing", by_rule[code], code)

    # ---------- funded plan ----------
    funding = Counter(r["funding_status"] for r in recommended)
    for status, n in sorted(funding.items()):
        _metric(rows, "funding", "steps", n, status)
    _metric(rows, "funding", "share_funded", _rate(funding["FUNDED"], len(recommended)))
    feasible_and_funded = sum(1 for r in recommended if r["funding_status"] == "FUNDED" and r["recommendation_id"] not in failing)
    _metric(rows, "funding", "share_feasible_and_funded", _rate(feasible_and_funded, len(recommended)))
    decisions = Counter((r["decision"], r["reason_code"]) for r in t["recommendation"])
    for (decision, reason), n in sorted(decisions.items()):
        _metric(rows, "feasibility", f"{decision.lower()}_rows", n, reason)

    # ---------- budget ----------
    rejected_budget = Counter()
    for ev in t["enrollment_event"]:
        if ev["reason_code"] == "BUDGET_EXHAUSTED":
            e = ctx.enrollments[ev["enrollment_id"]]
            rejected_budget[ctx.budgets[e["budget_id"]]["department_code"]] += 1
    for b in t["budget"]:
        code = b["department_code"]
        _metric(rows, "budget", "limit", b["limit_amount"], code)
        _metric(rows, "budget", "planned", b["planned_amount"], code)
        _metric(rows, "budget", "funded", b["funded_amount"], code)
        _metric(rows, "budget", "committed", b["committed_amount"], code)
        _metric(rows, "budget", "utilization_pct", b["utilization_pct"], code)
        _metric(rows, "budget", "budget_rejections", rejected_budget[code], code)

    # ---------- funnel ----------
    ever = Counter()
    for e in t["enrollment"]:
        statuses = {ev["to_status"] for ev in ctx.events_by_enrollment[e["enrollment_id"]]}
        for status in statuses:
            ever[status] += 1
    first = ctx.first_completions
    passed = sum(1 for c in first if c["result"] == "PASSED")
    reassessed = sum(1 for c in first if ctx.post_course_by_completion.get(c["completion_id"]))
    funnel = [
        ("recommended", len(recommended)),
        ("requested", ever["REQUESTED"]),
        ("approved", ever["APPROVED"]),
        ("rejected", ever["REJECTED"]),
        ("started", ever["IN_PROGRESS"]),
        ("withdrawn", ever["WITHDRAWN"]),
        ("completed", ever["COMPLETED"]),
        ("passed", passed),
        ("reassessed", reassessed),
    ]
    for name, n in funnel:
        _metric(rows, "funnel", name, n)

    # ---------- outcomes: attendance, pass and learning are different numbers ----------
    started = ever["IN_PROGRESS"]
    closes = [
        c
        for c in first
        if ctx.recommendations[ctx.enrollments[c["enrollment_id"]]["recommendation_id"]]["reason_code"] == "CLOSES_GAP"
    ]
    reassessed_closes = [c for c in closes if ctx.post_course_by_completion.get(c["completion_id"])]
    targets = {(r["role_id"], r["skill_id"]): r["target_level"] for r in t["role_skill_target"]}
    closed = 0
    uplift = {"PASSED": [], "FAILED": []}
    baseline = {(r["employee_id"], r["skill_id"]): r["baseline_level"] for r in t["employee_skill"]}
    for c in reassessed_closes:
        e = ctx.enrollments[c["enrollment_id"]]
        rec = ctx.recommendations[e["recommendation_id"]]
        post = ctx.post_course_by_completion[c["completion_id"]][0]
        target = targets[(ctx.employees[e["employee_id"]]["target_role_id"], rec["target_skill_id"])]
        if post["proficiency_level"] >= target:
            closed += 1
        uplift[c["result"]].append(post["proficiency_level"] - baseline[(e["employee_id"], rec["target_skill_id"])])
    _metric(rows, "outcomes", "completion_rate_of_started", _rate(ever["COMPLETED"], started))
    _metric(rows, "outcomes", "pass_rate_of_completed", _rate(passed, len(first)))
    _metric(rows, "outcomes", "gap_closed_rate_of_reassessed", _rate(closed, len(reassessed_closes)))
    for result, values in uplift.items():
        _metric(rows, "outcomes", "average_level_uplift", sum(values) / len(values) if values else 0, result)
    due = [c for c in closes if (config.AS_OF_DATE - c["completed_on"]).days >= config.REASSESSMENT_DELAY_DAYS[1]]
    _metric(rows, "outcomes", "reassessment_coverage_of_due", _rate(sum(1 for c in due if ctx.post_course_by_completion.get(c["completion_id"])), len(due)))
    _metric(rows, "outcomes", "gaps_closed_by_as_of", int((gaps["gap_status"] == "CLOSED").sum()))
    _metric(rows, "outcomes", "gaps_still_open", int((gaps["gap_status"] == "OPEN").sum()))

    # ---------- duplicate impact ----------
    _metric(rows, "duplicates", "completion_rows", len(t["completion"]))
    _metric(rows, "duplicates", "distinct_completed_enrollments", len(ctx.completions_by_enrollment))

    # ---------- distributions ----------
    courses = pd.DataFrame(t["course"])
    for level, group in courses.groupby("course_level"):
        _metric(rows, "distribution", "average_cost", group["cost_amount"].mean(), level)
        _metric(rows, "distribution", "average_hours", group["duration_hours"].mean(), level)
    for size, n in open_gaps["planning_gap"].value_counts().sort_index().items():
        _metric(rows, "distribution", "planning_gap_size", n, str(int(size)))
    per_employee = Counter(e["employee_id"] for e in t["enrollment"])
    for n, k in sorted(Counter(per_employee.values()).items()):
        _metric(rows, "distribution", "employees_with_n_enrollments", k, str(n))
    offerings = pd.DataFrame(t["course_offering"])
    used = offerings[offerings["seats_approved"] > 0]
    _metric(rows, "distribution", "average_seat_utilization_of_used_offerings", (used["seats_approved"] / used["capacity"]).mean() if len(used) else 0)

    rows.sort(key=lambda r: (r["metric_group"], r["metric_name"], r["dimension"]))
    return rows
