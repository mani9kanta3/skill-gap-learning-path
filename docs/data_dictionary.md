# Data dictionary

Generated from `backend/pipeline/dictionary.py`, the single source for the schema,
the SQL DDL and the validator's column checks. Do not edit by hand.

Req = required (NOT NULL). Derived = recomputed from other rows in s10 and checked
again by the validator. Formats are the regexes in `pipeline/ids.py`.

## public.department

The eight fixed departments. Kind: master. Primary key: `department_code`.
Unique: `department_name`.

| Column | Type | Req | Allowed values / rule | References | Derived |
|---|---|---|---|---|---|
| department_code | CHAR(3) | yes | ENG, DAT, ITS, SAL, MKT, FIN, HRM, OPS; `^[A-Z]{3}$`; Three-letter code, e.g. ENG. |  |  |
| department_name | VARCHAR(60) | yes | Unique display name. |  |  |
| home_category | VARCHAR(40) | yes | Software Engineering, Data & AI, Infrastructure & Cloud, Sales, Marketing, Finance, People & HR, Operations & Supply Chain, Leadership & Communication, Digital Productivity; The department's own skill category. |  |  |

## public.job_role

Roles: five career levels per department, linked into a ladder. Named job_role because ROLE is a Postgres keyword. Kind: master. Primary key: `role_id`.
Unique: `role_title`.

| Column | Type | Req | Allowed values / rule | References | Derived |
|---|---|---|---|---|---|
| role_id | VARCHAR(10) | yes | `^ROL-[0-9]{6}$` |  |  |
| role_title | VARCHAR(80) | yes | Unique title. |  |  |
| department_code | CHAR(3) | yes | ENG, DAT, ITS, SAL, MKT, FIN, HRM, OPS | department.department_code |  |
| career_level | SMALLINT | yes | range 1..5 |  |  |
| next_role_id | VARCHAR(10) | no | `^ROL-[0-9]{6}$`; Next role up the ladder. Null only at career level 5. | job_role.role_id |  |

## public.skill

Skills, grouped into ten categories. Kind: master. Primary key: `skill_id`.
Unique: `skill_name`.

| Column | Type | Req | Allowed values / rule | References | Derived |
|---|---|---|---|---|---|
| skill_id | VARCHAR(10) | yes | `^SKL-[0-9]{6}$` |  |  |
| skill_name | VARCHAR(80) | yes | Unique name. |  |  |
| skill_category | VARCHAR(40) | yes | Software Engineering, Data & AI, Infrastructure & Cloud, Sales, Marketing, Finance, People & HR, Operations & Supply Chain, Leadership & Communication, Digital Productivity |  |  |

## public.role_skill_target

The level each role needs in each of its skills (N:M role-skill). Kind: bridge. Primary key: `role_id, skill_id`.

| Column | Type | Req | Allowed values / rule | References | Derived |
|---|---|---|---|---|---|
| role_id | VARCHAR(10) | yes | `^ROL-[0-9]{6}$` | job_role.role_id |  |
| skill_id | VARCHAR(10) | yes | `^SKL-[0-9]{6}$` | skill.skill_id |  |
| target_level | SMALLINT | yes | range 1..5 |  |  |
| importance | VARCHAR(10) | yes | CORE, SUPPORTING |  |  |
| effective_from | DATE | yes |  |  |  |
| effective_to | DATE | no | Null while the target is in force. |  |  |

## public.employee

Employees, their current role and the role they are working towards. Kind: master. Primary key: `employee_id`.

| Column | Type | Req | Allowed values / rule | References | Derived |
|---|---|---|---|---|---|
| employee_id | VARCHAR(10) | yes | `^EMP-[0-9]{6}$` |  |  |
| first_name | VARCHAR(40) | yes |  |  |  |
| last_name | VARCHAR(40) | yes |  |  |  |
| department_code | CHAR(3) | yes | ENG, DAT, ITS, SAL, MKT, FIN, HRM, OPS; Equals the department of role_id. | department.department_code |  |
| role_id | VARCHAR(10) | yes | `^ROL-[0-9]{6}$`; Current role. | job_role.role_id |  |
| target_role_id | VARCHAR(10) | yes | `^ROL-[0-9]{6}$`; role_id, or the role's next_role_id for a career pathway. | job_role.role_id |  |
| manager_id | VARCHAR(10) | no | `^EMP-[0-9]{6}$`; Same department, higher level. Null only at level 5. | employee.employee_id |  |
| hire_date | DATE | yes |  |  |  |
| employment_status | VARCHAR(10) | yes | ACTIVE, ON_LEAVE |  |  |

