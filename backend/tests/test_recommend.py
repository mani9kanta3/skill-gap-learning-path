"""
The recommendation engine on hand-made catalogs (ARCHITECTURE.md 5.2).

Each test builds the smallest world that shows one rule, so a failure
names exactly which rule broke.
"""

from datetime import date, timedelta

from tests.factory import EMP, PLANNING, S1, S2, S3, World, c, path_of, status_of


def test_cheapest_available_course_closes_the_gap():
    w = World()
    w.target(S1, 4)
    w.employee(levels={S1: 2})
    w.course(1, {S1: 4}, cost=5000)
    w.course(2, {S1: 4}, cost=3000)
    rows, gaps = w.plan()

    path = path_of(rows)
    assert [r["course_id"] for r in path] == [c(2)]
    assert path[0]["reason_code"] == "CLOSES_GAP"
    assert path[0]["path_sequence"] == 1
    assert path[0]["cumulative_cost"] == 3000
    assert status_of(gaps, S1) == "PLANNED"


def test_tie_breaks_cost_then_duration_then_id():
    w = World()
    w.target(S1, 4)
    w.employee(levels={S1: 2})
    w.course(3, {S1: 4}, cost=3000, hours=8)
    w.course(2, {S1: 4}, cost=3000, hours=4)
    w.course(1, {S1: 4}, cost=3000, hours=8)
    rows, _ = w.plan()
    assert path_of(rows)[0]["course_id"] == c(2)


def test_first_course_starts_at_least_14_days_after_planning():
    w = World()
    w.target(S1, 4)
    w.employee(levels={S1: 2})
    w.course(1, {S1: 4}, starts=(date(2026, 1, 12), date(2026, 1, 19)))
    rows, _ = w.plan()
    assert path_of(rows)[0]["planned_start_date"] == date(2026, 1, 19)


def test_prerequisite_chain_comes_first_and_ends_14_days_before():
    w = World()
    w.target(S1, 4)
    w.employee(levels={S1: 1})
    w.course(1, {S1: 2}, hours=8, starts=(date(2026, 1, 19), date(2026, 3, 2)))
    w.course(2, {S1: 4}, prereqs=(1,), starts=(date(2026, 2, 2), date(2026, 2, 16), date(2026, 4, 6)))
    rows, _ = w.plan()

    first, second = path_of(rows)
    assert (first["course_id"], first["reason_code"], first["required_for_course_id"]) == (
        c(1),
        "PREREQUISITE_FOR",
        c(2),
    )
    assert (second["course_id"], second["reason_code"]) == (c(2), "CLOSES_GAP")
    # 1 runs 19 Jan - 1 Feb, so 2 may start on 15 Feb at the earliest.
    assert second["planned_start_date"] == date(2026, 2, 16)
    assert second["planned_start_date"] >= first["planned_end_date"] + timedelta(days=14)


def test_passed_prerequisite_is_not_planned_again():
    w = World()
    w.target(S1, 4)
    w.employee(levels={S1: 2})
    w.course(1, {S1: 2})
    w.course(2, {S1: 4}, prereqs=(1,), starts=(date(2026, 8, 3),))
    # A PASSED completion of course 1 before the planning date.
    w.tables["enrollment"].append(
        {
            "enrollment_id": "ENR-EMP-000001-CRS-000001",
            "employee_id": EMP,
            "course_id": c(1),
            "offering_id": "OFF-000001",
            "budget_id": "BUD-ENG-2026",
            "requested_on": date(2026, 1, 10),
            "cost_amount": 1000,
        }
    )
    w.tables["completion"].append(
        {"enrollment_id": "ENR-EMP-000001-CRS-000001", "completed_on": date(2026, 2, 8), "result": "PASSED"}
    )
    rows, _ = w.plan(planning_date=date(2026, 7, 1))
    assert [r["course_id"] for r in path_of(rows)] == [c(2)]


def test_unavailable_course_falls_through_to_the_next_candidate():
    w = World()
    w.target(S1, 4)
    w.employee(levels={S1: 2})
    w.course(1, {S1: 4}, cost=100, starts=(date(2027, 2, 1),))  # only next year
    w.course(2, {S1: 4}, cost=900)
    rows, _ = w.plan()
    assert [r["course_id"] for r in path_of(rows)] == [c(2)]
    # Nothing is written for course 1: a winner was found.
    assert len(rows) == 1


