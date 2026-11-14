"""
The data dictionary: every table, column, type, enum and format.

This is the single source (ARCHITECTURE.md 8). It is used to:

- build sql/schema.sql,
- build docs/data_dictionary.md,
- drive the validator's enum, required, range and format checks.

So the database, the documentation and the checks cannot drift apart. If
a column changes, it changes here and nowhere else.

Only column-level facts live here (type, required, enum, range, pattern,
foreign key). Rules that span rows or tables, like "a prerequisite has a
lower level" or "committed = sum of approvals", live in rules/ and
checks/, because a dictionary entry cannot express them.

check_dictionary() checks this file against itself, and the tests run it.
"""

from dataclasses import dataclass, field

from . import config, ids

# ---------------------------------------------------------------------------
# Enums. The vocabulary of the schema.
# ---------------------------------------------------------------------------

CAREER_LEVELS = config.CAREER_LEVELS
IMPORTANCE = ("CORE", "SUPPORTING")
EMPLOYMENT_STATUS = ("ACTIVE", "ON_LEAVE")
ASSESSMENT_TYPE = ("BASELINE", "POST_COURSE")
ASSESSOR_TYPE = ("MANAGER", "SKILL_TEST")
COURSE_LEVEL = ("FOUNDATION", "INTERMEDIATE", "ADVANCED")
DELIVERY_MODE = ("ONLINE", "BLENDED", "CLASSROOM")
COURSE_STATUS = ("ACTIVE", "RETIRED")
SKILL_ROLE = ("PRIMARY", "SECONDARY")
BUDGET_STATUS = ("WITHIN_LIMIT", "EXCEEDED")
DECISION = ("RECOMMENDED", "NOT_RECOMMENDED")
RECOMMENDED_REASONS = ("CLOSES_GAP", "PREREQUISITE_FOR")
NOT_RECOMMENDED_REASONS = (
    "COURSE_UNAVAILABLE",
    "PREREQUISITE_UNAVAILABLE",
    "PATH_LIMIT",
    "OVER_BUDGET",
    "NO_SCHEDULE",
)
RECOMMENDATION_REASON = RECOMMENDED_REASONS + NOT_RECOMMENDED_REASONS
# Funding of a RECOMMENDED (proposed) step, decided when the department
# budget is allocated (BR-21). Null on NOT_RECOMMENDED rows.
FUNDING_STATUS = ("FUNDED", "NOT_FUNDED_BUDGET", "NOT_FUNDED_PREREQUISITE")
ENROLLMENT_STATUS = (
    "REQUESTED",
    "APPROVED",
    "REJECTED",
    "IN_PROGRESS",
    "COMPLETED",
    "WITHDRAWN",
)
EVENT_ACTOR = ("EMPLOYEE", "MANAGER", "HR_PARTNER", "SYSTEM")
REJECTION_REASONS = ("NO_SEATS", "BUDGET_EXHAUSTED")
WITHDRAWAL_REASONS = ("PERSONAL", "WORKLOAD")
EVENT_REASON = REJECTION_REASONS + WITHDRAWAL_REASONS
COMPLETION_RESULT = ("PASSED", "FAILED")
PLAN_STATUS = (
    "NO_GAP",
    "PLANNED",
    "NO_COURSE",
    "EMPLOYEE_ON_LEAVE",
) + NOT_RECOMMENDED_REASONS
GAP_STATUS = ("NO_GAP", "CLOSED", "OPEN")

ISSUE_TYPE = config.EDGE_CASE_TYPES
CHECK_KIND = ("STRUCTURAL", "RULE")
CHECK_STATUS = ("PASS", "FAIL")
RULE_CODES = tuple(f"BR-{n:02d}" for n in range(1, 22))

# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------

PUBLIC = "public"
EVAL = "eval"

# Kinds, as in ARCHITECTURE.md 3.1.
MASTER = "master"
BRIDGE = "bridge"
TRANSACTION = "transaction"
EVENT = "event"
DERIVED = "derived"
EVALUATION = "evaluation"


@dataclass(frozen=True)
class Column:
    name: str
    sql_type: str
    required: bool = True
    enum: tuple = None
    pattern: str = None  # a key of ids.PATTERNS
    minimum: float = None
    maximum: float = None
    references: str = None  # "table.column"
    derived: bool = False
    description: str = ""