## public.course

The course catalog. Kind: master. Primary key: `course_id`.
Unique: `course_title`.

| Column | Type | Req | Allowed values / rule | References | Derived |
|---|---|---|---|---|---|
| course_id | VARCHAR(10) | yes | `^CRS-[0-9]{6}$` |  |  |
| course_title | VARCHAR(120) | yes |  |  |  |
| skill_category | VARCHAR(40) | yes | Software Engineering, Data & AI, Infrastructure & Cloud, Sales, Marketing, Finance, People & HR, Operations & Supply Chain, Leadership & Communication, Digital Productivity |  |  |
| course_level | VARCHAR(12) | yes | FOUNDATION, INTERMEDIATE, ADVANCED |  |  |
| delivery_mode | VARCHAR(10) | yes | ONLINE, BLENDED, CLASSROOM |  |  |
| duration_hours | SMALLINT | yes | range 4..40; A multiple of 4. |  |  |
| cost_amount | NUMERIC(12,2) | yes | range 0..; duration_hours x hourly rate of the delivery mode. |  | yes |
| currency | CHAR(3) | yes | INR |  |  |
| course_status | VARCHAR(10) | yes | ACTIVE, RETIRED |  |  |

## public.course_skill

Which skills a course teaches and up to what level (N:M course-skill). Kind: bridge. Primary key: `course_id, skill_id`.

| Column | Type | Req | Allowed values / rule | References | Derived |
|---|---|---|---|---|---|
| course_id | VARCHAR(10) | yes | `^CRS-[0-9]{6}$` | course.course_id |  |
| skill_id | VARCHAR(10) | yes | `^SKL-[0-9]{6}$` | skill.skill_id |  |
| skill_role | VARCHAR(10) | yes | PRIMARY, SECONDARY |  |  |
| target_level | SMALLINT | yes | range 1..5; The level the course can certify. |  |  |

## public.course_prerequisite

Course prerequisites (N:M course-course). Always same category, strictly lower level. Kind: bridge. Primary key: `course_id, prerequisite_course_id`.

| Column | Type | Req | Allowed values / rule | References | Derived |
|---|---|---|---|---|---|
| course_id | VARCHAR(10) | yes | `^CRS-[0-9]{6}$` | course.course_id |  |
| prerequisite_course_id | VARCHAR(10) | yes | `^CRS-[0-9]{6}$` | course.course_id |  |

## public.course_offering

Scheduled runs of a course, with seats. Kind: master. Primary key: `offering_id`.

| Column | Type | Req | Allowed values / rule | References | Derived |
|---|---|---|---|---|---|
| offering_id | VARCHAR(10) | yes | `^OFF-[0-9]{6}$` |  |  |
| course_id | VARCHAR(10) | yes | `^CRS-[0-9]{6}$` | course.course_id |  |
| start_date | DATE | yes | A Monday. |  |  |
| end_date | DATE | yes | start + (hours / 4) x 7 - 1. |  | yes |
| capacity | SMALLINT | yes | range 1..100 |  |  |
| seats_planned | SMALLINT | yes | range 0..100 |  | yes |
| seats_approved | SMALLINT | yes | range 0..100 |  | yes |

## public.budget

One learning budget per department per year. Kind: master. Primary key: `budget_id`.
Unique: `department_code, fiscal_year`.

| Column | Type | Req | Allowed values / rule | References | Derived |
|---|---|---|---|---|---|
| budget_id | VARCHAR(16) | yes | `^BUD-[A-Z]{3}-[0-9]{4}$` |  |  |
| department_code | CHAR(3) | yes | ENG, DAT, ITS, SAL, MKT, FIN, HRM, OPS | department.department_code |  |
| fiscal_year | SMALLINT | yes | range 2026..2026 |  |  |
| limit_amount | NUMERIC(12,2) | yes | range 0.. |  |  |
| planned_amount | NUMERIC(12,2) | yes | range 0.. |  | yes |
| committed_amount | NUMERIC(12,2) | yes | range 0.. |  | yes |
| remaining_amount | NUMERIC(12,2) | yes | Can be negative. |  | yes |
| utilization_pct | NUMERIC(6,2) | yes | range 0.. |  | yes |
| budget_status | VARCHAR(12) | yes | WITHIN_LIMIT, EXCEEDED |  | yes |
| currency | CHAR(3) | yes | INR |  |  |

