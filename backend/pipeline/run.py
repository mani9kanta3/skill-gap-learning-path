"""
The generator command.

    python -m pipeline.run --scale starter
    python -m pipeline.run --scale full
    python -m pipeline.run --scale starter --no-inject --out ../output/_baseline

What it does, in order:
1. generate the tables (stages s01..s10),
2. write CSV and JSON, the data dictionary and schema.sql,
3. read the CSVs back, so every check runs on exactly what was written,
4. validate, detect and evaluate,
5. write the reports, the eval tables, seed.sql and manifest.json.

The exit code is 1 if any check fails, so a broken dataset cannot pass
quietly in a script or CI job.
"""

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

from . import config, dictionary, export
from .checks import context, detect, evaluate, validate
from .generate import generate

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GENERATOR_VERSION = "1.0.0"
OWNED = ("csv", "json", "sql", "ground_truth", "reports", "manifest.json")


def parameters():
    """Every upper-case setting in config, as JSON-friendly values."""
    result = {}
    for name in sorted(vars(config)):
        if not name.isupper():
            continue
        value = getattr(config, name)
        if hasattr(value, "isoformat"):
            value = value.isoformat()
        elif isinstance(value, config.Scale):
            value = vars(value)
        elif isinstance(value, dict) and value and isinstance(next(iter(value.values())), config.Scale):
            value = {k: vars(v) for k, v in value.items()}
        result[name] = json.loads(json.dumps(value, default=lambda v: v.isoformat() if hasattr(v, "isoformat") else str(v)))
    return result


def clear(out):
    """Remove only what this command writes, never anything else in the folder."""
    for name in OWNED:
        target = out / name
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()


def build(scale_name, out, inject=True, quiet=False):
    started = time.time()
    say = (lambda *a: None) if quiet else print
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    clear(out)

    say(f"Generating {scale_name} (seed {config.SEED}, inject={inject}) ...")
    tables, plan = generate(scale_name, inject=inject)

    for name in dictionary.EXPORTED_TABLES:
        table = dictionary.table(name)
        export.write_text(out / "csv" / f"{name}.csv", export.csv_text(table, tables[name]))
        export.write_text(out / "json" / f"{name}.json", export.json_text(table, tables[name]))
    truth_table = dictionary.table("ground_truth")
    export.write_text(out / "ground_truth" / "ground_truth.csv", export.csv_text(truth_table, tables["ground_truth"]))
    export.write_text(out / "ground_truth" / "ground_truth.json", export.json_text(truth_table, tables["ground_truth"]))
    export.write_text(out / "sql" / "schema.sql", export.schema_sql())

    # Read everything back: the checks see exactly what a user would get.
    loaded = export.read_tables(out / "csv")
    truth = export.read_csv(truth_table, out / "ground_truth" / "ground_truth.csv")
    ctx = context.Context(loaded)

    say("Validating ...")
    results = validate.validate(ctx, truth, plan)
    detected = detect.detect(ctx)
    metrics = evaluate.evaluate(ctx, truth, detected)

    validation_rows = [
        {
            "check_id": r["check_id"],
            "rule_code": r["rule_code"],
            "table_name": r["table_name"],
            "kind": r["kind"],
            "failing_count": r["failing_count"],
            "expected_count": r["expected_count"],
            "status": r["status"],
            "sample_ids": ";".join(r["failing_ids"][: validate.SAMPLE]) or None,
        }
        for r in results
    ]
    reports = out / "reports"
    export.write_text(reports / "validation_result.csv", export.csv_text(dictionary.table("validation_result"), validation_rows))
    export.write_text(reports / "detected_issues.csv", export.csv_text(dictionary.table("detected_issue"), detected))
    export.write_text(reports / "metric.csv", export.csv_text(dictionary.table("metric"), metrics))
    export.write_text(reports / "validation_summary.json", json.dumps(summary_json(results), indent=2, sort_keys=True) + "\n")
    export.write_text(reports / "validation_summary.md", summary_md(scale_name, inject, results))
    export.write_text(reports / "metrics.json", json.dumps(metrics, indent=2, sort_keys=True) + "\n")
    export.write_text(reports / "evaluation.md", evaluation_md(scale_name, metrics, truth))

    eval_tables = {
        "ground_truth": truth,
        "detected_issue": detected,
        "validation_result": validation_rows,
        "metric": metrics,
    }
    export.write_text(out / "sql" / "seed.sql", export.seed_sql({**loaded, **eval_tables}))

    manifest = write_manifest(out, scale_name, plan, inject)
    failed = [r for r in results if r["status"] == "FAIL"]
    say(
        f"Done in {time.time() - started:.1f}s: {len(manifest['files'])} files, "
        f"{len(results)} checks, {len(failed)} failed."
    )
    for r in failed:
        say(f"  FAIL {r['check_id']}: unexpected {r['unexpected_ids'][:5]} missed {r['missed_ids'][:5]}")
    return results, manifest


