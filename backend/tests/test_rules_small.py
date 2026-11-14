"""
The small rules: gaps, outcomes, lifecycle, budget, schedule, prerequisites,
availability and the point-in-time snapshot. Mostly edge values, because
that is where an off-by-one hides.
"""

from datetime import date

import pytest

from tests.factory import EMP, S1, World, c
from pipeline.rules import availability, budget, gaps, lifecycle, outcomes, prerequisites, schedule, snapshot

# ---------- BR-01 gaps ----------


@pytest.mark.parametrize("target, level, expected", [(4, 2, 2), (4, 4, 0), (3, 5, 0), (5, 0, 5)])
def test_gap_is_never_negative(target, level, expected):
    assert gaps.gap(target, level) == expected


@pytest.mark.parametrize("planning, current, expected", [(0, 0, "NO_GAP"), (2, 0, "CLOSED"), (2, 1, "OPEN")])
def test_gap_status(planning, current, expected):
    assert gaps.gap_status(planning, current) == expected


# ---------- BR-14 / BR-15 / BR-16 outcomes ----------


@pytest.mark.parametrize(
    "score, level",
    [(0, 0), (19, 0), (20, 1), (39, 1), (40, 2), (54, 2), (55, 3), (69, 3), (70, 4), (84, 4), (85, 5), (100, 5)],
)
def test_band_edges(score, level):
    assert outcomes.band(score) == level


@pytest.mark.parametrize("bad", [-1, 101])
def test_band_refuses_out_of_range(bad):
    with pytest.raises(ValueError):
        outcomes.band(bad)


@pytest.mark.parametrize(
    "attendance, score, result",
    [(75.0, 60, "PASSED"), (74.9, 99, "FAILED"), (100.0, 59, "FAILED"), (90.0, 80, "PASSED")],
)
def test_pass_rule_edges(attendance, score, result):
    assert outcomes.completion_result(attendance, score) == result


def test_round_half_up():
    assert [outcomes.round_half_up(x) for x in (68.5, 69.5, 69.49, -0.5)] == [69, 70, 69, 0]


def test_final_score_mean_moves_with_readiness_and_is_clamped():
    # entry level = target - 2. At the entry level the mean is the base, 70.
    assert outcomes.final_score_mean(pre_level=2, primary_target_level=4) == 70
    assert outcomes.final_score_mean(pre_level=1, primary_target_level=4) == 64
    assert outcomes.final_score_mean(pre_level=5, primary_target_level=2) == 85  # clamped
    assert outcomes.final_score_mean(pre_level=0, primary_target_level=5) == 52


def test_worked_example_from_the_architecture():
    # Pre level 2 (score 47), course target 4. Passing with 78: about 77, level 4.
    score = outcomes.post_course_score(47, 78, "PASSED", noise=0, course_target_level=4)
    assert score == 77 and outcomes.band(score) == 4
    # Passing with 62: about 65, level 3, so the gap stays open.
    score = outcomes.post_course_score(47, 62, "PASSED", noise=0, course_target_level=4)
    assert outcomes.band(score) == 3


def test_course_cannot_certify_above_its_level():
    score = outcomes.post_course_score(60, 100, "PASSED", noise=10, course_target_level=3)
    assert score == outcomes.band_top(3) == 69


def test_failed_course_still_gives_a_small_uplift():
    assert outcomes.uplift(50, "FAILED") == pytest.approx(3.0)
    assert outcomes.uplift(30, "FAILED") == 0


# ---------- BR-12 lifecycle ----------


def ev(seq, frm, to, on):
    return {"event_seq": seq, "from_status": frm, "to_status": to, "event_on": on}


def test_valid_history_has_no_problems():
    history = [
        ev(1, None, "REQUESTED", date(2026, 1, 1)),
        ev(2, "REQUESTED", "APPROVED", date(2026, 1, 3)),
        ev(3, "APPROVED", "IN_PROGRESS", date(2026, 2, 2)),
        ev(4, "IN_PROGRESS", "COMPLETED", date(2026, 2, 8)),
    ]
    assert lifecycle.sequence_problems(history) == []
    assert lifecycle.current_status(history) == "COMPLETED"