## public.recommendation

The January planning run: the learning path and every rejected candidate, with reasons. Kind: transaction. Primary key: `recommendation_id`.
Unique: `employee_id, course_id`.

| Column | Type | Req | Allowed values / rule | References | Derived |
|---|---|---|---|---|---|
| recommendation_id | VARCHAR(30) | yes | `^REC-EMP-[0-9]{6}-CRS-[0-9]{6}$` |  |  |
| employee_id | VARCHAR(10) | yes | `^EMP-[0-9]{6}$` | employee.employee_id |  |
| course_id | VARCHAR(10) | yes | `^CRS-[0-9]{6}$` | course.course_id |  |
| target_skill_id | VARCHAR(10) | yes | `^SKL-[0-9]{6}$` | skill.skill_id |  |
| required_for_course_id | VARCHAR(10) | no | `^CRS-[0-9]{6}$`; Set only for PREREQUISITE_FOR. | course.course_id |  |
| decision | VARCHAR(16) | yes | RECOMMENDED, NOT_RECOMMENDED |  |  |
| reason_code | VARCHAR(30) | yes | CLOSES_GAP, PREREQUISITE_FOR, COURSE_UNAVAILABLE, PREREQUISITE_UNAVAILABLE, PATH_LIMIT, OVER_BUDGET, NO_SCHEDULE |  |  |
| path_sequence | SMALLINT | no | range 1..4 |  |  |
| planned_offering_id | VARCHAR(10) | no | `^OFF-[0-9]{6}$`; Required when RECOMMENDED. | course_offering.offering_id |  |
| planned_start_date | DATE | no |  |  | yes |
| planned_end_date | DATE | no |  |  | yes |
| estimated_cost | NUMERIC(12,2) | yes | range 0.. |  | yes |
| cumulative_cost | NUMERIC(12,2) | no | range 0.. |  | yes |
| planning_date | DATE | yes |  |  |  |
| period_start | DATE | yes |  |  |  |
| period_end | DATE | yes |  |  |  |

## public.enrollment

A request to take a course. Rejected requests are enrollments too. Kind: transaction. Primary key: `enrollment_id`.
Unique: `employee_id, course_id`.

| Column | Type | Req | Allowed values / rule | References | Derived |
|---|---|---|---|---|---|
| enrollment_id | VARCHAR(30) | yes | `^ENR-EMP-[0-9]{6}-CRS-[0-9]{6}$` |  |  |
| employee_id | VARCHAR(10) | yes | `^EMP-[0-9]{6}$` | employee.employee_id |  |
| course_id | VARCHAR(10) | yes | `^CRS-[0-9]{6}$` | course.course_id |  |
| offering_id | VARCHAR(10) | yes | `^OFF-[0-9]{6}$` | course_offering.offering_id |  |
| recommendation_id | VARCHAR(30) | yes | `^REC-EMP-[0-9]{6}-CRS-[0-9]{6}$` | recommendation.recommendation_id |  |
| budget_id | VARCHAR(16) | yes | `^BUD-[A-Z]{3}-[0-9]{4}$` | budget.budget_id |  |
| requested_on | DATE | yes |  |  |  |
| cost_amount | NUMERIC(12,2) | yes | range 0.. |  | yes |
| current_status | VARCHAR(12) | yes | REQUESTED, APPROVED, REJECTED, IN_PROGRESS, COMPLETED, WITHDRAWN |  | yes |
| last_event_on | DATE | yes |  |  | yes |

## public.enrollment_event

Append-only status history of every enrollment. Kind: event. Primary key: `event_id`.
Unique: `enrollment_id, event_seq`.