def test_path_limit_tries_a_candidate_with_a_shorter_chain():
    # The review point: PATH_LIMIT on one candidate must not end the search.
    w = World()
    w.target(S2, 5)  # gap 5, planned first: takes one slot
    w.target(S1, 4)  # gap 4
    w.employee(levels={S1: 0, S2: 0})
    many = tuple(date(2026, 1, 19) + timedelta(weeks=3 * k) for k in range(15))
    w.course(6, {S2: 5}, cost=100, starts=many)
    # The cheapest S1 course needs a chain of 3 prerequisites (4 slots in all),
    # which no longer fits next to course 6.
    w.course(1, {S3: 1}, starts=many)
    w.course(2, {S3: 2}, prereqs=(1,), starts=many)
    w.course(3, {S3: 3}, prereqs=(2,), starts=many)
    w.course(4, {S1: 4}, cost=500, prereqs=(3,), starts=many)
    # A dearer S1 course with no chain must win instead.
    w.course(5, {S1: 4}, cost=2000, starts=many)

    rows, gaps = w.plan()
    assert [r["course_id"] for r in path_of(rows)] == [c(6), c(5)]
    assert status_of(gaps, S1) == "PLANNED"
    assert len(rows) == 2  # course 4 lost, but a winner was found, so no row


def test_over_budget_tries_the_next_candidate():
    w = World()
    w.target(S1, 4)
    w.employee(levels={S1: 2})
    w.course(1, {S1: 2}, cost=59_500, starts=(date(2026, 1, 19),))
    w.course(2, {S1: 4}, cost=1000, prereqs=(1,), starts=(date(2026, 3, 2),))
    w.course(3, {S1: 4}, cost=2000, starts=(date(2026, 3, 2),))
    rows, _ = w.plan(allowance=60_000)
    assert [r["course_id"] for r in path_of(rows)] == [c(3)]


def test_allowance_edge_is_inclusive():
    w = World()
    w.target(S1, 4)
    w.employee(levels={S1: 2})
    w.course(1, {S1: 4}, cost=60_000)
    rows, _ = w.plan(allowance=60_000)
    assert [r["course_id"] for r in path_of(rows)] == [c(1)]
    rows, gaps = w.plan(allowance=59_999)
    assert path_of(rows) == []
    assert rows[0]["reason_code"] == "OVER_BUDGET"
    assert status_of(gaps, S1) == "OVER_BUDGET"


def test_department_remaining_budget_is_checked():
    w = World(limit=500)
    w.target(S1, 4)
    w.employee(levels={S1: 2})
    w.course(1, {S1: 4}, cost=600)
    rows, gaps = w.plan()
    assert rows[0]["decision"] == "NOT_RECOMMENDED"
    assert status_of(gaps, S1) == "OVER_BUDGET"


def test_full_offering_tries_the_next_candidate():
    w = World()
    w.target(S1, 4)
    w.employee(levels={S1: 2})
    w.course(1, {S1: 4}, cost=100, capacity=0)
    w.course(2, {S1: 4}, cost=900)
    rows, _ = w.plan()
    assert [r["course_id"] for r in path_of(rows)] == [c(2)]


def test_no_candidate_left_writes_one_row_for_the_best():
    w = World()
    w.target(S1, 4)
    w.employee(levels={S1: 2})
    w.course(1, {S1: 4}, cost=100, capacity=0)  # NO_SCHEDULE
    w.course(2, {S1: 4}, cost=900, starts=(date(2027, 3, 1),))  # unavailable
    rows, gaps = w.plan()
    assert len(rows) == 1
    # Course 2 is unavailable so it ranks last; course 1 is the best-ranked.
    assert (rows[0]["course_id"], rows[0]["reason_code"]) == (c(1), "NO_SCHEDULE")
    assert rows[0]["path_sequence"] is None and rows[0]["planned_offering_id"] is None
    assert status_of(gaps, S1) == "NO_SCHEDULE"


def test_unavailable_prerequisite():
    w = World()
    w.target(S1, 4)
    w.employee(levels={S1: 2})
    w.course(1, {S1: 2}, status="RETIRED", starts=())
    w.course(2, {S1: 4}, prereqs=(1,))
    rows, gaps = w.plan()
    assert rows[0]["reason_code"] == "PREREQUISITE_UNAVAILABLE"
    assert status_of(gaps, S1) == "PREREQUISITE_UNAVAILABLE"


