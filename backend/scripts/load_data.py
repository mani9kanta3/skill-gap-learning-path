"""
Load one generated dataset into Postgres.

    python -m scripts.load_data --scale full

Reads output/<scale>/, empties every table, then COPYs the CSVs in load
order inside one transaction with all foreign keys deferred. Either the
whole dataset goes in, or nothing changes. Afterwards the row count of
every table is compared with manifest.json.

Input tables go to schema public; ground truth and the reports go to
schema eval, so no input query can join them by accident.
"""

import argparse
import json
import sys

from app import config, db
from pipeline import dictionary

# Where each eval table's CSV lives inside output/<scale>/.
EVAL_FILES = {
    "ground_truth": "ground_truth/ground_truth.csv",
    "detected_issue": "reports/detected_issues.csv",
    "validation_result": "reports/validation_result.csv",
    "metric": "reports/metric.csv",
}


def source(table):
    if table.schema == dictionary.EVAL:
        return EVAL_FILES[table.name]
    return f"csv/{table.name}.csv"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Load a generated dataset into Postgres.")
    parser.add_argument("--scale", default="starter", choices=("starter", "full"))
    args = parser.parse_args(argv)

    folder = config.OUTPUT_DIR / args.scale
    manifest_path = folder / "manifest.json"
    if not manifest_path.exists():
        print(f"No dataset in {folder}. Run: python -m pipeline.run --scale {args.scale}")
        return 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {f["path"]: f["rows"] for f in manifest["files"]}

    connection = db.get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL DEFERRED")
            names = ", ".join(f"{t.schema}.{t.name}" for t in dictionary.LOAD_ORDER)
            cursor.execute(f"TRUNCATE {names}")
            for table in dictionary.LOAD_ORDER:
                path = folder / source(table)
                with open(path, encoding="utf-8", newline="") as handle:
                    cursor.copy_expert(
                        f"COPY {table.schema}.{table.name} ({', '.join(table.column_names)}) "
                        "FROM STDIN WITH (FORMAT csv, HEADER true)",
                        handle,
                    )
        # The deferred foreign keys are checked here, all at once.
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    problems = []
    for table in dictionary.LOAD_ORDER:
        loaded = db.fetch_one(f"SELECT count(*) AS n FROM {table.schema}.{table.name}")["n"]
        want = expected.get(source(table))
        status = "ok" if loaded == want else f"MISMATCH (manifest says {want})"
        if loaded != want:
            problems.append(table.name)
        print(f"  {table.schema}.{table.name:<24} {loaded:>7}  {status}")
    if problems:
        print(f"Row counts differ for: {', '.join(problems)}")
        return 1
    print(f"Loaded {args.scale}: every table matches the manifest.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
