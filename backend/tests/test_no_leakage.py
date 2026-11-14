"""
Ground truth must never leak into the input data (brief, step 7).
"""

import csv

from pipeline import dictionary

WORDS = ("issue", "anomaly", "label", "ground_truth", "injected", "is_valid")


def test_input_csvs_have_no_label_columns(starter):
    for name in dictionary.EXPORTED_TABLES:
        with open(starter["out"] / "csv" / f"{name}.csv", encoding="utf-8") as handle:
            header = next(csv.reader(handle))
        for column in header:
            assert not any(w in column.lower() for w in WORDS), f"{name}.{column}"


def test_ground_truth_is_kept_outside_the_input_folder(starter):
    out = starter["out"]
    assert (out / "ground_truth" / "ground_truth.csv").exists()
    assert not any("ground_truth" in p.name for p in (out / "csv").iterdir())
    assert not any("ground_truth" in p.name for p in (out / "json").iterdir())


def test_input_rows_do_not_name_the_issue_types(starter):
    # COURSE_UNAVAILABLE is both an issue type and a normal NOT_RECOMMENDED
    # reason the engine writes for honest rejections, so it is part of the
    # input vocabulary and not a label. Every other issue name must be absent.
    issue_names = set(dictionary.ISSUE_TYPE) - set(dictionary.RECOMMENDATION_REASON)
    assert issue_names == set(dictionary.ISSUE_TYPE) - {"COURSE_UNAVAILABLE"}
    for name in dictionary.EXPORTED_TABLES:
        text = (starter["out"] / "csv" / f"{name}.csv").read_text(encoding="utf-8")
        for issue in issue_names:
            assert issue not in text, f"{issue} appears in {name}.csv"
