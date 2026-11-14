"""
The preview request: dates are checked before any query runs. These need
no database.
"""

import pytest
from pydantic import ValidationError

from app.schemas import PreviewRequest


def make(**overrides):
    body = {
        "employee_id": "EMP-000010",
        "planning_date": "2026-07-01",
        "period_start": "2026-01-01",
        "period_end": "2026-12-31",
    }
    body.update(overrides)
    return PreviewRequest(**body)


def test_a_valid_request():
    assert make().planning_date.isoformat() == "2026-07-01"


@pytest.mark.parametrize(
    "overrides",
    [
        # The reported issue: 2027 dates were accepted and checked against 2026 money.
        {"planning_date": "2027-03-01", "period_start": "2027-01-01", "period_end": "2027-12-31"},
        {"period_end": "2027-06-30"},
        {"period_start": "2025-12-01"},
    ],
)
def test_periods_outside_the_budget_year_are_refused(overrides):
    with pytest.raises(ValidationError, match="budget year"):
        make(**overrides)


def test_period_must_run_forwards():
    with pytest.raises(ValidationError, match="after period_start"):
        make(period_start="2026-06-01", period_end="2026-03-01", planning_date="2026-04-01")


def test_planning_date_must_be_inside_the_period():
    with pytest.raises(ValidationError, match="inside the period"):
        make(period_start="2026-03-01", planning_date="2026-02-01")


def test_employee_id_format():
    with pytest.raises(ValidationError):
        make(employee_id="EMP-1")