def test_forbidden_moves_are_reported():
    history = [
        ev(1, None, "REQUESTED", date(2026, 1, 1)),
        ev(2, "REQUESTED", "COMPLETED", date(2026, 1, 3)),
    ]
    assert any("not allowed" in p for p in lifecycle.sequence_problems(history))


def test_dates_going_backwards_and_gaps_in_seq_are_reported():
    history = [
        ev(1, None, "REQUESTED", date(2026, 1, 5)),
        ev(3, "REQUESTED", "APPROVED", date(2026, 1, 3)),
    ]
    problems = lifecycle.sequence_problems(history)
    assert any("event_seq" in p for p in problems)
    assert any("dated before" in p for p in problems)


def test_nothing_may_follow_a_terminal_status():
    history = [
        ev(1, None, "REQUESTED", date(2026, 1, 1)),
        ev(2, "REQUESTED", "REJECTED", date(2026, 1, 2)),
        ev(3, "REJECTED", "APPROVED", date(2026, 1, 3)),
    ]
    assert any("terminal" in p for p in lifecycle.sequence_problems(history))


def test_actors():
    assert lifecycle.actor_for("REJECTED", "BUDGET_EXHAUSTED") == "HR_PARTNER"
    assert lifecycle.actor_for("REJECTED", "NO_SEATS") == "SYSTEM"
    assert lifecycle.actor_for("APPROVED") == "MANAGER"


# ---------- budget ----------


def test_department_limit_rounds_up():
    assert budget.department_limit(300_000, 1.0) == 300_000
    assert budget.department_limit(300_001, 1.0) == 310_000
    # 2965200 x 0.62 = 1838424 exactly; floating point noise must not matter.
    assert budget.department_limit(2_965_200, 0.62) == 1_840_000
    assert budget.department_limit(1_000_000, 0.62) == 620_000


def test_approval_edge_is_inclusive():
    assert budget.can_approve(committed=90, cost=10, limit=100)
    assert not budget.can_approve(committed=90, cost=10.01, limit=100)


def test_over_limit_replay_uses_event_order():
    approvals = [
        {"department_code": "ENG", "event_on": date(2026, 1, 2), "event_id": "EVT-000002", "enrollment_id": "B", "cost": 60},
        {"department_code": "ENG", "event_on": date(2026, 1, 2), "event_id": "EVT-000001", "enrollment_id": "A", "cost": 60},
        {"department_code": "ENG", "event_on": date(2026, 1, 1), "event_id": "EVT-000003", "enrollment_id": "C", "cost": 30},
    ]
    # Order: C (30), A (90), B (150 > 100).
    assert budget.over_limit_approvals(approvals, {"ENG": 100}) == {"B": 90}


# ---------- schedule ----------


def test_end_date():
    assert schedule.end_date(date(2026, 2, 2), 4) == date(2026, 2, 8)
    assert schedule.end_date(date(2026, 2, 2), 12) == date(2026, 2, 22)
    with pytest.raises(ValueError):
        schedule.end_date(date(2026, 2, 2), 6)


def test_first_slot_respects_busy_courses():
    assert schedule.first_slot(date(2026, 1, 5)) == date(2026, 1, 19)
    assert schedule.first_slot(date(2026, 1, 5), busy_until=date(2026, 2, 1)) == date(2026, 2, 15)


def test_place_skips_full_offerings_and_respects_the_period_end():
    offerings = {
        "A": [
            {"offering_id": "O1", "start_date": date(2026, 2, 2), "end_date": date(2026, 2, 8)},
            {"offering_id": "O2", "start_date": date(2026, 3, 2), "end_date": date(2026, 3, 8)},
        ],
        "B": [{"offering_id": "O3", "start_date": date(2026, 3, 16), "end_date": date(2026, 3, 22)}],
    }
    ledger = schedule.SeatLedger({"O1": 0, "O2": 1, "O3": 1})
    placed = schedule.place(["A", "B"], date(2026, 1, 19), date(2026, 12, 31), offerings, ledger)
    # O1 is full; O2 ends 8 Mar so B must start 22 Mar or later: O3 (16 Mar) is too early.
    assert placed is None
    placed = schedule.place(["A"], date(2026, 1, 19), date(2026, 2, 28), offerings, ledger)
    assert placed is None  # O2 starts after the period end
    placed = schedule.place(["A"], date(2026, 1, 19), date(2026, 12, 31), offerings, ledger)
    assert placed[0][1]["offering_id"] == "O2"