@dataclass(frozen=True)
class Table:
    name: str
    schema: str
    kind: str
    description: str
    primary_key: tuple
    columns: tuple
    unique: tuple = field(default_factory=tuple)  # tuples of column names

    def column(self, name):
        for col in self.columns:
            if col.name == name:
                return col
        raise KeyError(f"{self.name} has no column {name!r}.")

    @property
    def column_names(self):
        return tuple(col.name for col in self.columns)


def _id(name, kind, size, *, required=True, references=None, description=""):
    """An ID column: the VARCHAR size and the format pattern always together."""
    return Column(
        name,
        f"VARCHAR({size})",
        required=required,
        pattern=kind,
        references=references,
        description=description,
    )


def _level(name, low, high, *, required=True, derived=False, description=""):
    return Column(
        name,
        "SMALLINT",
        required=required,
        minimum=low,
        maximum=high,
        derived=derived,
        description=description,
    )


def _money(name, *, required=True, minimum=0, derived=False, description=""):
    return Column(
        name,
        "NUMERIC(12,2)",
        required=required,
        minimum=minimum,
        derived=derived,
        description=description,
    )


def _date(name, *, required=True, derived=False, description=""):
    return Column(name, "DATE", required=required, derived=derived, description=description)


def _enum(name, values, size, *, required=True, derived=False, description=""):
    return Column(
        name,
        f"VARCHAR({size})",
        required=required,
        enum=tuple(values),
        derived=derived,
        description=description,
    )


# Every ID column has the same size everywhere it appears, so a foreign key
# and its target always share a type.
ROLE = ("role", 10)
SKILL = ("skill", 10)
EMPLOYEE = ("employee", 10)
COURSE = ("course", 10)
OFFERING = ("offering", 10)
ASSESSMENT = ("assessment", 10)
EVENT_ID = ("event", 10)
COMPLETION = ("completion", 16)
BUDGET = ("budget", 16)
RECOMMENDATION = ("recommendation", 30)
ENROLLMENT = ("enrollment", 30)

# ---------------------------------------------------------------------------
# Input tables (schema public)
# ---------------------------------------------------------------------------

DEPARTMENT_TABLE = Table(
    "department",
    PUBLIC,
    MASTER,
    "The eight fixed departments.",
    ("department_code",),
    (
        Column(
            "department_code",
            "CHAR(3)",
            enum=config.DEPARTMENT_CODES,
            pattern="department",
            description="Three-letter code, e.g. ENG.",
        ),
        Column("department_name", "VARCHAR(60)", description="Unique display name."),
        _enum("home_category", config.CATEGORIES, 40, description="The department's own skill category."),
    ),
    unique=(("department_name",),),
)

JOB_ROLE_TABLE = Table(
    "job_role",
    PUBLIC,
    MASTER,
    "Roles: five career levels per department, linked into a ladder. Named job_role because ROLE is a Postgres keyword.",
    ("role_id",),
    (
        _id("role_id", *ROLE),
        Column("role_title", "VARCHAR(80)", description="Unique title."),
        Column(
            "department_code",
            "CHAR(3)",
            enum=config.DEPARTMENT_CODES,
            references="department.department_code",
        ),
        _level("career_level", 1, 5),
        _id(
            "next_role_id",
            *ROLE,
            required=False,
            references="job_role.role_id",
            description="Next role up the ladder. Null only at career level 5.",
        ),
    ),
    unique=(("role_title",),),
)

SKILL_TABLE = Table(
    "skill",
    PUBLIC,
    MASTER,
    "Skills, grouped into ten categories.",
    ("skill_id",),
    (
        _id("skill_id", *SKILL),
        Column("skill_name", "VARCHAR(80)", description="Unique name."),
        _enum("skill_category", config.CATEGORIES, 40),
    ),
    unique=(("skill_name",),),
)

ROLE_SKILL_TARGET_TABLE = Table(
    "role_skill_target",
    PUBLIC,
    BRIDGE,
    "The level each role needs in each of its skills (N:M role-skill).",
    ("role_id", "skill_id"),
    (
        _id("role_id", *ROLE, references="job_role.role_id"),
        _id("skill_id", *SKILL, references="skill.skill_id"),
        _level("target_level", 1, 5),
        _enum("importance", IMPORTANCE, 10),
        _date("effective_from"),
        _date("effective_to", required=False, description="Null while the target is in force."),
    ),
)

