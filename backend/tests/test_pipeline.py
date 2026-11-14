"""
The whole pipeline at starter scale.

- The clean baseline (no injection) must pass every check, RULE checks
  included, with zero failing records.
- With injection, every RULE check must fail on exactly the labelled
  records, and the detector must score 1.0.
- A deliberately corrupted file must be caught, so the validator is not
  just passing everything.
"""

import copy
import csv
import json
from collections import Counter

from pipeline import config, export
from pipeline.checks import context, detect, validate


def failed(results):
    return [(r["check_id"], r["unexpected_ids"][:3], r["missed_ids"][:3]) for r in results if r["status"] == "FAIL"]


def test_clean_baseline_passes_every_check(baseline):
    assert failed(baseline["results"]) == []
    truth = list(csv.DictReader(open(baseline["out"] / "ground_truth" / "ground_truth.csv", encoding="utf-8")))
    assert truth == []
    for r in baseline["results"]:
        assert r["failing_count"] == 0, r["check_id"]


def test_injected_starter_passes_every_check(starter):
    assert failed(starter["results"]) == []


def test_rule_checks_match_ground_truth_by_id(starter, starter_truth):
    by_type = {}
    for row in starter_truth:
        by_type.setdefault(row["issue_type"], set()).add(row["record_id"])
    rules = {r["check_id"]: r for r in starter["results"] if r["check_id"].startswith("rule.")}
    for issue_type in config.EDGE_CASE_TYPES:
        check = rules[f"rule.{issue_type.lower()}"]
        assert set(check["failing_ids"]) == by_type[issue_type]
        assert check["unexpected_ids"] == [] and check["missed_ids"] == []


def test_exact_counts(starter_tables, starter_truth):
    scale = config.STARTER
    assert len(starter_tables["employee"]) == scale.employees
    assert len(starter_tables["skill"]) == scale.skills
    assert len(starter_tables["course"]) == scale.courses
    assert len(starter_tables["enrollment"]) == scale.enrollments
    assert Counter(t["issue_type"] for t in starter_truth) == {t: scale.edge_cases_per_type for t in config.EDGE_CASE_TYPES}


def test_detector_scores_one(starter, starter_context, starter_truth):
    found = {(d["issue_type"], d["record_id"]) for d in detect.detect(starter_context)}
    truth = {(t["issue_type"], t["record_id"]) for t in starter_truth}
    assert found == truth
    metrics = json.loads((starter["out"] / "reports" / "metrics.json").read_text(encoding="utf-8"))
    overall = {m["metric_name"]: m["value"] for m in metrics if m["metric_group"] == "detection" and m["dimension"] == "ALL"}
    assert overall["precision"] == 1.0 and overall["recall"] == 1.0


def test_paths_stay_within_four_courses_including_injected(starter_tables):
    per_employee = Counter(r["employee_id"] for r in starter_tables["recommendation"] if r["decision"] == "RECOMMENDED")
    assert max(per_employee.values()) <= config.MAX_PATH_COURSES


def test_each_injected_record_breaks_one_rule_only(starter_context, starter_truth):
    # A labelled record must be found by its own detector and by no other.
    hits = Counter()
    for issue_type, (_, detector) in detect.DETECTORS.items():
        for record_id in detector(starter_context):
            hits[record_id] += 1
    for row in starter_truth:
        assert hits[row["record_id"]] == 1, row


def test_duplicate_completion_keeps_the_original_date(starter_context, starter_truth):
    completions = {c["completion_id"]: c for c in starter_context.t["completion"]}
    for row in starter_truth:
        if row["issue_type"] == "DUPLICATE_COMPLETION":
            original_id = row["related_ids"].split(";")[0]
            copy_row, original = completions[row["record_id"]], completions[original_id]
            assert copy_row["completed_on"] == original["completed_on"]
            assert (copy_row["attendance_pct"], copy_row["final_score"], copy_row["result"]) == (
                original["attendance_pct"],
                original["final_score"],
                original["result"],
            )


def test_learning_outcome_is_separate_from_completion(starter_context):
    # Some PASSED gap-closing courses still leave the gap open: passing is
    # not the same as learning.
    ctx = starter_context
    targets = {(r["role_id"], r["skill_id"]): r["target_level"] for r in ctx.t["role_skill_target"]}
    passed_but_open = 0
    for c in ctx.first_completions:
        post = ctx.post_course_by_completion.get(c["completion_id"])
        if c["result"] != "PASSED" or not post:
            continue
        e = ctx.enrollments[c["enrollment_id"]]
        rec = ctx.recommendations[e["recommendation_id"]]
        target = targets[(ctx.employees[e["employee_id"]]["target_role_id"], rec["target_skill_id"])]
        if post[0]["proficiency_level"] < target:
            passed_but_open += 1
    assert passed_but_open > 0


def _revalidate(tables, truth):
    ctx = context.Context(tables)
    return validate.validate(ctx, truth, config.check_scale(config.STARTER))


def test_validator_catches_a_corrupted_value(starter_tables, starter_truth):
    tables = copy.deepcopy(starter_tables)
    tables["course"][0]["cost_amount"] += 1  # breaks cost = hours x rate
    results = {r["check_id"]: r for r in _revalidate(tables, starter_truth)}
    assert results["course.cost_is_hours_x_rate"]["status"] == "FAIL"
    assert results["course.cost_is_hours_x_rate"]["failing_ids"] == [tables["course"][0]["course_id"]]


def test_validator_catches_an_unlabelled_anomaly(starter_tables, starter_truth):
    # Add one more duplicate completion that ground truth does not know about.
    tables = copy.deepcopy(starter_tables)
    extra = dict(tables["completion"][0], completion_id="CMP-2026-999999")
    tables["completion"].append(extra)
    results = {r["check_id"]: r for r in _revalidate(tables, starter_truth)}
    check = results["rule.duplicate_completion"]
    assert check["status"] == "FAIL"
    assert check["unexpected_ids"] == ["CMP-2026-999999"]


def test_validator_notices_a_missing_label(starter_tables, starter_truth):
    truth = [t for t in starter_truth if t["issue_type"] != "BUDGET_EXCEEDED"] + [
        t for t in starter_truth if t["issue_type"] == "BUDGET_EXCEEDED"
    ][1:]
    results = {r["check_id"]: r for r in _revalidate(starter_tables, truth)}
    assert results["rule.budget_exceeded"]["status"] == "FAIL"
    assert len(results["rule.budget_exceeded"]["unexpected_ids"]) == 1


def test_manifest_lists_every_file_with_a_checksum(starter):
    manifest = starter["manifest"]
    paths = {f["path"] for f in manifest["files"]}
    assert "csv/enrollment.csv" in paths and "ground_truth/ground_truth.csv" in paths
    assert all(len(f["sha256"]) == 64 for f in manifest["files"])
    enrollment = next(f for f in manifest["files"] if f["path"] == "csv/enrollment.csv")
    assert enrollment["rows"] == config.STARTER.enrollments
    assert manifest["seed"] == config.SEED


def test_csv_round_trips_through_the_dictionary(starter):
    from pipeline import dictionary

    table = dictionary.table("enrollment")
    text = (starter["out"] / "csv" / "enrollment.csv").read_text(encoding="utf-8")
    rows = export.read_csv(table, starter["out"] / "csv" / "enrollment.csv")
    assert export.csv_text(table, rows) == text
    assert "\r" not in text
