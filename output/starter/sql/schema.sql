-- Generated from pipeline/dictionary.py. Do not edit by hand.
CREATE SCHEMA IF NOT EXISTS eval;

CREATE TABLE IF NOT EXISTS public.department (
    department_code CHAR(3) NOT NULL,
    department_name VARCHAR(60) NOT NULL,
    home_category VARCHAR(40) NOT NULL,
    PRIMARY KEY (department_code),
    UNIQUE (department_name),
    CHECK (department_code IN ('ENG', 'DAT', 'ITS', 'SAL', 'MKT', 'FIN', 'HRM', 'OPS')),
    CHECK (department_code ~ '^[A-Z]{3}$'),
    CHECK (home_category IN ('Software Engineering', 'Data & AI', 'Infrastructure & Cloud', 'Sales', 'Marketing', 'Finance', 'People & HR', 'Operations & Supply Chain', 'Leadership & Communication', 'Digital Productivity'))
);
COMMENT ON TABLE public.department IS 'The eight fixed departments.';

CREATE TABLE IF NOT EXISTS public.job_role (
    role_id VARCHAR(10) NOT NULL,
    role_title VARCHAR(80) NOT NULL,
    department_code CHAR(3) NOT NULL,
    career_level SMALLINT NOT NULL,
    next_role_id VARCHAR(10),
    PRIMARY KEY (role_id),
    UNIQUE (role_title),
    CHECK (role_id ~ '^ROL-[0-9]{6}$'),
    CHECK (department_code IN ('ENG', 'DAT', 'ITS', 'SAL', 'MKT', 'FIN', 'HRM', 'OPS')),
    CHECK (career_level >= 1),
    CHECK (career_level <= 5),
    CHECK (next_role_id ~ '^ROL-[0-9]{6}$'),
    FOREIGN KEY (department_code) REFERENCES public.department (department_code) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (next_role_id) REFERENCES public.job_role (role_id) DEFERRABLE INITIALLY DEFERRED
);
COMMENT ON TABLE public.job_role IS 'Roles: five career levels per department, linked into a ladder. Named job_role because ROLE is a Postgres keyword.';

CREATE TABLE IF NOT EXISTS public.skill (
    skill_id VARCHAR(10) NOT NULL,
    skill_name VARCHAR(80) NOT NULL,
    skill_category VARCHAR(40) NOT NULL,
    PRIMARY KEY (skill_id),
    UNIQUE (skill_name),
    CHECK (skill_id ~ '^SKL-[0-9]{6}$'),
    CHECK (skill_category IN ('Software Engineering', 'Data & AI', 'Infrastructure & Cloud', 'Sales', 'Marketing', 'Finance', 'People & HR', 'Operations & Supply Chain', 'Leadership & Communication', 'Digital Productivity'))
);
COMMENT ON TABLE public.skill IS 'Skills, grouped into ten categories.';