def test_ledger_refuses_overbooking():
    ledger = schedule.SeatLedger({"O1": 1})
    ledger.book("O1")
    with pytest.raises(ValueError):
        ledger.book("O1")


# ---------- prerequisites ----------


def test_chain_order_and_required_for():
    prereqs = {"A": ["I"], "I": ["F"], "F": []}
    assert prerequisites.chain("A", prereqs, passed=set(), in_path=set()) == [("F", "I"), ("I", "A")]
    assert prerequisites.chain("A", prereqs, passed={"I"}, in_path=set()) == []
    assert prerequisites.chain("A", prereqs, passed=set(), in_path={"F"}) == [("I", "A")]


def test_path_violations():
    prereqs = {"B": ["A"]}
    ok_path = [
        {"course_id": "A", "path_sequence": 1, "planned_start_date": date(2026, 2, 2), "planned_end_date": date(2026, 2, 8)},
        {"course_id": "B", "path_sequence": 2, "planned_start_date": date(2026, 2, 22), "planned_end_date": date(2026, 2, 28)},
    ]
    assert prerequisites.path_violations(ok_path, prereqs, passed=set()) == {}
    too_close = [dict(ok_path[0]), dict(ok_path[1], planned_start_date=date(2026, 2, 21))]
    assert prerequisites.path_violations(too_close, prereqs, passed=set()) == {"B": ["A"]}
    assert prerequisites.path_violations(ok_path[1:], prereqs, passed=set()) == {"B": ["A"]}
    assert prerequisites.path_violations(ok_path[1:], prereqs, passed={"A"}) == {}


# ---------- availability ----------


def test_availability():
    period = (date(2026, 1, 1), date(2026, 12, 31))
    assert availability.is_available("ACTIVE", [date(2026, 12, 31)], *period)
    assert not availability.is_available("ACTIVE", [date(2027, 1, 4)], *period)
    assert not availability.is_available("RETIRED", [date(2026, 3, 2)], *period)
    assert not availability.is_available("ACTIVE", [], *period)


# ---------- BR-20 snapshot ----------


def test_snapshot_only_sees_the_past():
    w = World()
    w.employee(levels={S1: 2})
    w.assess(EMP, S1, 4, date(2026, 6, 1))
    w.course(1, {S1: 4}, cost=5000, starts=(date(2026, 3, 2),))
    enrollment = "ENR-EMP-000001-CRS-000001"
    w.tables["enrollment"].append(
        {
            "enrollment_id": enrollment,
            "employee_id": EMP,
            "course_id": c(1),
            "offering_id": "OFF-000001",
            "budget_id": "BUD-ENG-2026",
            "requested_on": date(2026, 2, 1),
            "cost_amount": 5000,
        }
    )
    w.tables["enrollment_event"] += [
        {"enrollment_id": enrollment, "event_seq": 1, "to_status": "REQUESTED", "event_on": date(2026, 2, 1)},
        {"enrollment_id": enrollment, "event_seq": 2, "to_status": "APPROVED", "event_on": date(2026, 2, 3)},
    ]
    catalog = snapshot.build_catalog(w.tables)

    jan = snapshot.build_snapshot(w.tables, catalog, date(2026, 1, 31), date(2026, 1, 1), date(2026, 12, 31))
    assert jan.levels[(EMP, S1)] == 2
    assert not jan.blocked[EMP] and jan.committed["ENG"] == 0 and jan.seats_approved["OFF-000001"] == 0

    feb = snapshot.build_snapshot(w.tables, catalog, date(2026, 2, 10), date(2026, 1, 1), date(2026, 12, 31))
    assert feb.blocked[EMP] == {c(1)}
    assert feb.committed["ENG"] == 5000 and feb.spent[EMP] == 5000
    assert feb.seats_approved["OFF-000001"] == 1
    assert feb.busy_until[EMP] == date(2026, 3, 8)

    jul = snapshot.build_snapshot(w.tables, catalog, date(2026, 7, 1), date(2026, 1, 1), date(2026, 12, 31))
    assert jul.levels[(EMP, S1)] == 4