| Column | Type | Req | Allowed values / rule | References | Derived |
|---|---|---|---|---|---|
| event_id | VARCHAR(10) | yes | `^EVT-[0-9]{6}$` |  |  |
| enrollment_id | VARCHAR(30) | yes | `^ENR-EMP-[0-9]{6}-CRS-[0-9]{6}$` | enrollment.enrollment_id |  |
| event_seq | SMALLINT | yes | range 1..10 |  |  |
| from_status | VARCHAR(12) | no | REQUESTED, APPROVED, REJECTED, IN_PROGRESS, COMPLETED, WITHDRAWN |  |  |
| to_status | VARCHAR(12) | yes | REQUESTED, APPROVED, REJECTED, IN_PROGRESS, COMPLETED, WITHDRAWN |  |  |
| event_on | DATE | yes |  |  |  |
| actor | VARCHAR(12) | yes | EMPLOYEE, MANAGER, HR_PARTNER, SYSTEM |  |  |
| reason_code | VARCHAR(20) | no | NO_SEATS, BUDGET_EXHAUSTED, PERSONAL, WORKLOAD |  |  |

## public.completion

Course completions. enrollment_id is deliberately not unique: a duplicate is a labelled anomaly. Kind: event. Primary key: `completion_id`.

| Column | Type | Req | Allowed values / rule | References | Derived |
|---|---|---|---|---|---|
| completion_id | VARCHAR(16) | yes | `^CMP-[0-9]{4}-[0-9]{6}$` |  |  |
| enrollment_id | VARCHAR(30) | yes | `^ENR-EMP-[0-9]{6}-CRS-[0-9]{6}$` | enrollment.enrollment_id |  |
| completed_on | DATE | yes |  |  |  |
| attendance_pct | NUMERIC(5,1) | yes | range 0..100 |  |  |
| final_score | SMALLINT | yes | range 0..100 |  |  |
| result | VARCHAR(8) | yes | PASSED, FAILED |  | yes |

## public.proficiency_assessment

Append-only history of skill assessments. The score is the evidence; the level comes from the score bands. Kind: event. Primary key: `assessment_id`.

| Column | Type | Req | Allowed values / rule | References | Derived |
|---|---|---|---|---|---|
| assessment_id | VARCHAR(10) | yes | `^ASM-[0-9]{6}$` |  |  |
| employee_id | VARCHAR(10) | yes | `^EMP-[0-9]{6}$` | employee.employee_id |  |
| skill_id | VARCHAR(10) | yes | `^SKL-[0-9]{6}$` | skill.skill_id |  |
| assessment_type | VARCHAR(12) | yes | BASELINE, POST_COURSE |  |  |
| assessed_on | DATE | yes |  |  |  |
| assessment_score | SMALLINT | yes | range 0..100 |  |  |
| proficiency_level | SMALLINT | yes | range 0..5; band(assessment_score), BR-15. |  |  |
| assessor_type | VARCHAR(12) | yes | MANAGER, SKILL_TEST |  |  |
| completion_id | VARCHAR(16) | no | `^CMP-[0-9]{4}-[0-9]{6}$`; Required if and only if POST_COURSE. | completion.completion_id |  |

## public.employee_skill

Each employee's level in each skill of their current and target role (N:M employee-skill). Kind: bridge. Primary key: `employee_id, skill_id`.

| Column | Type | Req | Allowed values / rule | References | Derived |
|---|---|---|---|---|---|
| employee_id | VARCHAR(10) | yes | `^EMP-[0-9]{6}$` | employee.employee_id |  |
| skill_id | VARCHAR(10) | yes | `^SKL-[0-9]{6}$` | skill.skill_id |  |
| baseline_level | SMALLINT | yes | range 0..5 |  |  |
| current_level | SMALLINT | yes | range 0..5; Latest assessment on or before the as-of date. |  | yes |
| last_assessment_id | VARCHAR(10) | yes | `^ASM-[0-9]{6}$` | proficiency_assessment.assessment_id | yes |
| last_assessed_on | DATE | yes |  |  | yes |

## public.skill_gap

Derived: every target-role skill of every employee, with the gap at planning and now. Kind: derived. Primary key: `employee_id, skill_id`.

| Column | Type | Req | Allowed values / rule | References | Derived |
|---|---|---|---|---|---|
| employee_id | VARCHAR(10) | yes | `^EMP-[0-9]{6}$` | employee.employee_id |  |
| skill_id | VARCHAR(10) | yes | `^SKL-[0-9]{6}$` | skill.skill_id |  |
| target_role_id | VARCHAR(10) | yes | `^ROL-[0-9]{6}$` | job_role.role_id |  |
| target_level | SMALLINT | yes | range 1..5 |  | yes |
| planning_level | SMALLINT | yes | range 0..5 |  | yes |
| planning_gap | SMALLINT | yes | range 0..5 |  | yes |
| current_level | SMALLINT | yes | range 0..5 |  | yes |
| current_gap | SMALLINT | yes | range 0..5 |  | yes |
| plan_status | VARCHAR(26) | yes | NO_GAP, PLANNED, NO_COURSE, EMPLOYEE_ON_LEAVE, COURSE_UNAVAILABLE, PREREQUISITE_UNAVAILABLE, PATH_LIMIT, OVER_BUDGET, NO_SCHEDULE |  | yes |
| gap_status | VARCHAR(10) | yes | NO_GAP, CLOSED, OPEN |  | yes |

