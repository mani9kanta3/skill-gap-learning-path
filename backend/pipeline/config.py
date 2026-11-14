"""
Every number the generator uses, in one place.

Nothing in stages/ or rules/ should contain a magic number. If a value
decides what the data looks like, it lives here with a line saying why,
so changing the shape of the dataset means reading one file.

Two kinds of values sit here:

- Scenario values (dates, rates, shares). These are the same at every scale.
- Scale values (how many employees, skills, courses...). These live in
  SCALES, and check_scale() refuses a scale that cannot work before a
  single row is generated.

The section numbers in comments point at ARCHITECTURE.md.
"""

from dataclasses import dataclass
from datetime import date

# ---------------------------------------------------------------------------
# Seed and dates (section 0)
# ---------------------------------------------------------------------------

SEED = 20261022

FISCAL_YEAR = 2026
PERIOD_START = date(2026, 1, 1)
PERIOD_END = date(2026, 12, 31)

# The annual planning run. The plan may only use data dated on or before
# this day (BR-20).
PLANNING_DATE = date(2026, 1, 5)

# The snapshot date. Nothing in the data is dated after it.
AS_OF_DATE = date(2026, 12, 31)

# The simulation creates no normal requests after this day (5.3). It is a
# simulation setting, not a business rule.
REQUEST_HORIZON = date(2026, 11, 30)

# Baseline assessments happen in the last quarter before the year starts.
BASELINE_ASSESSMENT_FROM = date(2025, 10, 1)
BASELINE_ASSESSMENT_TO = date(2025, 12, 31)

HIRE_DATE_FROM = date(2010, 1, 1)
HIRE_DATE_TO = date(2025, 9, 30)

CURRENCY = "INR"

# ---------------------------------------------------------------------------
# Departments and skill categories (3.3)
# ---------------------------------------------------------------------------

# (code, name, home category). The order here is the order IDs follow.
DEPARTMENTS = (
    ("ENG", "Engineering", "Software Engineering"),
    ("DAT", "Data & Analytics", "Data & AI"),
    ("ITS", "IT Services", "Infrastructure & Cloud"),
    ("SAL", "Sales", "Sales"),
    ("MKT", "Marketing", "Marketing"),
    ("FIN", "Finance", "Finance"),
    ("HRM", "Human Resources", "People & HR"),
    ("OPS", "Operations", "Operations & Supply Chain"),
)
DEPARTMENT_CODES = tuple(code for code, _, _ in DEPARTMENTS)

# Every department can draw on these two.
SHARED_CATEGORIES = ("Leadership & Communication", "Digital Productivity")

# Home categories in department order, then the shared ones.
CATEGORIES = tuple(home for _, _, home in DEPARTMENTS) + SHARED_CATEGORIES

# Share of employees per department. Deliberately uneven.
DEPARTMENT_SHARE = {
    "ENG": 0.22,
    "OPS": 0.16,
    "SAL": 0.14,
    "DAT": 0.12,
    "ITS": 0.11,
    "FIN": 0.09,
    "MKT": 0.09,
    "HRM": 0.07,
}

# ---------------------------------------------------------------------------
# Roles and the career ladder (3.3, 3.5 job_role / role_skill_target)
# ---------------------------------------------------------------------------

CAREER_LEVELS = (1, 2, 3, 4, 5)
ROLES_PER_DEPARTMENT = len(CAREER_LEVELS)

# Each department's ladder list has this many skills. A level-L role targets
# the first (LADDER_BASE_SKILLS + L) of them, so level 5 targets all 10.
LADDER_SIZE = 10
LADDER_BASE_SKILLS = 5

# At most this many ladder skills come from the home category. At small
# scales the category may hold fewer, so the real number is
# min(MAX_HOME_LADDER_SKILLS, skills_per_category).
MAX_HOME_LADDER_SKILLS = 6

# The first CORE_SKILL_COUNT ladder skills are CORE, the rest SUPPORTING.
CORE_SKILL_COUNT = 4

# base_level per ladder skill is drawn from these. Target for a level-L
# role = min(5, base_level + (L - 1) // 2).
BASE_TARGET_LEVELS = (1, 2, 3)