EMPLOYEE_TABLE = Table(
    "employee",
    PUBLIC,
    MASTER,
    "Employees, their current role and the role they are working towards.",
    ("employee_id",),
    (
        _id("employee_id", *EMPLOYEE),
        Column("first_name", "VARCHAR(40)"),
        Column("last_name", "VARCHAR(40)"),
        Column(
            "department_code",
            "CHAR(3)",
            enum=config.DEPARTMENT_CODES,
            references="department.department_code",
            description="Equals the department of role_id.",
        ),
        _id("role_id", *ROLE, references="job_role.role_id", description="Current role."),
        _id(
            "target_role_id",
            *ROLE,
            references="job_role.role_id",
            description="role_id, or the role's next_role_id for a career pathway.",
        ),
        _id(
            "manager_id",
            *EMPLOYEE,
            required=False,
            references="employee.employee_id",
            description="Same department, higher level. Null only at level 5.",
        ),
        _date("hire_date"),
        _enum("employment_status", EMPLOYMENT_STATUS, 10),
    ),
)

PROFICIENCY_ASSESSMENT_TABLE = Table(
    "proficiency_assessment",
    PUBLIC,
    EVENT,
    "Append-only history of skill assessments. The score is the evidence; the level comes from the score bands.",
    ("assessment_id",),
    (
        _id("assessment_id", *ASSESSMENT),
        _id("employee_id", *EMPLOYEE, references="employee.employee_id"),
        _id("skill_id", *SKILL, references="skill.skill_id"),
        _enum("assessment_type", ASSESSMENT_TYPE, 12),
        _date("assessed_on"),
        _level("assessment_score", 0, 100),
        _level("proficiency_level", 0, 5, description="band(assessment_score), BR-15."),
        _enum("assessor_type", ASSESSOR_TYPE, 12),
        _id(
            "completion_id",
            *COMPLETION,
            required=False,
            references="completion.completion_id",
            description="Required if and only if POST_COURSE.",
        ),
    ),
)

EMPLOYEE_SKILL_TABLE = Table(
    "employee_skill",
    PUBLIC,
    BRIDGE,
    "Each employee's level in each skill of their current and target role (N:M employee-skill).",
    ("employee_id", "skill_id"),
    (
        _id("employee_id", *EMPLOYEE, references="employee.employee_id"),
        _id("skill_id", *SKILL, references="skill.skill_id"),
        _level("baseline_level", 0, 5),
        _level("current_level", 0, 5, derived=True, description="Latest assessment on or before the as-of date."),
        Column(
            "last_assessment_id",
            "VARCHAR(10)",
            pattern="assessment",
            references="proficiency_assessment.assessment_id",
            derived=True,
        ),
        _date("last_assessed_on", derived=True),
    ),
)

COURSE_TABLE = Table(
    "course",
    PUBLIC,
    MASTER,
    "The course catalog.",
    ("course_id",),
    (
        _id("course_id", *COURSE),
        Column("course_title", "VARCHAR(120)"),
        _enum("skill_category", config.CATEGORIES, 40),
        _enum("course_level", COURSE_LEVEL, 12),
        _enum("delivery_mode", DELIVERY_MODE, 10),
        _level("duration_hours", 4, 40, description="A multiple of 4."),
        _money("cost_amount", derived=True, description="duration_hours x hourly rate of the delivery mode."),
        Column("currency", "CHAR(3)", enum=(config.CURRENCY,)),
        _enum("course_status", COURSE_STATUS, 10),
    ),
    unique=(("course_title",),),
)

COURSE_SKILL_TABLE = Table(
    "course_skill",
    PUBLIC,
    BRIDGE,
    "Which skills a course teaches and up to what level (N:M course-skill).",
    ("course_id", "skill_id"),
    (
        _id("course_id", *COURSE, references="course.course_id"),
        _id("skill_id", *SKILL, references="skill.skill_id"),
        _enum("skill_role", SKILL_ROLE, 10),
        _level("target_level", 1, 5, description="The level the course can certify."),
    ),
)

COURSE_PREREQUISITE_TABLE = Table(
    "course_prerequisite",
    PUBLIC,
    BRIDGE,
    "Course prerequisites (N:M course-course). Always same category, strictly lower level.",
    ("course_id", "prerequisite_course_id"),
    (
        _id("course_id", *COURSE, references="course.course_id"),
        _id("prerequisite_course_id", *COURSE, references="course.course_id"),
    ),
)