def test_a_course_already_on_the_path_covers_a_second_gap():
    w = World()
    w.target(S1, 4)
    w.target(S2, 3, importance="SUPPORTING")
    w.employee(levels={S1: 2, S2: 1})
    w.course(1, {S1: 4, S2: 3})
    rows, gaps = w.plan()
    assert len(rows) == 1
    assert status_of(gaps, S2) == "PLANNED"


def test_statuses_for_no_gap_no_course_and_on_leave():
    w = World()
    w.target(S1, 3)
    w.target(S2, 4)
    w.employee(levels={S1: 3, S2: 1})
    w.course(1, {S2: 3})  # does not reach 4
    w.course(2, {S2: 5}, status="RETIRED", starts=())
    rows, gaps = w.plan()
    assert rows == []
    assert status_of(gaps, S1) == "NO_GAP"
    assert status_of(gaps, S2) == "NO_COURSE"

    w.employee("EMP-000002", levels={S2: 1}, status="ON_LEAVE")
    rows, gaps = w.plan("EMP-000002")
    assert rows == []
    assert {g["plan_status"] for g in gaps} == {"EMPLOYEE_ON_LEAVE"}


def test_core_gaps_and_bigger_gaps_go_first():
    w = World()
    w.target(S1, 3, importance="SUPPORTING")
    w.target(S2, 3)
    w.target(S3, 5)
    w.employee(levels={S1: 0, S2: 2, S3: 1})
    w.course(1, {S1: 3}, starts=(date(2026, 1, 19), date(2026, 5, 4), date(2026, 9, 7)))
    w.course(2, {S2: 3}, starts=(date(2026, 1, 19), date(2026, 5, 4), date(2026, 9, 7)))
    w.course(3, {S3: 5}, starts=(date(2026, 1, 19), date(2026, 5, 4), date(2026, 9, 7)))
    rows, _ = w.plan()
    # CORE before SUPPORTING; among CORE, gap 4 (S3) before gap 1 (S2).
    assert [r["course_id"] for r in path_of(rows)] == [c(3), c(2), c(1)]


def test_seats_are_shared_across_employees():
    w = World()
    w.target(S1, 4)
    w.employee("EMP-000001", levels={S1: 2})
    w.employee("EMP-000002", levels={S1: 2})
    w.course(1, {S1: 4}, capacity=1, starts=(date(2026, 2, 2), date(2026, 3, 2)))
    planner, snap, ledger = w.planner()
    first, _ = planner.recommend(w.employees["EMP-000001"], snap, ledger)
    second, _ = planner.recommend(w.employees["EMP-000002"], snap, ledger)
    assert first[0]["planned_start_date"] == date(2026, 2, 2)
    assert second[0]["planned_start_date"] == date(2026, 3, 2)


def test_planning_date_hides_later_assessments():
    # BR-20: a December assessment must not leak into a January plan.
    w = World()
    w.target(S1, 4)
    w.employee(levels={S1: 2})
    w.assess(EMP, S1, 4, date(2026, 6, 1))
    w.course(1, {S1: 4}, starts=(date(2026, 2, 2), date(2026, 9, 7)))
    rows, gaps = w.plan()
    assert len(path_of(rows)) == 1
    rows, gaps = w.plan(planning_date=date(2026, 7, 1))
    assert rows == [] and status_of(gaps, S1) == "NO_GAP"


def test_preview_only_uses_offerings_after_the_planning_date():
    w = World()
    w.target(S1, 4)
    w.employee(levels={S1: 2})
    w.course(1, {S1: 4}, starts=(date(2026, 2, 2), date(2026, 7, 6), date(2026, 7, 20)))
    rows, _ = w.plan(planning_date=date(2026, 7, 1))
    # 1 Jul + 14 days = 15 Jul, so 6 Jul is too early.
    assert path_of(rows)[0]["planned_start_date"] == date(2026, 7, 20)


def test_path_never_exceeds_four_courses():
    w = World()
    skills = [f"SKL-0000{n:02d}" for n in range(10, 16)]
    for skill in skills:
        w.target(skill, 2)
    w.employee(levels={skill: 0 for skill in skills})
    mondays = [date(2026, 1, 19) + timedelta(weeks=3 * k) for k in range(15)]
    for n, skill in enumerate(skills, start=1):
        w.course(n, {skill: 2}, starts=tuple(mondays))
    rows, gaps = w.plan()
    assert len(path_of(rows)) == 4
    assert [r["path_sequence"] for r in path_of(rows)] == [1, 2, 3, 4]
    assert sorted(g["plan_status"] for g in gaps).count("PATH_LIMIT") == 2
