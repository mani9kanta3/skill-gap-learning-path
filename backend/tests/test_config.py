"""
config.py: the scales, check_scale(), and whether the scenario numbers
agree with each other and with the data dictionary.

The scale tests pin the exact numbers from ARCHITECTURE.md, so a change to
a scale that the document does not mention fails here first.
"""

from dataclasses import replace
from datetime import timedelta

import pytest

from pipeline import config, dictionary
from pipeline.config import ScaleError, check_scale


# ---------- the two real scales ----------


def test_full_scale_matches_the_brief():
    full = config.get_scale("full")
    assert (full.employees, full.skills, full.courses, full.enrollments) == (5000, 500, 1000, 10000)
    assert full.edge_cases_per_type == 50


def test_starter_is_ten_percent_of_full():
    starter = config.get_scale("starter")
    assert (starter.employees, starter.skills, starter.courses, starter.enrollments) == (
        500,
        50,
        100,
        1000,
    )
    assert starter.edge_cases_per_type == 5


def test_full_plan():
    plan = check_scale(config.FULL)
    assert plan.skills_per_category == 50
    assert (plan.home_ladder_skills, plan.shared_ladder_skills) == (6, 4)
    assert (plan.injected_enrollments, plan.baseline_enrollments) == (50, 9950)


def test_starter_plan_is_scale_aware():
    # The review point: starter has only 5 skills per category, so the
    # ladder must take 5 home skills and fill the rest from shared ones.
    plan = check_scale(config.STARTER)
    assert plan.skills_per_category == 5
    assert (plan.home_ladder_skills, plan.shared_ladder_skills) == (5, 5)
    assert plan.home_ladder_skills + plan.shared_ladder_skills == config.LADDER_SIZE
    assert (plan.injected_enrollments, plan.baseline_enrollments) == (5, 995)


@pytest.mark.parametrize("name", sorted(config.SCALES))
def test_every_scale_passes_its_own_check(name):
    plan = check_scale(config.get_scale(name))
    assert plan.home_ladder_skills >= config.CORE_SKILL_COUNT
    assert plan.shared_ladder_skills <= plan.skills_per_category * len(config.SHARED_CATEGORIES)
    assert plan.smallest_department >= config.ROLES_PER_DEPARTMENT


def test_unknown_scale_names_the_real_ones():
    with pytest.raises(ScaleError, match="full, starter"):
        config.get_scale("medium")


# ---------- scales that must be refused ----------


def test_too_few_skills_per_category_for_core_skills():
    # 30 skills -> 3 per category -> only 3 home skills, but 4 must be CORE.
    bad = replace(config.STARTER, name="tiny", skills=30, courses=60)
    with pytest.raises(ScaleError, match="CORE"):
        check_scale(bad)


def test_skills_must_split_evenly_into_categories():
    bad = replace(config.STARTER, name="odd", skills=55, courses=110)
    with pytest.raises(ScaleError, match="divide evenly"):
        check_scale(bad)


def test_courses_must_be_two_per_skill():
    bad = replace(config.STARTER, name="short", courses=99)
    with pytest.raises(ScaleError, match="courses"):
        check_scale(bad)


def test_every_department_needs_every_career_level():
    bad = replace(config.STARTER, name="few", employees=40)
    with pytest.raises(ScaleError, match="career levels"):
        check_scale(bad)


def test_enrollments_must_exceed_injected_cases():
    bad = replace(config.STARTER, name="empty", enrollments=5)
    with pytest.raises(ScaleError, match="injected"):
        check_scale(bad)


def test_all_problems_are_reported_together():
    bad = replace(config.STARTER, name="broken", skills=30, courses=7, employees=40)
    with pytest.raises(ScaleError) as error:
        check_scale(bad)
    message = str(error.value)
    assert "CORE" in message and "courses" in message and "career levels" in message


# ---------- shares ----------


@pytest.mark.parametrize(
    "shares",
    [
        config.DEPARTMENT_SHARE,
        config.CAREER_LEVEL_SHARE,
        config.BASELINE_GAP_SHARE,
        config.DELIVERY_MODE_SHARE,
        config.FIRST_COURSE_LEVEL_SHARE,
        config.SECOND_COURSE_LEVEL_SHARE,
    ],
)
def test_shares_add_up_to_one(shares):
    assert sum(shares.values()) == pytest.approx(1.0)