COURSE_OFFERING_TABLE = Table(
    "course_offering",
    PUBLIC,
    MASTER,
    "Scheduled runs of a course, with seats.",
    ("offering_id",),
    (
        _id("offering_id", *OFFERING),
        _id("course_id", *COURSE, references="course.course_id"),
        _date("start_date", description="A Monday."),
        _date("end_date", derived=True, description="start + (hours / 4) x 7 - 1."),
        _level("capacity", 1, 100),
        _level("seats_planned", 0, 100, derived=True),
        _level("seats_approved", 0, 100, derived=True),
    ),
)

BUDGET_TABLE = Table(
    "budget",
    PUBLIC,
    MASTER,
    "One learning budget per department per year.",
    ("budget_id",),
    (
        _id("budget_id", *BUDGET),
        Column(
            "department_code",
            "CHAR(3)",
            enum=config.DEPARTMENT_CODES,
            references="department.department_code",
        ),
        _level("fiscal_year", config.FISCAL_YEAR, config.FISCAL_YEAR),
        _money("limit_amount"),
        _money("planned_amount", derived=True, description="Proposed demand: cost of every RECOMMENDED step."),
        _money("funded_amount", derived=True, description="Cost of the FUNDED steps. Never above the limit."),
        _money("committed_amount", derived=True, description="Cost of enrollments that reached APPROVED."),
        _money("remaining_amount", minimum=None, derived=True, description="Can be negative."),
        Column("utilization_pct", "NUMERIC(6,2)", minimum=0, derived=True),
        _enum(
            "budget_status",
            BUDGET_STATUS,
            12,
            derived=True,
            description="EXCEEDED when funded steps plus approvals outside the funded plan cost more than the limit.",
        ),
        Column("currency", "CHAR(3)", enum=(config.CURRENCY,)),
    ),
    unique=(("department_code", "fiscal_year"),),
)

RECOMMENDATION_TABLE = Table(
    "recommendation",
    PUBLIC,
    TRANSACTION,
    "The January planning run: the proposed learning path, every rejected candidate with its reason, and which proposed steps the budget funded.",
    ("recommendation_id",),
    (
        _id("recommendation_id", *RECOMMENDATION),
        _id("employee_id", *EMPLOYEE, references="employee.employee_id"),
        _id("course_id", *COURSE, references="course.course_id"),
        _id("target_skill_id", *SKILL, references="skill.skill_id"),
        _id(
            "required_for_course_id",
            *COURSE,
            required=False,
            references="course.course_id",
            description="Set only for PREREQUISITE_FOR.",
        ),
        _enum("decision", DECISION, 16),
        _enum("reason_code", RECOMMENDATION_REASON, 30),
        _level("path_sequence", 1, config.MAX_PATH_COURSES, required=False),
        _id(
            "planned_offering_id",
            *OFFERING,
            required=False,
            references="course_offering.offering_id",
            description="Required when RECOMMENDED.",
        ),
        _date("planned_start_date", required=False, derived=True),
        _date("planned_end_date", required=False, derived=True),
        _money("estimated_cost", derived=True),
        _money("cumulative_cost", required=False, derived=True),
        _enum(
            "funding_status",
            FUNDING_STATUS,
            24,
            required=False,
            description="Set on RECOMMENDED rows when the department budget is allocated (BR-21).",
        ),
        _date("planning_date"),
        _date("period_start"),
        _date("period_end"),
    ),
    unique=(("employee_id", "course_id"),),
)

ENROLLMENT_TABLE = Table(
    "enrollment",
    PUBLIC,
    TRANSACTION,
    "A request to take a course. Rejected requests are enrollments too.",
    ("enrollment_id",),
    (
        _id("enrollment_id", *ENROLLMENT),
        _id("employee_id", *EMPLOYEE, references="employee.employee_id"),
        _id("course_id", *COURSE, references="course.course_id"),
        _id("offering_id", *OFFERING, references="course_offering.offering_id"),
        _id("recommendation_id", *RECOMMENDATION, references="recommendation.recommendation_id"),
        _id("budget_id", *BUDGET, references="budget.budget_id"),
        _date("requested_on"),
        _money("cost_amount", derived=True),
        _enum("current_status", ENROLLMENT_STATUS, 12, derived=True),
        _date("last_event_on", derived=True),
    ),
    unique=(("employee_id", "course_id"),),
)