def summary_json(results):
    passed = sum(r["status"] == "PASS" for r in results)
    return {
        "checks": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "results": [
            {
                "check_id": r["check_id"],
                "rule_code": r["rule_code"],
                "table": r["table_name"],
                "kind": r["kind"],
                "status": r["status"],
                "failing_count": r["failing_count"],
                "expected_count": r["expected_count"],
                # RULE checks list every ID so the per-record match is visible.
                "failing_ids": r["failing_ids"] if r["kind"] == "RULE" else r["failing_ids"][: validate.SAMPLE],
                "unexpected_ids": r["unexpected_ids"][: validate.SAMPLE * 5],
                "missed_ids": r["missed_ids"][: validate.SAMPLE * 5],
            }
            for r in results
        ],
    }


def summary_md(scale_name, inject, results):
    passed = sum(r["status"] == "PASS" for r in results)
    lines = [
        f"# Validation summary: {scale_name}",
        "",
        f"Seed {config.SEED}. Edge cases injected: {'yes' if inject else 'no'}.",
        "",
        f"**{passed} of {len(results)} checks passed.**",
        "",
        "STRUCTURAL checks must fail on nothing. RULE checks must fail on exactly the",
        "ground-truth records of their issue type, matched by ID (unexpected = failing but",
        "not labelled, missed = labelled but not failing).",
        "",
        "| Check | Rule | Table | Kind | Failing | Expected | Unexpected | Missed | Status |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {r['check_id']} | {r['rule_code'] or ''} | {r['table_name']} | {r['kind']} | "
            f"{r['failing_count']} | {r['expected_count']} | {len(r['unexpected_ids'])} | "
            f"{len(r['missed_ids'])} | {r['status']} |"
        )
    return "\n".join(lines) + "\n"


