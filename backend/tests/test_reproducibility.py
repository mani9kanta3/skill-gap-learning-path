"""
The same seed gives byte-identical files (brief, step 10), checked on
the starter scale so it stays quick. The script does the same for full.
"""

from pipeline.run import build


def test_same_seed_gives_identical_files(starter, tmp_path):
    _, again = build("starter", tmp_path / "again", quiet=True)
    first = {f["path"]: (f["rows"], f["sha256"]) for f in starter["manifest"]["files"]}
    second = {f["path"]: (f["rows"], f["sha256"]) for f in again["files"]}
    assert first == second
    assert (starter["out"] / "manifest.json").read_bytes() == (tmp_path / "again" / "manifest.json").read_bytes()