# Share of employees at each career level.
CAREER_LEVEL_SHARE = {1: 0.35, 2: 0.30, 3: 0.20, 4: 0.10, 5: 0.05}

ON_LEAVE_SHARE = 0.05

# Share of ACTIVE employees below level 5 whose target role is the next
# role up the ladder (a career pathway).
CAREER_PATH_SHARE = 0.25

# ---------------------------------------------------------------------------
# Baseline proficiency (5.1 s03)
# ---------------------------------------------------------------------------

# For a current-role skill: level = max(0, target - d), d drawn from this.
BASELINE_GAP_SHARE = {0: 0.45, 1: 0.30, 2: 0.17, 3: 0.08}

# Skills that are only in the target role start somewhere in this range.
TARGET_ONLY_SKILL_LEVELS = (0, 1, 2)

# Share of BASELINE assessments done by a manager (the rest are skill tests).
BASELINE_MANAGER_SHARE = 0.40

# Score band per proficiency level, inclusive (3.4, BR-15).
SCORE_BANDS = {
    0: (0, 19),
    1: (20, 39),
    2: (40, 54),
    3: (55, 69),
    4: (70, 84),
    5: (85, 100),
}

# ---------------------------------------------------------------------------
# Course catalog (5.1 s04, 3.5 course / course_skill)
# ---------------------------------------------------------------------------

# Every skill gets exactly this many PRIMARY courses, so courses = 2 x skills.
PRIMARY_COURSES_PER_SKILL = 2

# Level of the first and the second primary course of a skill.
FIRST_COURSE_LEVEL_SHARE = {"FOUNDATION": 0.50, "INTERMEDIATE": 0.50}
SECOND_COURSE_LEVEL_SHARE = {"INTERMEDIATE": 0.40, "ADVANCED": 0.60}

# Each course also teaches 0 to 2 SECONDARY skills from its category.
SECONDARY_SKILLS_RANGE = (0, 2)

# target_level the course certifies for its PRIMARY skill. INTERMEDIATE is
# either 3 or 4. SECONDARY skills get PRIMARY - 1, never below 1.
PRIMARY_TARGET_LEVELS = {
    "FOUNDATION": (2,),
    "INTERMEDIATE": (3, 4),
    "ADVANCED": (5,),
}

# Allowed duration in hours per level. Always a multiple of HOURS_PER_WEEK.
DURATION_RANGE = {
    "FOUNDATION": (4, 12),
    "INTERMEDIATE": (8, 24),
    "ADVANCED": (16, 40),
}
HOURS_PER_WEEK = 4

DELIVERY_MODE_SHARE = {"ONLINE": 0.50, "BLENDED": 0.30, "CLASSROOM": 0.20}

# cost_amount = duration_hours x HOURLY_RATE[delivery_mode]
HOURLY_RATE = {"ONLINE": 600, "BLENDED": 1000, "CLASSROOM": 1500}

# Seats per offering.
CAPACITY = {"ONLINE": 100, "BLENDED": 40, "CLASSROOM": 25}

RETIRED_COURSE_SHARE = 0.04

# Prerequisite shape. Prerequisites are always the same category and a
# strictly lower level, so there can never be a cycle.
INTERMEDIATE_PREREQ_SHARE = 0.60  # gets 1 FOUNDATION prerequisite
ADVANCED_EXTRA_FOUNDATION_SHARE = 0.30  # on top of its 1 INTERMEDIATE one

# ---------------------------------------------------------------------------
# Offerings (5.1 s05)
# ---------------------------------------------------------------------------

OFFERINGS_PER_COURSE = (4, 7)
FIRST_OFFERING_START = date(2026, 1, 12)  # a Monday
LAST_OFFERING_START = date(2026, 12, 21)  # a Monday

# Share of ACTIVE courses that only run in 2027, so they are unavailable
# in the planning period (BR-04).
NEXT_YEAR_ONLY_SHARE = 0.10
NEXT_YEAR_OFFERINGS = (1, 2)
NEXT_YEAR_FIRST_START = date(2027, 1, 11)  # a Monday
NEXT_YEAR_LAST_START = date(2027, 6, 28)  # a Monday