def evaluation_md(scale_name, metrics, truth):
    def get(group, name, dimension="ALL"):
        for m in metrics:
            if (m["metric_group"], m["metric_name"], m["dimension"]) == (group, name, dimension):
                return m["value"]
        return 0

    pct = lambda v: f"{100 * v:.1f}%"
    lines = [
        f"# Evaluation: {scale_name}",
        "",
        "Every number below is computed from the generated input tables. Ground truth is",
        "used only for the detection scores. The full list is in `metrics.json`.",
        "",
        "## Detection (detector vs ground truth, matched by record ID)",
        "",
        "| Issue type | Labelled | TP | FP | FN | Precision | Recall | F1 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    labelled = {t: sum(1 for g in truth if g["issue_type"] == t) for t in config.EDGE_CASE_TYPES}
    labelled["ALL"] = len(truth)
    for issue in config.EDGE_CASE_TYPES + ("ALL",):
        lines.append(
            f"| {issue} | {labelled[issue]} | {get('detection', 'tp', issue):.0f} | {get('detection', 'fp', issue):.0f} | "
            f"{get('detection', 'fn', issue):.0f} | {get('detection', 'precision', issue):.3f} | "
            f"{get('detection', 'recall', issue):.3f} | {get('detection', 'f1', issue):.3f} |"
        )
    lines += [
        "",
        "## Funnel",
        "",
        "| Step | Count |",
        "|---|---|",
    ]
    for name in ("recommended", "requested", "approved", "rejected", "started", "withdrawn", "completed", "passed", "reassessed"):
        lines.append(f"| {name} | {get('funnel', name):.0f} |")
    lines += [
        "",
        "## Attendance, passing and learning are different numbers",
        "",
        f"- Completed, of started: {pct(get('outcomes', 'completion_rate_of_started'))}",
        f"- Passed, of completed: {pct(get('outcomes', 'pass_rate_of_completed'))}",
        f"- Gap closed, of reassessed gap-closing courses: {pct(get('outcomes', 'gap_closed_rate_of_reassessed'))}",
        f"- Average level uplift after a PASSED course: {get('outcomes', 'average_level_uplift', 'PASSED'):.2f}",
        f"- Average level uplift after a FAILED course: {get('outcomes', 'average_level_uplift', 'FAILED'):.2f}",
        f"- Reassessment coverage of due completions: {pct(get('outcomes', 'reassessment_coverage_of_due'))}",
        "",
        "## Recommendations",
        "",
        f"- RECOMMENDED rows: {get('feasibility', 'recommended_rows'):.0f}",
        f"- Feasible (BR-04 and BR-05 hold): {pct(get('feasibility', 'share_feasible'))}",
        f"- Planning gaps: {get('gap_coverage', 'planning_gaps'):.0f}, of which PLANNED: "
        f"{pct(get('gap_coverage', 'share_of_planning_gaps', 'PLANNED'))}",
        "",
        "## Budgets",
        "",
        "| Department | Limit | Planned | Committed | Utilization | Budget rejections |",
        "|---|---|---|---|---|---|",
    ]
    for code in config.DEPARTMENT_CODES:
        lines.append(
            f"| {code} | {get('budget', 'limit', code):,.0f} | {get('budget', 'planned', code):,.0f} | "
            f"{get('budget', 'committed', code):,.0f} | {get('budget', 'utilization_pct', code):.2f}% | "
            f"{get('budget', 'budget_rejections', code):.0f} |"
        )
    return "\n".join(lines) + "\n"


def write_manifest(out, scale_name, plan, inject):
    files = []
    for path in sorted(p for p in out.rglob("*") if p.is_file() and p.name != "manifest.json"):
        relative = path.relative_to(out).as_posix()
        files.append({"path": relative, "rows": export.count_rows(path), "sha256": export.sha256(path)})
    manifest = {
        "generator": "skill-gap-learning-path",
        "generator_version": GENERATOR_VERSION,
        "command": f"python -m pipeline.run --scale {scale_name}" + ("" if inject else " --no-inject"),
        "seed": config.SEED,
        "scale": vars(plan.scale),
        "derived_scale": {
            "skills_per_category": plan.skills_per_category,
            "home_ladder_skills": plan.home_ladder_skills,
            "shared_ladder_skills": plan.shared_ladder_skills,
            "baseline_enrollments": plan.baseline_enrollments,
            "injected_enrollments": plan.injected_enrollments,
        },
        "edge_cases_injected": inject,
        "planning_date": config.PLANNING_DATE.isoformat(),
        "planning_period": [config.PERIOD_START.isoformat(), config.PERIOD_END.isoformat()],
        "as_of_date": config.AS_OF_DATE.isoformat(),
        "parameters": parameters(),
        "provenance": {
            "data": "Fully synthetic. No external dataset was used.",
            "names": "Word lists written for this project (pipeline/vocab.py). No real people.",
            "license": "Generated data may be shared freely with this repository.",
        },
        "files": files,
    }
    export.write_text(out / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate, validate and export the dataset.")
    parser.add_argument("--scale", choices=sorted(config.SCALES), default="starter")
    parser.add_argument("--out", default=None, help="Output folder. Default: output/<scale> at the repo root.")
    parser.add_argument("--no-inject", action="store_true", help="Clean baseline without edge cases.")
    parser.add_argument("--docs", action="store_true", help="Also rewrite docs/data_dictionary.md.")
    args = parser.parse_args(argv)

    out = Path(args.out) if args.out else REPO_ROOT / "output" / args.scale
    results, _ = build(args.scale, out, inject=not args.no_inject)
    if args.docs:
        export.write_text(REPO_ROOT / "docs" / "data_dictionary.md", export.data_dictionary_md())
    return 1 if any(r["status"] == "FAIL" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
