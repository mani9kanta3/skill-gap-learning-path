"""
rng.py: the same (seed, stage, stream) always gives the same numbers, and
different stages never share a stream.
"""

import pytest

from pipeline import rng


def draws(stage, stream=0, seed=20261022):
    return rng.stage_rng(stage, stream=stream, seed=seed).integers(0, 1_000_000, size=5).tolist()


def test_same_inputs_give_same_numbers():
    assert draws(rng.CATALOG) == draws(rng.CATALOG)


def test_default_seed_is_the_project_seed():
    default = rng.stage_rng(rng.CATALOG).integers(0, 1_000_000, size=5).tolist()
    assert default == draws(rng.CATALOG, seed=20261022)


def test_stages_get_different_streams():
    assert draws(rng.EMPLOYEES) != draws(rng.CATALOG)


def test_streams_within_a_stage_differ():
    assert draws(rng.INJECT, stream=0) != draws(rng.INJECT, stream=1)


def test_seed_changes_the_numbers():
    assert draws(rng.CATALOG, seed=1) != draws(rng.CATALOG, seed=2)


def test_one_stage_does_not_disturb_another():
    # Drawing a lot from one stage must not change what the next stage sees.
    before = draws(rng.OFFERINGS)
    rng.stage_rng(rng.CATALOG).random(10_000)
    assert draws(rng.OFFERINGS) == before


@pytest.mark.parametrize("stage", [0, 11, "s01", None])
def test_unknown_stage_is_refused(stage):
    with pytest.raises(ValueError):
        rng.stage_rng(stage)


@pytest.mark.parametrize("stream", [-1, 1.5, "0"])
def test_bad_stream_is_refused(stream):
    with pytest.raises(ValueError):
        rng.stage_rng(rng.CATALOG, stream=stream)
