"""
Shared fixtures: the starter dataset, built once per test session into a
temporary folder (never into output/), with and without injection.
"""

import pytest

from pipeline import export
from pipeline.checks import context
from pipeline.run import build


@pytest.fixture(scope="session")
def starter(tmp_path_factory):
    out = tmp_path_factory.mktemp("starter")
    results, manifest = build("starter", out, quiet=True)
    return {"out": out, "results": results, "manifest": manifest}


@pytest.fixture(scope="session")
def baseline(tmp_path_factory):
    out = tmp_path_factory.mktemp("baseline")
    results, manifest = build("starter", out, inject=False, quiet=True)
    return {"out": out, "results": results, "manifest": manifest}


@pytest.fixture(scope="session")
def starter_tables(starter):
    return export.read_tables(starter["out"] / "csv")


@pytest.fixture(scope="session")
def starter_truth(starter):
    from pipeline import dictionary

    return export.read_csv(dictionary.table("ground_truth"), starter["out"] / "ground_truth" / "ground_truth.csv")


@pytest.fixture(scope="session")
def starter_context(starter_tables):
    return context.Context(starter_tables)