ENROLLMENT_EVENT_TABLE = Table(
    "enrollment_event",
    PUBLIC,
    EVENT,
    "Append-only status history of every enrollment.",
    ("event_id",),
    (
        _id("event_id", *EVENT_ID),
        _id("enrollment_id", *ENROLLMENT, references="enrollment.enrollment_id"),
        _level("event_seq", 1, 10),
        _enum("from_status", ENROLLMENT_STATUS, 12, required=False),
        _enum("to_status", ENROLLMENT_STATUS, 12),
        _date("event_on"),
        _enum("actor", EVENT_ACTOR, 12),
        _enum("reason_code", EVENT_REASON, 20, required=False),
    ),
    unique=(("enrollment_id", "event_seq"),),
)

COMPLETION_TABLE = Table(
    "completion",
    PUBLIC,
    EVENT,
    "Course completions. enrollment_id is deliberately not unique: a duplicate is a labelled anomaly.",
    ("completion_id",),
    (
        _id("completion_id", *COMPLETION),
        _id("enrollment_id", *ENROLLMENT, references="enrollment.enrollment_id"),
        _date("completed_on"),
        Column("attendance_pct", "NUMERIC(5,1)", minimum=0, maximum=100),
        _level("final_score", 0, 100),
        _enum("result", COMPLETION_RESULT, 8, derived=True),
    ),
)

SKILL_GAP_TABLE = Table(
    "skill_gap",
    PUBLIC,
    DERIVED,
    "Derived: every target-role skill of every employee, with the gap at planning and now.",
    ("employee_id", "skill_id"),
    (
        _id("employee_id", *EMPLOYEE, references="employee.employee_id"),
        _id("skill_id", *SKILL, references="skill.skill_id"),
        _id("target_role_id", *ROLE, references="job_role.role_id"),
        _level("target_level", 1, 5, derived=True),
        _level("planning_level", 0, 5, derived=True),
        _level("planning_gap", 0, 5, derived=True),
        _level("current_level", 0, 5, derived=True),
        _level("current_gap", 0, 5, derived=True),
        _enum("plan_status", PLAN_STATUS, 26, derived=True),
        _enum("gap_status", GAP_STATUS, 10, derived=True),
    ),
)

# ---------------------------------------------------------------------------
# Evaluation tables (schema eval). Kept apart so no input query can join
# ground truth by accident. They hold input IDs as plain text, with no
# foreign keys into public.
# ---------------------------------------------------------------------------

GROUND_TRUTH_TABLE = Table(
    "ground_truth",
    EVAL,
    EVALUATION,
    "The labelled edge cases. Never read by the detector.",
    ("case_id",),
    (
        _id("case_id", "ground_truth", 10),
        _enum("issue_type", ISSUE_TYPE, 30),
        Column("entity", "VARCHAR(40)", description="Input table holding the record."),
        Column("record_id", "VARCHAR(30)"),
        Column("employee_id", "VARCHAR(10)", pattern="employee"),
        Column("related_ids", "TEXT", required=False, description="Semicolon-separated."),
        _enum("rule_code", RULE_CODES, 6),
        Column("expected_decision", "VARCHAR(60)"),
        Column("description", "TEXT"),
    ),
    unique=(("issue_type", "record_id"),),
)

DETECTED_ISSUE_TABLE = Table(
    "detected_issue",
    EVAL,
    EVALUATION,
    "What the detector found, using input tables only.",
    ("issue_type", "record_id"),
    (
        _enum("issue_type", ISSUE_TYPE, 30),
        Column("record_id", "VARCHAR(30)"),
        _enum("rule_code", RULE_CODES, 6),
        Column("evidence", "TEXT"),
    ),
)

VALIDATION_RESULT_TABLE = Table(
    "validation_result",
    EVAL,
    EVALUATION,
    "One row per validator check.",
    ("check_id",),
    (
        Column("check_id", "VARCHAR(60)"),
        _enum("rule_code", RULE_CODES, 6, required=False),
        Column("table_name", "VARCHAR(40)"),
        _enum("kind", CHECK_KIND, 12),
        Column("failing_count", "INTEGER", minimum=0),
        Column("expected_count", "INTEGER", required=False, minimum=0),
        _enum("status", CHECK_STATUS, 4),
        Column("sample_ids", "TEXT", required=False),
    ),
)

METRIC_TABLE = Table(
    "metric",
    EVAL,
    EVALUATION,
    "Evaluation metrics. dimension is ALL or a breakdown key such as a department code.",
    ("metric_group", "metric_name", "dimension"),
    (
        Column("metric_group", "VARCHAR(40)"),
        Column("metric_name", "VARCHAR(80)"),
        Column("dimension", "VARCHAR(60)"),
        Column("value", "NUMERIC(14,4)"),
    ),
)

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