# ---------------------------------------------------------------------------
# Planning rules (4, 5.2)
# ---------------------------------------------------------------------------

MAX_PATH_COURSES = 4  # BR-07
SCHEDULE_GAP_DAYS = 14  # BR-08: planning date -> step 1, and between steps

# BR-09(a): the most one employee's plan may cost in a year.
LEARNING_ALLOWANCE_PER_EMPLOYEE = 60_000

# Budgets work in two steps (ARCHITECTURE.md 4, "Proposed and funded"):
#
# 1. The January run produces a PROPOSED plan: every path is feasible on
#    dates, seats, prerequisites and the employee's allowance.
# 2. Each department's limit is set to FUNDING_RATIO x its proposed
#    demand, rounded up to BUDGET_ROUNDING, and the limit is then
#    allocated to individual proposed steps, everyone's first step first. Steps
#    that get money are FUNDED; the rest are NOT_FUNDED. That is the
#    FUNDED plan, and only funded steps can be approved (BR-11).
#
# Below 1 on purpose: a department funds less than its people propose.
# A ratio rather than a fixed amount per head, because proposed demand
# per head differs a lot between departments, and a ratio puts every
# department under the same pressure at every scale.
FUNDING_RATIO = 0.85
BUDGET_ROUNDING = 10_000

# ---------------------------------------------------------------------------
# Simulation (5.3)
# ---------------------------------------------------------------------------

REQUEST_PROBABILITY = 0.95  # for a FUNDED step
# Some employees ask for a step the budget did not fund. HR rejects it
# (BUDGET_EXHAUSTED); that is the normal budget exception path.
UNFUNDED_REQUEST_PROBABILITY = 0.50
REQUEST_LEAD_DAYS = (7, 21)  # requested_on = planned_start - U{7..21}
MIN_REQUEST_LEAD_DAYS = 7  # requested_on <= start - 7 always
DECISION_DELAY_DAYS = (1, 5)
WITHDRAW_PROBABILITY = 0.05
REASSESSMENT_DELAY_DAYS = (3, 14)  # BR-17

# Completion result (BR-14).
PASS_MIN_ATTENDANCE = 75.0
PASS_MIN_SCORE = 60

# final_score ~ Normal(mean, FINAL_SCORE_SD), where
# mean = clamp(BASE + STEP x (pre_level - entry_level), MIN, MAX)
FINAL_SCORE_BASE_MEAN = 70
FINAL_SCORE_STEP = 6
FINAL_SCORE_MEAN_RANGE = (50, 85)
FINAL_SCORE_SD = 12

# attendance_pct = round(100 x Beta(a, b), 1)
ATTENDANCE_BETA = (10.0, 1.0)

# Post-course score uplift (BR-16):
# PASSED: UPLIFT_PASSED x (final_score - UPLIFT_FLOOR)
# FAILED: UPLIFT_FAILED x max(0, final_score - UPLIFT_FLOOR)
UPLIFT_PASSED = 0.8
UPLIFT_FAILED = 0.3
UPLIFT_FLOOR = 40
POST_SCORE_NOISE_SD = 5

# ---------------------------------------------------------------------------
# Scales (0, 3.3)
# ---------------------------------------------------------------------------


class ScaleError(ValueError):
    """A scale that cannot produce a valid dataset. Raised before any data exists."""


@dataclass(frozen=True)
class Scale:
    """The counts that change between starter and full. Everything else is shared."""

    name: str
    employees: int
    skills: int
    courses: int
    enrollments: int
    edge_cases_per_type: int


FULL = Scale(
    name="full",
    employees=5000,
    skills=500,
    courses=1000,
    enrollments=10000,
    edge_cases_per_type=50,
)

STARTER_FRACTION = 0.10