# ---------- config agrees with the dictionary ----------


def test_department_keyed_settings_cover_every_department():
    codes = set(config.DEPARTMENT_CODES)
    assert set(config.DEPARTMENT_SHARE) == codes
    assert len(config.CATEGORIES) == 10
    assert len(set(config.CATEGORIES)) == 10


def test_departments_fund_less_than_they_plan():
    # Departments fund less than everyone plans. That gap is where budget
    # rejections come from (ARCHITECTURE.md 4).
    assert 0 < config.FUNDING_RATIO < 1


def test_delivery_mode_settings_match_the_enum():
    modes = set(dictionary.DELIVERY_MODE)
    assert set(config.HOURLY_RATE) == modes
    assert set(config.CAPACITY) == modes
    assert set(config.DELIVERY_MODE_SHARE) == modes
    assert max(config.CAPACITY.values()) <= dictionary.COURSE_OFFERING_TABLE.column("capacity").maximum


def test_course_level_settings_match_the_enum():
    levels = set(dictionary.COURSE_LEVEL)
    assert set(config.DURATION_RANGE) == levels
    assert set(config.PRIMARY_TARGET_LEVELS) == levels
    assert set(config.FIRST_COURSE_LEVEL_SHARE) | set(config.SECOND_COURSE_LEVEL_SHARE) == levels


def test_durations_are_whole_weeks_inside_the_dictionary_range():
    column = dictionary.COURSE_TABLE.column("duration_hours")
    for low, high in config.DURATION_RANGE.values():
        assert low % config.HOURS_PER_WEEK == 0 and high % config.HOURS_PER_WEEK == 0
        assert column.minimum <= low <= high <= column.maximum


def test_score_bands_cover_0_to_100_without_gaps():
    assert sorted(config.SCORE_BANDS) == [0, 1, 2, 3, 4, 5]
    expected_start = 0
    for level in sorted(config.SCORE_BANDS):
        low, high = config.SCORE_BANDS[level]
        assert low == expected_start and low <= high
        expected_start = high + 1
    assert expected_start == 101


# ---------- dates ----------


def test_offering_start_bounds_are_mondays():
    for day in (
        config.FIRST_OFFERING_START,
        config.LAST_OFFERING_START,
        config.NEXT_YEAR_FIRST_START,
        config.NEXT_YEAR_LAST_START,
    ):
        assert day.weekday() == 0, day


def test_dates_are_in_a_sensible_order():
    assert config.PERIOD_START <= config.PLANNING_DATE <= config.PERIOD_END
    assert config.AS_OF_DATE == config.PERIOD_END
    assert config.HIRE_DATE_TO < config.BASELINE_ASSESSMENT_FROM
    assert config.BASELINE_ASSESSMENT_TO < config.PERIOD_START
    assert config.PERIOD_START <= config.FIRST_OFFERING_START <= config.LAST_OFFERING_START <= config.PERIOD_END
    assert config.NEXT_YEAR_FIRST_START > config.PERIOD_END


def test_budget_injection_window_fits_before_the_last_offering():
    # Worst case: the last normal request is on the horizon and decided as
    # late as possible. The injected requests follow, and still need an
    # offering starting at least 7 days later.
    last_normal_decision = config.REQUEST_HORIZON + timedelta(days=config.DECISION_DELAY_DAYS[1])
    latest_request = last_normal_decision + timedelta(days=config.BUDGET_INJECTION_WINDOW_DAYS)
    assert latest_request + timedelta(days=config.MIN_REQUEST_LEAD_DAYS) <= config.LAST_OFFERING_START


def test_request_lead_respects_the_minimum():
    low, high = config.REQUEST_LEAD_DAYS
    assert config.MIN_REQUEST_LEAD_DAYS <= low <= high
    # A decision must land before the course starts.
    assert config.DECISION_DELAY_DAYS[1] < config.MIN_REQUEST_LEAD_DAYS


def test_path_limit_matches_the_dictionary():
    column = dictionary.RECOMMENDATION_TABLE.column("path_sequence")
    assert column.maximum == config.MAX_PATH_COURSES
