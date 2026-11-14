"""
Generate one scale twice with the same seed and compare every file.

    python -m scripts.check_reproducibility --scale full

The two runs go to output/_repro/run_a and run_b (gitignored). The report
goes to output/reproducibility/report_<scale>.json and .md, and lists the
row count and SHA-256 of every file in both runs.

Exit code 1 if anything differs.
"""

import argparse
import json
import sys
from pathlib import Path

from pipeline import config, export
from pipeline.run import REPO_ROOT, build


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--scale", choices=sorted(config.SCALES), default="starter")
    args = parser.parse_args(argv)

    scratch = REPO_ROOT / "output" / "_repro"
    runs = {}
    for name in ("run_a", "run_b"):
        print(f"{name}: generating {args.scale} ...")
        _, manifest = build(args.scale, scratch / name, quiet=True)
        manifest_path = scratch / name / "manifest.json"
        files = {f["path"]: f for f in manifest["files"]}
        files["manifest.json"] = {
            "path": "manifest.json",
            "rows": None,
            "sha256": export.sha256(manifest_path),
        }
        runs[name] = files

    paths = sorted(set(runs["run_a"]) | set(runs["run_b"]))
    rows = []
    for path in paths:
        a, b = runs["run_a"].get(path), runs["run_b"].get(path)
        same = a is not None and b is not None and a["sha256"] == b["sha256"] and a["rows"] == b["rows"]
        rows.append(
            {
                "path": path,
                "rows_a": a and a["rows"],
                "rows_b": b and b["rows"],
                "sha256_a": a and a["sha256"],
                "sha256_b": b and b["sha256"],
                "identical": same,
            }
        )

    identical = all(r["identical"] for r in rows)
    report = {"scale": args.scale, "seed": config.SEED, "identical": identical, "files": rows}
    out = REPO_ROOT / "output" / "reproducibility"
    export.write_text(out / f"report_{args.scale}.json", json.dumps(report, indent=2, sort_keys=True) + "\n")

    lines = [
        f"# Reproducibility: {args.scale}",
        "",
        f"Generated twice with seed {config.SEED} into two separate folders.",
        "",
        f"**Result: {'every file is byte-for-byte identical' if identical else 'FILES DIFFER'}** "
        f"({sum(r['identical'] for r in rows)} of {len(rows)} files match).",
        "",
        "| File | Rows (run A) | Rows (run B) | SHA-256 (run A) | Same |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['path']} | {'' if r['rows_a'] is None else r['rows_a']} | "
            f"{'' if r['rows_b'] is None else r['rows_b']} | `{(r['sha256_a'] or '')[:16]}…` | "
            f"{'yes' if r['identical'] else 'NO'} |"
        )
    export.write_text(out / f"report_{args.scale}.md", "\n".join(lines) + "\n")

    print(f"{'Identical' if identical else 'DIFFERENT'}: {sum(r['identical'] for r in rows)}/{len(rows)} files match.")
    return 0 if identical else 1


if __name__ == "__main__":
    sys.exit(main())