## eval.ground_truth

The labelled edge cases. Never read by the detector. Kind: evaluation. Primary key: `case_id`.
Unique: `issue_type, record_id`.

| Column | Type | Req | Allowed values / rule | References | Derived |
|---|---|---|---|---|---|
| case_id | VARCHAR(10) | yes | `^GT-[0-9]{6}$` |  |  |
| issue_type | VARCHAR(30) | yes | PREREQUISITE_VIOLATION, COURSE_UNAVAILABLE, BUDGET_EXCEEDED, DUPLICATE_COMPLETION, GAP_NOT_REASSESSED |  |  |
| entity | VARCHAR(40) | yes | Input table holding the record. |  |  |
| record_id | VARCHAR(30) | yes |  |  |  |
| employee_id | VARCHAR(10) | yes | `^EMP-[0-9]{6}$` |  |  |
| related_ids | TEXT | no | Semicolon-separated. |  |  |
| rule_code | VARCHAR(6) | yes | BR-01, BR-02, BR-03, BR-04, BR-05, BR-06, BR-07, BR-08, BR-09, BR-10, BR-11, BR-12, BR-13, BR-14, BR-15, BR-16, BR-17, BR-18, BR-19, BR-20 |  |  |
| expected_decision | VARCHAR(60) | yes |  |  |  |
| description | TEXT | yes |  |  |  |

## eval.detected_issue

What the detector found, using input tables only. Kind: evaluation. Primary key: `issue_type, record_id`.

| Column | Type | Req | Allowed values / rule | References | Derived |
|---|---|---|---|---|---|
| issue_type | VARCHAR(30) | yes | PREREQUISITE_VIOLATION, COURSE_UNAVAILABLE, BUDGET_EXCEEDED, DUPLICATE_COMPLETION, GAP_NOT_REASSESSED |  |  |
| record_id | VARCHAR(30) | yes |  |  |  |
| rule_code | VARCHAR(6) | yes | BR-01, BR-02, BR-03, BR-04, BR-05, BR-06, BR-07, BR-08, BR-09, BR-10, BR-11, BR-12, BR-13, BR-14, BR-15, BR-16, BR-17, BR-18, BR-19, BR-20 |  |  |
| evidence | TEXT | yes |  |  |  |

## eval.validation_result

One row per validator check. Kind: evaluation. Primary key: `check_id`.

| Column | Type | Req | Allowed values / rule | References | Derived |
|---|---|---|---|---|---|
| check_id | VARCHAR(60) | yes |  |  |  |
| rule_code | VARCHAR(6) | no | BR-01, BR-02, BR-03, BR-04, BR-05, BR-06, BR-07, BR-08, BR-09, BR-10, BR-11, BR-12, BR-13, BR-14, BR-15, BR-16, BR-17, BR-18, BR-19, BR-20 |  |  |
| table_name | VARCHAR(40) | yes |  |  |  |
| kind | VARCHAR(12) | yes | STRUCTURAL, RULE |  |  |
| failing_count | INTEGER | yes | range 0.. |  |  |
| expected_count | INTEGER | no | range 0.. |  |  |
| status | VARCHAR(4) | yes | PASS, FAIL |  |  |
| sample_ids | TEXT | no |  |  |  |

## eval.metric

Evaluation metrics. dimension is ALL or a breakdown key such as a department code. Kind: evaluation. Primary key: `metric_group, metric_name, dimension`.

| Column | Type | Req | Allowed values / rule | References | Derived |
|---|---|---|---|---|---|
| metric_group | VARCHAR(40) | yes |  |  |  |
| metric_name | VARCHAR(80) | yes |  |  |  |
| dimension | VARCHAR(60) | yes |  |  |  |
| value | NUMERIC(14,4) | yes |  |  |  |
