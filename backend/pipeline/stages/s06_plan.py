"""
s07: the January planning run.

rules/recommend.py for every ACTIVE employee in employee_id order, on a
snapshot as of the planning date (BR-20), sharing one seat ledger so no
offering is ever booked past its capacity.

There is no randomness here: the plan is a pure function of s01 to s06.
That is what lets the validator re-run it and compare row by row.
"""

from .. import config
from ..rules import recommend, schedule, snapshot


def january_planner(tables):
    """The planner, snapshot and a fresh seat ledger for the January run."""
    catalog = snapshot.build_catalog(tables)
    settings = recommend.Settings(config.PLANNING_DATE, config.PERIOD_START, config.PERIOD_END)
    planner = recommend.Planner(catalog, settings)
    snap = snapshot.build_snapshot(
        # The plan may only see data dated on or before the planning date.
        # At this point only baseline assessments exist anyway.
        {"proficiency_assessment": tables["proficiency_assessment"]},
        catalog,
        config.PLANNING_DATE,
        config.PERIOD_START,
        config.PERIOD_END,
    )
    ledger = schedule.SeatLedger(snapshot.free_seats(catalog, snap))
    return planner, snap, ledger


def plan_everyone(tables):
    """(recommendation rows, gap rows, ledger) for the whole January run."""
    planner, snap, ledger = january_planner(tables)
    rows, gap_rows = [], []
    for employee in sorted(tables["employee"], key=lambda e: e["employee_id"]):
        employee_rows, employee_gaps = planner.recommend(employee, snap, ledger)
        rows.extend(employee_rows)
        gap_rows.extend(employee_gaps)
    return rows, gap_rows, ledger


def run(tables, plan):
    rows, _, _ = plan_everyone(tables)
    tables["recommendation"] = rows
    return tables