CREATE TABLE IF NOT EXISTS public.role_skill_target (
    role_id VARCHAR(10) NOT NULL,
    skill_id VARCHAR(10) NOT NULL,
    target_level SMALLINT NOT NULL,
    importance VARCHAR(10) NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE,
    PRIMARY KEY (role_id, skill_id),
    CHECK (role_id ~ '^ROL-[0-9]{6}$'),
    CHECK (skill_id ~ '^SKL-[0-9]{6}$'),
    CHECK (target_level >= 1),
    CHECK (target_level <= 5),
    CHECK (importance IN ('CORE', 'SUPPORTING')),
    FOREIGN KEY (role_id) REFERENCES public.job_role (role_id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (skill_id) REFERENCES public.skill (skill_id) DEFERRABLE INITIALLY DEFERRED
);
COMMENT ON TABLE public.role_skill_target IS 'The level each role needs in each of its skills (N:M role-skill).';

CREATE TABLE IF NOT EXISTS public.employee (
    employee_id VARCHAR(10) NOT NULL,
    first_name VARCHAR(40) NOT NULL,
    last_name VARCHAR(40) NOT NULL,
    department_code CHAR(3) NOT NULL,
    role_id VARCHAR(10) NOT NULL,
    target_role_id VARCHAR(10) NOT NULL,
    manager_id VARCHAR(10),
    hire_date DATE NOT NULL,
    employment_status VARCHAR(10) NOT NULL,
    PRIMARY KEY (employee_id),
    CHECK (employee_id ~ '^EMP-[0-9]{6}$'),
    CHECK (department_code IN ('ENG', 'DAT', 'ITS', 'SAL', 'MKT', 'FIN', 'HRM', 'OPS')),
    CHECK (role_id ~ '^ROL-[0-9]{6}$'),
    CHECK (target_role_id ~ '^ROL-[0-9]{6}$'),
    CHECK (manager_id ~ '^EMP-[0-9]{6}$'),
    CHECK (employment_status IN ('ACTIVE', 'ON_LEAVE')),
    FOREIGN KEY (department_code) REFERENCES public.department (department_code) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (role_id) REFERENCES public.job_role (role_id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (target_role_id) REFERENCES public.job_role (role_id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (manager_id) REFERENCES public.employee (employee_id) DEFERRABLE INITIALLY DEFERRED
);
COMMENT ON TABLE public.employee IS 'Employees, their current role and the role they are working towards.';

CREATE TABLE IF NOT EXISTS public.course (
    course_id VARCHAR(10) NOT NULL,
    course_title VARCHAR(120) NOT NULL,
    skill_category VARCHAR(40) NOT NULL,
    course_level VARCHAR(12) NOT NULL,
    delivery_mode VARCHAR(10) NOT NULL,
    duration_hours SMALLINT NOT NULL,
    cost_amount NUMERIC(12,2) NOT NULL,
    currency CHAR(3) NOT NULL,
    course_status VARCHAR(10) NOT NULL,
    PRIMARY KEY (course_id),
    UNIQUE (course_title),
    CHECK (course_id ~ '^CRS-[0-9]{6}$'),
    CHECK (skill_category IN ('Software Engineering', 'Data & AI', 'Infrastructure & Cloud', 'Sales', 'Marketing', 'Finance', 'People & HR', 'Operations & Supply Chain', 'Leadership & Communication', 'Digital Productivity')),
    CHECK (course_level IN ('FOUNDATION', 'INTERMEDIATE', 'ADVANCED')),
    CHECK (delivery_mode IN ('ONLINE', 'BLENDED', 'CLASSROOM')),
    CHECK (duration_hours >= 4),
    CHECK (duration_hours <= 40),
    CHECK (cost_amount >= 0),
    CHECK (currency IN ('INR')),
    CHECK (course_status IN ('ACTIVE', 'RETIRED'))
);
COMMENT ON TABLE public.course IS 'The course catalog.';

CREATE TABLE IF NOT EXISTS public.course_skill (
    course_id VARCHAR(10) NOT NULL,
    skill_id VARCHAR(10) NOT NULL,
    skill_role VARCHAR(10) NOT NULL,
    target_level SMALLINT NOT NULL,
    PRIMARY KEY (course_id, skill_id),
    CHECK (course_id ~ '^CRS-[0-9]{6}$'),
    CHECK (skill_id ~ '^SKL-[0-9]{6}$'),
    CHECK (skill_role IN ('PRIMARY', 'SECONDARY')),
    CHECK (target_level >= 1),
    CHECK (target_level <= 5),
    FOREIGN KEY (course_id) REFERENCES public.course (course_id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (skill_id) REFERENCES public.skill (skill_id) DEFERRABLE INITIALLY DEFERRED
);
COMMENT ON TABLE public.course_skill IS 'Which skills a course teaches and up to what level (N:M course-skill).';

CREATE TABLE IF NOT EXISTS public.course_prerequisite (
    course_id VARCHAR(10) NOT NULL,
    prerequisite_course_id VARCHAR(10) NOT NULL,
    PRIMARY KEY (course_id, prerequisite_course_id),
    CHECK (course_id ~ '^CRS-[0-9]{6}$'),
    CHECK (prerequisite_course_id ~ '^CRS-[0-9]{6}$'),
    FOREIGN KEY (course_id) REFERENCES public.course (course_id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (prerequisite_course_id) REFERENCES public.course (course_id) DEFERRABLE INITIALLY DEFERRED
);
COMMENT ON TABLE public.course_prerequisite IS 'Course prerequisites (N:M course-course). Always same category, strictly lower level.';

CREATE TABLE IF NOT EXISTS public.course_offering (
    offering_id VARCHAR(10) NOT NULL,
    course_id VARCHAR(10) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    capacity SMALLINT NOT NULL,
    seats_planned SMALLINT NOT NULL,
    seats_approved SMALLINT NOT NULL,
    PRIMARY KEY (offering_id),
    CHECK (offering_id ~ '^OFF-[0-9]{6}$'),
    CHECK (course_id ~ '^CRS-[0-9]{6}$'),
    CHECK (capacity >= 1),
    CHECK (capacity <= 100),
    CHECK (seats_planned >= 0),
    CHECK (seats_planned <= 100),
    CHECK (seats_approved >= 0),
    CHECK (seats_approved <= 100),
    FOREIGN KEY (course_id) REFERENCES public.course (course_id) DEFERRABLE INITIALLY DEFERRED
);
COMMENT ON TABLE public.course_offering IS 'Scheduled runs of a course, with seats.';

CREATE TABLE IF NOT EXISTS public.budget (
    budget_id VARCHAR(16) NOT NULL,
    department_code CHAR(3) NOT NULL,
    fiscal_year SMALLINT NOT NULL,
    limit_amount NUMERIC(12,2) NOT NULL,
    planned_amount NUMERIC(12,2) NOT NULL,
    funded_amount NUMERIC(12,2) NOT NULL,
    committed_amount NUMERIC(12,2) NOT NULL,
    remaining_amount NUMERIC(12,2) NOT NULL,
    utilization_pct NUMERIC(6,2) NOT NULL,
    budget_status VARCHAR(12) NOT NULL,
    currency CHAR(3) NOT NULL,
    PRIMARY KEY (budget_id),
    UNIQUE (department_code, fiscal_year),
    CHECK (budget_id ~ '^BUD-[A-Z]{3}-[0-9]{4}$'),
    CHECK (department_code IN ('ENG', 'DAT', 'ITS', 'SAL', 'MKT', 'FIN', 'HRM', 'OPS')),
    CHECK (fiscal_year >= 2026),
    CHECK (fiscal_year <= 2026),
    CHECK (limit_amount >= 0),
    CHECK (planned_amount >= 0),
    CHECK (funded_amount >= 0),
    CHECK (committed_amount >= 0),
    CHECK (utilization_pct >= 0),
    CHECK (budget_status IN ('WITHIN_LIMIT', 'EXCEEDED')),
    CHECK (currency IN ('INR')),
    FOREIGN KEY (department_code) REFERENCES public.department (department_code) DEFERRABLE INITIALLY DEFERRED
);
COMMENT ON TABLE public.budget IS 'One learning budget per department per year.';

CREATE TABLE IF NOT EXISTS public.recommendation (
    recommendation_id VARCHAR(30) NOT NULL,
    employee_id VARCHAR(10) NOT NULL,
    course_id VARCHAR(10) NOT NULL,
    target_skill_id VARCHAR(10) NOT NULL,
    required_for_course_id VARCHAR(10),
    decision VARCHAR(16) NOT NULL,
    reason_code VARCHAR(30) NOT NULL,
    path_sequence SMALLINT,
    planned_offering_id VARCHAR(10),
    planned_start_date DATE,
    planned_end_date DATE,
    estimated_cost NUMERIC(12,2) NOT NULL,
    cumulative_cost NUMERIC(12,2),
    funding_status VARCHAR(24),
    planning_date DATE NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    PRIMARY KEY (recommendation_id),
    UNIQUE (employee_id, course_id),
    CHECK (recommendation_id ~ '^REC-EMP-[0-9]{6}-CRS-[0-9]{6}$'),
    CHECK (employee_id ~ '^EMP-[0-9]{6}$'),
    CHECK (course_id ~ '^CRS-[0-9]{6}$'),
    CHECK (target_skill_id ~ '^SKL-[0-9]{6}$'),
    CHECK (required_for_course_id ~ '^CRS-[0-9]{6}$'),
    CHECK (decision IN ('RECOMMENDED', 'NOT_RECOMMENDED')),
    CHECK (reason_code IN ('CLOSES_GAP', 'PREREQUISITE_FOR', 'COURSE_UNAVAILABLE', 'PREREQUISITE_UNAVAILABLE', 'PATH_LIMIT', 'OVER_BUDGET', 'NO_SCHEDULE')),
    CHECK (path_sequence >= 1),
    CHECK (path_sequence <= 4),
    CHECK (planned_offering_id ~ '^OFF-[0-9]{6}$'),
    CHECK (estimated_cost >= 0),
    CHECK (cumulative_cost >= 0),
    CHECK (funding_status IN ('FUNDED', 'NOT_FUNDED_BUDGET', 'NOT_FUNDED_PREREQUISITE')),
    FOREIGN KEY (employee_id) REFERENCES public.employee (employee_id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (course_id) REFERENCES public.course (course_id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (target_skill_id) REFERENCES public.skill (skill_id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (required_for_course_id) REFERENCES public.course (course_id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (planned_offering_id) REFERENCES public.course_offering (offering_id) DEFERRABLE INITIALLY DEFERRED
);
COMMENT ON TABLE public.recommendation IS 'The January planning run: the proposed learning path, every rejected candidate with its reason, and which proposed steps the budget funded.';

CREATE TABLE IF NOT EXISTS public.enrollment (
    enrollment_id VARCHAR(30) NOT NULL,
    employee_id VARCHAR(10) NOT NULL,
    course_id VARCHAR(10) NOT NULL,
    offering_id VARCHAR(10) NOT NULL,
    recommendation_id VARCHAR(30) NOT NULL,
    budget_id VARCHAR(16) NOT NULL,
    requested_on DATE NOT NULL,
    cost_amount NUMERIC(12,2) NOT NULL,
    current_status VARCHAR(12) NOT NULL,
    last_event_on DATE NOT NULL,
    PRIMARY KEY (enrollment_id),
    UNIQUE (employee_id, course_id),
    CHECK (enrollment_id ~ '^ENR-EMP-[0-9]{6}-CRS-[0-9]{6}$'),
    CHECK (employee_id ~ '^EMP-[0-9]{6}$'),
    CHECK (course_id ~ '^CRS-[0-9]{6}$'),
    CHECK (offering_id ~ '^OFF-[0-9]{6}$'),
    CHECK (recommendation_id ~ '^REC-EMP-[0-9]{6}-CRS-[0-9]{6}$'),
    CHECK (budget_id ~ '^BUD-[A-Z]{3}-[0-9]{4}$'),
    CHECK (cost_amount >= 0),
    CHECK (current_status IN ('REQUESTED', 'APPROVED', 'REJECTED', 'IN_PROGRESS', 'COMPLETED', 'WITHDRAWN')),
    FOREIGN KEY (employee_id) REFERENCES public.employee (employee_id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (course_id) REFERENCES public.course (course_id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (offering_id) REFERENCES public.course_offering (offering_id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (recommendation_id) REFERENCES public.recommendation (recommendation_id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (budget_id) REFERENCES public.budget (budget_id) DEFERRABLE INITIALLY DEFERRED
);
COMMENT ON TABLE public.enrollment IS 'A request to take a course. Rejected requests are enrollments too.';

CREATE TABLE IF NOT EXISTS public.enrollment_event (
    event_id VARCHAR(10) NOT NULL,
    enrollment_id VARCHAR(30) NOT NULL,
    event_seq SMALLINT NOT NULL,
    from_status VARCHAR(12),
    to_status VARCHAR(12) NOT NULL,
    event_on DATE NOT NULL,
    actor VARCHAR(12) NOT NULL,
    reason_code VARCHAR(20),
    PRIMARY KEY (event_id),
    UNIQUE (enrollment_id, event_seq),
    CHECK (event_id ~ '^EVT-[0-9]{6}$'),
    CHECK (enrollment_id ~ '^ENR-EMP-[0-9]{6}-CRS-[0-9]{6}$'),
    CHECK (event_seq >= 1),
    CHECK (event_seq <= 10),
    CHECK (from_status IN ('REQUESTED', 'APPROVED', 'REJECTED', 'IN_PROGRESS', 'COMPLETED', 'WITHDRAWN')),
    CHECK (to_status IN ('REQUESTED', 'APPROVED', 'REJECTED', 'IN_PROGRESS', 'COMPLETED', 'WITHDRAWN')),
    CHECK (actor IN ('EMPLOYEE', 'MANAGER', 'HR_PARTNER', 'SYSTEM')),
    CHECK (reason_code IN ('NO_SEATS', 'BUDGET_EXHAUSTED', 'PERSONAL', 'WORKLOAD')),
    FOREIGN KEY (enrollment_id) REFERENCES public.enrollment (enrollment_id) DEFERRABLE INITIALLY DEFERRED
);
COMMENT ON TABLE public.enrollment_event IS 'Append-only status history of every enrollment.';

CREATE TABLE IF NOT EXISTS public.completion (
    completion_id VARCHAR(16) NOT NULL,
    enrollment_id VARCHAR(30) NOT NULL,
    completed_on DATE NOT NULL,
    attendance_pct NUMERIC(5,1) NOT NULL,
    final_score SMALLINT NOT NULL,
    result VARCHAR(8) NOT NULL,
    PRIMARY KEY (completion_id),
    CHECK (completion_id ~ '^CMP-[0-9]{4}-[0-9]{6}$'),
    CHECK (enrollment_id ~ '^ENR-EMP-[0-9]{6}-CRS-[0-9]{6}$'),
    CHECK (attendance_pct >= 0),
    CHECK (attendance_pct <= 100),
    CHECK (final_score >= 0),
    CHECK (final_score <= 100),
    CHECK (result IN ('PASSED', 'FAILED')),
    FOREIGN KEY (enrollment_id) REFERENCES public.enrollment (enrollment_id) DEFERRABLE INITIALLY DEFERRED
);
COMMENT ON TABLE public.completion IS 'Course completions. enrollment_id is deliberately not unique: a duplicate is a labelled anomaly.';

CREATE TABLE IF NOT EXISTS public.proficiency_assessment (
    assessment_id VARCHAR(10) NOT NULL,
    employee_id VARCHAR(10) NOT NULL,
    skill_id VARCHAR(10) NOT NULL,
    assessment_type VARCHAR(12) NOT NULL,
    assessed_on DATE NOT NULL,
    assessment_score SMALLINT NOT NULL,
    proficiency_level SMALLINT NOT NULL,
    assessor_type VARCHAR(12) NOT NULL,
    completion_id VARCHAR(16),
    PRIMARY KEY (assessment_id),
    CHECK (assessment_id ~ '^ASM-[0-9]{6}$'),
    CHECK (employee_id ~ '^EMP-[0-9]{6}$'),
    CHECK (skill_id ~ '^SKL-[0-9]{6}$'),
    CHECK (assessment_type IN ('BASELINE', 'POST_COURSE')),
    CHECK (assessment_score >= 0),
    CHECK (assessment_score <= 100),
    CHECK (proficiency_level >= 0),
    CHECK (proficiency_level <= 5),
    CHECK (assessor_type IN ('MANAGER', 'SKILL_TEST')),
    CHECK (completion_id ~ '^CMP-[0-9]{4}-[0-9]{6}$'),
    FOREIGN KEY (employee_id) REFERENCES public.employee (employee_id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (skill_id) REFERENCES public.skill (skill_id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (completion_id) REFERENCES public.completion (completion_id) DEFERRABLE INITIALLY DEFERRED
);
COMMENT ON TABLE public.proficiency_assessment IS 'Append-only history of skill assessments. The score is the evidence; the level comes from the score bands.';

CREATE TABLE IF NOT EXISTS public.employee_skill (
    employee_id VARCHAR(10) NOT NULL,
    skill_id VARCHAR(10) NOT NULL,
    baseline_level SMALLINT NOT NULL,
    current_level SMALLINT NOT NULL,
    last_assessment_id VARCHAR(10) NOT NULL,
    last_assessed_on DATE NOT NULL,
    PRIMARY KEY (employee_id, skill_id),
    CHECK (employee_id ~ '^EMP-[0-9]{6}$'),
    CHECK (skill_id ~ '^SKL-[0-9]{6}$'),
    CHECK (baseline_level >= 0),
    CHECK (baseline_level <= 5),
    CHECK (current_level >= 0),
    CHECK (current_level <= 5),
    CHECK (last_assessment_id ~ '^ASM-[0-9]{6}$'),
    FOREIGN KEY (employee_id) REFERENCES public.employee (employee_id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (skill_id) REFERENCES public.skill (skill_id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (last_assessment_id) REFERENCES public.proficiency_assessment (assessment_id) DEFERRABLE INITIALLY DEFERRED
);
COMMENT ON TABLE public.employee_skill IS 'Each employee''s level in each skill of their current and target role (N:M employee-skill).';

CREATE TABLE IF NOT EXISTS public.skill_gap (
    employee_id VARCHAR(10) NOT NULL,
    skill_id VARCHAR(10) NOT NULL,
    target_role_id VARCHAR(10) NOT NULL,
    target_level SMALLINT NOT NULL,
    planning_level SMALLINT NOT NULL,
    planning_gap SMALLINT NOT NULL,
    current_level SMALLINT NOT NULL,
    current_gap SMALLINT NOT NULL,
    plan_status VARCHAR(26) NOT NULL,
    gap_status VARCHAR(10) NOT NULL,
    PRIMARY KEY (employee_id, skill_id),
    CHECK (employee_id ~ '^EMP-[0-9]{6}$'),
    CHECK (skill_id ~ '^SKL-[0-9]{6}$'),
    CHECK (target_role_id ~ '^ROL-[0-9]{6}$'),
    CHECK (target_level >= 1),
    CHECK (target_level <= 5),
    CHECK (planning_level >= 0),
    CHECK (planning_level <= 5),
    CHECK (planning_gap >= 0),
    CHECK (planning_gap <= 5),
    CHECK (current_level >= 0),
    CHECK (current_level <= 5),
    CHECK (current_gap >= 0),
    CHECK (current_gap <= 5),
    CHECK (plan_status IN ('NO_GAP', 'PLANNED', 'NO_COURSE', 'EMPLOYEE_ON_LEAVE', 'COURSE_UNAVAILABLE', 'PREREQUISITE_UNAVAILABLE', 'PATH_LIMIT', 'OVER_BUDGET', 'NO_SCHEDULE')),
    CHECK (gap_status IN ('NO_GAP', 'CLOSED', 'OPEN')),
    FOREIGN KEY (employee_id) REFERENCES public.employee (employee_id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (skill_id) REFERENCES public.skill (skill_id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (target_role_id) REFERENCES public.job_role (role_id) DEFERRABLE INITIALLY DEFERRED
);
COMMENT ON TABLE public.skill_gap IS 'Derived: every target-role skill of every employee, with the gap at planning and now.';

CREATE TABLE IF NOT EXISTS eval.ground_truth (
    case_id VARCHAR(10) NOT NULL,
    issue_type VARCHAR(30) NOT NULL,
    entity VARCHAR(40) NOT NULL,
    record_id VARCHAR(30) NOT NULL,
    employee_id VARCHAR(10) NOT NULL,
    related_ids TEXT,
    rule_code VARCHAR(6) NOT NULL,
    expected_decision VARCHAR(60) NOT NULL,
    description TEXT NOT NULL,
    PRIMARY KEY (case_id),
    UNIQUE (issue_type, record_id),
    CHECK (case_id ~ '^GT-[0-9]{6}$'),
    CHECK (issue_type IN ('PREREQUISITE_VIOLATION', 'COURSE_UNAVAILABLE', 'BUDGET_EXCEEDED', 'DUPLICATE_COMPLETION', 'GAP_NOT_REASSESSED')),
    CHECK (employee_id ~ '^EMP-[0-9]{6}$'),
    CHECK (rule_code IN ('BR-01', 'BR-02', 'BR-03', 'BR-04', 'BR-05', 'BR-06', 'BR-07', 'BR-08', 'BR-09', 'BR-10', 'BR-11', 'BR-12', 'BR-13', 'BR-14', 'BR-15', 'BR-16', 'BR-17', 'BR-18', 'BR-19', 'BR-20', 'BR-21'))
);
COMMENT ON TABLE eval.ground_truth IS 'The labelled edge cases. Never read by the detector.';

CREATE TABLE IF NOT EXISTS eval.detected_issue (
    issue_type VARCHAR(30) NOT NULL,
    record_id VARCHAR(30) NOT NULL,
    rule_code VARCHAR(6) NOT NULL,
    evidence TEXT NOT NULL,
    PRIMARY KEY (issue_type, record_id),
    CHECK (issue_type IN ('PREREQUISITE_VIOLATION', 'COURSE_UNAVAILABLE', 'BUDGET_EXCEEDED', 'DUPLICATE_COMPLETION', 'GAP_NOT_REASSESSED')),
    CHECK (rule_code IN ('BR-01', 'BR-02', 'BR-03', 'BR-04', 'BR-05', 'BR-06', 'BR-07', 'BR-08', 'BR-09', 'BR-10', 'BR-11', 'BR-12', 'BR-13', 'BR-14', 'BR-15', 'BR-16', 'BR-17', 'BR-18', 'BR-19', 'BR-20', 'BR-21'))
);
COMMENT ON TABLE eval.detected_issue IS 'What the detector found, using input tables only.';

CREATE TABLE IF NOT EXISTS eval.validation_result (
    check_id VARCHAR(60) NOT NULL,
    rule_code VARCHAR(6),
    table_name VARCHAR(40) NOT NULL,
    kind VARCHAR(12) NOT NULL,
    failing_count INTEGER NOT NULL,
    expected_count INTEGER,
    status VARCHAR(4) NOT NULL,
    sample_ids TEXT,
    PRIMARY KEY (check_id),
    CHECK (rule_code IN ('BR-01', 'BR-02', 'BR-03', 'BR-04', 'BR-05', 'BR-06', 'BR-07', 'BR-08', 'BR-09', 'BR-10', 'BR-11', 'BR-12', 'BR-13', 'BR-14', 'BR-15', 'BR-16', 'BR-17', 'BR-18', 'BR-19', 'BR-20', 'BR-21')),
    CHECK (kind IN ('STRUCTURAL', 'RULE')),
    CHECK (failing_count >= 0),
    CHECK (expected_count >= 0),
    CHECK (status IN ('PASS', 'FAIL'))
);
COMMENT ON TABLE eval.validation_result IS 'One row per validator check.';

CREATE TABLE IF NOT EXISTS eval.metric (
    metric_group VARCHAR(40) NOT NULL,
    metric_name VARCHAR(80) NOT NULL,
    dimension VARCHAR(60) NOT NULL,
    value NUMERIC(14,4) NOT NULL,
    PRIMARY KEY (metric_group, metric_name, dimension)
);
COMMENT ON TABLE eval.metric IS 'Evaluation metrics. dimension is ALL or a breakdown key such as a department code.';
