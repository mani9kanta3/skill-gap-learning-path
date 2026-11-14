"""
ids.py: formats, padding, bounds, pair IDs and counters.

Every ID in the dataset goes through these functions, so this is where a
wrong format would be caught before it reached ten thousand rows.
"""

import pytest

from pipeline import ids
from pipeline.ids import IdCounter

NUMBERED = [
    (ids.role_id, "role", "ROL-000001"),
    (ids.skill_id, "skill", "SKL-000001"),
    (ids.employee_id, "employee", "EMP-000001"),
    (ids.course_id, "course", "CRS-000001"),
    (ids.offering_id, "offering", "OFF-000001"),
    (ids.assessment_id, "assessment", "ASM-000001"),
    (ids.event_id, "event", "EVT-000001"),
    (ids.ground_truth_id, "ground_truth", "GT-000001"),
    (ids.completion_id, "completion", "CMP-2026-000001"),
]


@pytest.mark.parametrize("formatter, kind, first", NUMBERED)
def test_first_id_is_zero_padded(formatter, kind, first):
    assert formatter(1) == first
    assert ids.matches(kind, first)


@pytest.mark.parametrize("formatter, kind, first", NUMBERED)
def test_largest_id_still_has_six_digits(formatter, kind, first):
    value = formatter(999_999)
    assert value.endswith("-999999")
    assert ids.matches(kind, value)


@pytest.mark.parametrize("formatter, kind, first", NUMBERED)
@pytest.mark.parametrize("bad", [0, -1, 1_000_000, 1.0, "1", True, None])
def test_out_of_range_or_wrong_type_is_refused(formatter, kind, first, bad):
    with pytest.raises(ValueError):
        formatter(bad)


def test_examples_from_the_brief():
    assert ids.employee_id(1) == "EMP-000001"
    assert ids.skill_id(1) == "SKL-000001"
    assert ids.course_id(1) == "CRS-000001"
    assert ids.completion_id(1) == "CMP-2026-000001"
    assert ids.budget_id("ENG") == "BUD-ENG-2026"
    assert ids.enrollment_id("EMP-000001", "CRS-000042") == "ENR-EMP-000001-CRS-000042"


def test_budget_id_only_for_real_departments():
    for code in ("ENG", "DAT", "ITS", "SAL", "MKT", "FIN", "HRM", "OPS"):
        assert ids.matches("budget", ids.budget_id(code))
    with pytest.raises(ValueError):
        ids.budget_id("XYZ")
    with pytest.raises(ValueError):
        ids.budget_id("eng")


def test_recommendation_id_is_built_from_the_pair():
    value = ids.recommendation_id("EMP-000123", "CRS-000456")
    assert value == "REC-EMP-000123-CRS-000456"
    assert ids.matches("recommendation", value)


@pytest.mark.parametrize("builder", [ids.recommendation_id, ids.enrollment_id])
@pytest.mark.parametrize(
    "employee, course",
    [
        ("EMP-1", "CRS-000001"),
        ("EMP-000001", "CRS-1"),
        ("CRS-000001", "EMP-000001"),  # swapped
        ("emp-000001", "CRS-000001"),
        (None, "CRS-000001"),
    ],
)
def test_pair_ids_refuse_bad_parts(builder, employee, course):
    with pytest.raises(ValueError):
        builder(employee, course)


@pytest.mark.parametrize("builder", [ids.recommendation_id, ids.enrollment_id])
def test_split_pair_round_trips(builder):
    pair_id = builder("EMP-004210", "CRS-000999")
    assert ids.split_pair(pair_id) == ("EMP-004210", "CRS-000999")


def test_split_pair_refuses_other_ids():
    with pytest.raises(ValueError):
        ids.split_pair("EMP-000001")


@pytest.mark.parametrize(
    "value",
    [
        "EMP-000001\n",  # a trailing newline must not sneak past "$"
        " EMP-000001",
        "EMP-00001",
        "EMP-0000001",
        "emp-000001",
        "EMP-٠٠٠٠٠١",  # Arabic-Indic digits
        "",
        None,
        123,
    ],
)
def test_matches_is_strict(value):
    assert not ids.matches("employee", value)


def test_counter_hands_out_ids_in_order():
    counter = IdCounter(ids.event_id)
    assert [counter.next() for _ in range(3)] == ["EVT-000001", "EVT-000002", "EVT-000003"]
    assert counter.issued == 3


def test_counters_are_independent():
    events = IdCounter(ids.event_id)
    completions = IdCounter(ids.completion_id)
    events.next()
    events.next()
    assert completions.next() == "CMP-2026-000001"