# The order tables are loaded in (ARCHITECTURE.md 8). Every foreign key
# points at an earlier table, or at its own table.
LOAD_ORDER = (
    DEPARTMENT_TABLE,
    JOB_ROLE_TABLE,
    SKILL_TABLE,
    ROLE_SKILL_TARGET_TABLE,
    EMPLOYEE_TABLE,
    COURSE_TABLE,
    COURSE_SKILL_TABLE,
    COURSE_PREREQUISITE_TABLE,
    COURSE_OFFERING_TABLE,
    BUDGET_TABLE,
    RECOMMENDATION_TABLE,
    ENROLLMENT_TABLE,
    ENROLLMENT_EVENT_TABLE,
    COMPLETION_TABLE,
    PROFICIENCY_ASSESSMENT_TABLE,
    EMPLOYEE_SKILL_TABLE,
    SKILL_GAP_TABLE,
    GROUND_TRUTH_TABLE,
    DETECTED_ISSUE_TABLE,
    VALIDATION_RESULT_TABLE,
    METRIC_TABLE,
)

TABLES = {table.name: table for table in LOAD_ORDER}

INPUT_TABLES = tuple(t.name for t in LOAD_ORDER if t.schema == PUBLIC and t.kind != DERIVED)
EXPORTED_TABLES = tuple(t.name for t in LOAD_ORDER if t.schema == PUBLIC)
EVAL_TABLES = tuple(t.name for t in LOAD_ORDER if t.schema == EVAL)


def table(name):
    if name not in TABLES:
        raise KeyError(f"No table called {name!r}.")
    return TABLES[name]


def check_dictionary():
    """
    Check the dictionary against itself and return a list of problems.

    An empty list means it is consistent. The tests call this, so a typo in a
    foreign key or a missing primary key column fails the build instead of
    turning up as a confusing error inside Postgres.
    """
    problems = []
    position = {t.name: i for i, t in enumerate(LOAD_ORDER)}

    if len(TABLES) != len(LOAD_ORDER):
        problems.append("A table name appears twice in LOAD_ORDER.")

    for t in LOAD_ORDER:
        names = t.column_names
        if len(set(names)) != len(names):
            problems.append(f"{t.name}: a column name appears twice.")

        for key in t.primary_key:
            if key not in names:
                problems.append(f"{t.name}: primary key column {key} does not exist.")
            elif not t.column(key).required:
                problems.append(f"{t.name}: primary key column {key} must be required.")

        for group in t.unique:
            for col in group:
                if col not in names:
                    problems.append(f"{t.name}: unique column {col} does not exist.")

        for col in t.columns:
            if col.pattern is not None and col.pattern not in ids.PATTERNS:
                problems.append(f"{t.name}.{col.name}: unknown id pattern {col.pattern!r}.")

            if col.enum is not None and len(set(col.enum)) != len(col.enum):
                problems.append(f"{t.name}.{col.name}: an enum value appears twice.")

            if col.enum is not None and col.sql_type.startswith("VARCHAR("):
                size = int(col.sql_type[len("VARCHAR(") : -1])
                too_long = [v for v in col.enum if len(v) > size]
                if too_long:
                    problems.append(f"{t.name}.{col.name}: {too_long} longer than {col.sql_type}.")

            if (
                col.minimum is not None
                and col.maximum is not None
                and col.minimum > col.maximum
            ):
                problems.append(f"{t.name}.{col.name}: minimum is above maximum.")

            if col.references is None:
                continue

            if t.schema == EVAL:
                problems.append(f"{t.name}.{col.name}: eval tables must not hold foreign keys.")
                continue

            target_table, _, target_column = col.references.partition(".")
            if target_table not in TABLES:
                problems.append(f"{t.name}.{col.name}: references unknown table {target_table}.")
                continue

            target = TABLES[target_table]
            if target_column not in target.column_names:
                problems.append(f"{t.name}.{col.name}: references unknown column {col.references}.")
                continue

            if target.primary_key != (target_column,):
                problems.append(
                    f"{t.name}.{col.name}: references {col.references}, which is not a "
                    "single-column primary key."
                )

            if target.column(target_column).sql_type != col.sql_type:
                problems.append(
                    f"{t.name}.{col.name} is {col.sql_type} but {col.references} is "
                    f"{target.column(target_column).sql_type}."
                )

            if position[target_table] > position[t.name]:
                problems.append(
                    f"{t.name}.{col.name}: references {target_table}, which loads later."
                )

    return problems