# Starter is computed from full, not typed in, so the two can never drift.
# Departments and roles stay fixed: they are reference data, not volume.
STARTER = Scale(
    name="starter",
    employees=round(FULL.employees * STARTER_FRACTION),
    skills=round(FULL.skills * STARTER_FRACTION),
    courses=round(FULL.courses * STARTER_FRACTION),
    enrollments=round(FULL.enrollments * STARTER_FRACTION),
    edge_cases_per_type=round(FULL.edge_cases_per_type * STARTER_FRACTION),
)

SCALES = {FULL.name: FULL, STARTER.name: STARTER}

# The five labelled edge-case types (6). BUDGET_EXCEEDED is the only one
# that adds enrollment rows.
EDGE_CASE_TYPES = (
    "PREREQUISITE_VIOLATION",
    "COURSE_UNAVAILABLE",
    "BUDGET_EXCEEDED",
    "DUPLICATE_COMPLETION",
    "GAP_NOT_REASSESSED",
)


@dataclass(frozen=True)
class ScalePlan:
    """The numbers every stage needs, worked out once from a Scale."""

    scale: Scale
    skills_per_category: int
    home_ladder_skills: int
    shared_ladder_skills: int
    injected_enrollments: int
    baseline_enrollments: int
    smallest_department: int


def get_scale(name):
    """Look a scale up by name, with an error that lists the real ones."""
    if name not in SCALES:
        raise ScaleError(f"Unknown scale {name!r}. Use one of: {', '.join(sorted(SCALES))}.")
    return SCALES[name]


def check_scale(scale):
    """
    Work out the derived numbers for a scale, or refuse it.

    Every problem found is collected first and reported together, so a
    bad scale shows all its faults in one message instead of one per run.
    The candidate pools for the edge cases are counted again in s09,
    because they depend on the generated data.
    """
    problems = []

    if scale.skills % len(CATEGORIES) != 0:
        problems.append(
            f"skills ({scale.skills}) must divide evenly into {len(CATEGORIES)} categories."
        )
    skills_per_category = scale.skills // len(CATEGORIES)

    # The 3.3 rule: as many home skills as the category allows, up to 6.
    home = min(MAX_HOME_LADDER_SKILLS, skills_per_category)
    shared = LADDER_SIZE - home
    shared_pool = skills_per_category * len(SHARED_CATEGORIES)

    if home < CORE_SKILL_COUNT:
        problems.append(
            f"only {home} home skills fit in a ladder, but the first {CORE_SKILL_COUNT} "
            f"ladder skills are CORE. Need at least {CORE_SKILL_COUNT} skills per category."
        )
    if shared > shared_pool:
        problems.append(
            f"a ladder needs {shared} shared skills but the shared categories only hold "
            f"{shared_pool}."
        )

    expected_courses = scale.skills * PRIMARY_COURSES_PER_SKILL
    if scale.courses != expected_courses:
        problems.append(
            f"courses ({scale.courses}) must be {PRIMARY_COURSES_PER_SKILL} x skills "
            f"= {expected_courses}."
        )

    # Every department needs at least one employee at every career level,
    # otherwise someone at level L has no possible manager at level L + 1.
    smallest_department = min(
        int(scale.employees * share) for share in DEPARTMENT_SHARE.values()
    )
    if smallest_department < ROLES_PER_DEPARTMENT:
        problems.append(
            f"the smallest department gets {smallest_department} employees, fewer than "
            f"the {ROLES_PER_DEPARTMENT} career levels it must staff."
        )

    if scale.edge_cases_per_type < 1:
        problems.append("edge_cases_per_type must be at least 1.")

    injected = scale.edge_cases_per_type  # only BUDGET_EXCEEDED adds enrollments
    baseline = scale.enrollments - injected
    if baseline < 1:
        problems.append(
            f"enrollments ({scale.enrollments}) must be larger than the "
            f"{injected} injected budget cases."
        )

    if problems:
        raise ScaleError(
            f"Scale {scale.name!r} cannot work:\n- " + "\n- ".join(problems)
        )

    return ScalePlan(
        scale=scale,
        skills_per_category=skills_per_category,
        home_ladder_skills=home,
        shared_ladder_skills=shared,
        injected_enrollments=injected,
        baseline_enrollments=baseline,
        smallest_department=smallest_department,
    )
