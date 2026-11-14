"""
One function per endpoint, each one plain SQL.

All queries are parameterised (%(name)s); user input never goes into the
SQL text. Sort columns and filters are fixed in code.
"""

import json
from functools import lru_cache

from pipeline import config as pipeline_config
from pipeline.rules import recommend, schedule, snapshot

from . import config, db

# ---------------------------------------------------------------------------
# Small lookups
# ---------------------------------------------------------------------------


def health():
    row = db.fetch_one("SELECT count(*) AS employees FROM employee")
    return {"status": "ok", "database": "ok", "employees": row["employees"]}


def departments():
    return db.fetch_all("SELECT department_code, department_name, home_category FROM department ORDER BY department_code")


def skill_categories():
    rows = db.fetch_all("SELECT DISTINCT skill_category FROM skill ORDER BY skill_category")
    return [r["skill_category"] for r in rows]


def summary():
    counts = db.fetch_one(
        """
        SELECT
          (SELECT count(*) FROM employee)                                        AS employees,
          (SELECT count(*) FROM employee WHERE employment_status = 'ACTIVE')     AS active_employees,
          (SELECT count(*) FROM skill)                                           AS skills,
          (SELECT count(*) FROM course)                                          AS courses,
          (SELECT count(*) FROM skill_gap WHERE planning_gap > 0)                AS planning_gaps,
          (SELECT count(*) FROM skill_gap WHERE plan_status = 'PLANNED')         AS planned_gaps,
          (SELECT count(*) FROM skill_gap WHERE gap_status = 'CLOSED')           AS closed_gaps,
          (SELECT count(*) FROM skill_gap WHERE gap_status = 'OPEN')             AS open_gaps,
          (SELECT count(*) FROM recommendation WHERE decision = 'RECOMMENDED')   AS recommended,
          (SELECT count(*) FROM recommendation WHERE funding_status = 'FUNDED')  AS funded_steps,
          (SELECT count(*) FROM recommendation WHERE decision = 'NOT_RECOMMENDED') AS not_recommended,
          (SELECT count(*) FROM enrollment)                                      AS enrollments,
          (SELECT count(*) FROM completion)                                      AS completion_rows,
          (SELECT count(*) FROM eval.detected_issue)                             AS detected_issues,
          (SELECT sum(limit_amount) FROM budget)                                 AS budget_limit,
          (SELECT sum(committed_amount) FROM budget)                             AS budget_committed
        """
    )
    statuses = db.fetch_all(
        "SELECT current_status AS status, count(*) AS n FROM enrollment GROUP BY current_status ORDER BY current_status"
    )
    counts["enrollments_by_status"] = {r["status"]: r["n"] for r in statuses}
    counts["planning_date"] = pipeline_config.PLANNING_DATE
    counts["as_of_date"] = pipeline_config.AS_OF_DATE
    return counts


# ---------------------------------------------------------------------------
# Employees
# ---------------------------------------------------------------------------


def list_employees(search, department, manager_id, status, limit, offset):
    params = {
        "search": f"%{search.strip()}%" if search.strip() else None,
        "department": department or None,
        "manager_id": manager_id or None,
        "status": status or None,
        "limit": limit,
        "offset": offset,
    }
    where = """
        WHERE (%(search)s IS NULL OR e.employee_id ILIKE %(search)s
               OR (e.first_name || ' ' || e.last_name) ILIKE %(search)s)
          AND (%(department)s IS NULL OR e.department_code = %(department)s)
          AND (%(manager_id)s IS NULL OR e.manager_id = %(manager_id)s)
          AND (%(status)s IS NULL OR e.employment_status = %(status)s)
    """
    total = db.fetch_one(f"SELECT count(*) AS n FROM employee e {where}", params)["n"]
    rows = db.fetch_all(
        f"""
        SELECT e.employee_id, e.first_name, e.last_name, e.department_code, e.employment_status,
               e.manager_id, r.role_title, r.career_level, t.role_title AS target_role_title,
               (e.target_role_id <> e.role_id) AS on_career_path,
               (SELECT count(*) FROM skill_gap g WHERE g.employee_id = e.employee_id AND g.gap_status = 'OPEN') AS open_gaps,
               (SELECT count(*) FROM recommendation rc WHERE rc.employee_id = e.employee_id AND rc.decision = 'RECOMMENDED') AS path_courses
        FROM employee e
        JOIN job_role r ON r.role_id = e.role_id
        JOIN job_role t ON t.role_id = e.target_role_id
        {where}
        ORDER BY e.employee_id
        LIMIT %(limit)s OFFSET %(offset)s
        """,
        params,
    )
    return {"total": total, "results": rows}


def employee_detail(employee_id):
    p = {"id": employee_id}
    employee = db.fetch_one(
        """
        SELECT e.*, r.role_title, r.career_level, t.role_title AS target_role_title,
               d.department_name, m.first_name AS manager_first_name, m.last_name AS manager_last_name
        FROM employee e
        JOIN job_role r ON r.role_id = e.role_id
        JOIN job_role t ON t.role_id = e.target_role_id
        JOIN department d ON d.department_code = e.department_code
        LEFT JOIN employee m ON m.employee_id = e.manager_id
        WHERE e.employee_id = %(id)s
        """,
        p,
    )
    if employee is None:
        return None

    employee["gaps"] = db.fetch_all(
        """
        SELECT g.*, s.skill_name, s.skill_category, rst.importance
        FROM skill_gap g
        JOIN skill s ON s.skill_id = g.skill_id
        JOIN role_skill_target rst ON rst.role_id = g.target_role_id AND rst.skill_id = g.skill_id
        WHERE g.employee_id = %(id)s
        ORDER BY (rst.importance = 'CORE') DESC, g.planning_gap DESC, g.skill_id
        """,
        p,
    )
    employee["recommendations"] = db.fetch_all(
        """
        SELECT rc.*, c.course_title, c.course_level, c.delivery_mode, s.skill_name AS target_skill_name,
               rf.course_title AS required_for_title, en.enrollment_id, en.current_status AS enrollment_status
        FROM recommendation rc
        JOIN course c ON c.course_id = rc.course_id
        JOIN skill s ON s.skill_id = rc.target_skill_id
        LEFT JOIN course rf ON rf.course_id = rc.required_for_course_id
        LEFT JOIN enrollment en ON en.recommendation_id = rc.recommendation_id
        WHERE rc.employee_id = %(id)s
        ORDER BY rc.decision, rc.path_sequence NULLS LAST, rc.course_id
        """,
        p,
    )
    enrollments = db.fetch_all(
        """
        SELECT en.*, c.course_title, o.start_date, o.end_date
        FROM enrollment en
        JOIN course c ON c.course_id = en.course_id
        JOIN course_offering o ON o.offering_id = en.offering_id
        WHERE en.employee_id = %(id)s
        ORDER BY en.requested_on, en.enrollment_id
        """,
        p,
    )
    events = db.fetch_all(
        """
        SELECT ev.* FROM enrollment_event ev
        JOIN enrollment en ON en.enrollment_id = ev.enrollment_id
        WHERE en.employee_id = %(id)s
        ORDER BY ev.enrollment_id, ev.event_seq
        """,
        p,
    )
    completions = db.fetch_all(
        """
        SELECT cp.*, a.assessment_id, a.skill_id AS assessed_skill_id, a.assessment_score AS post_score,
               a.proficiency_level AS post_level, a.assessed_on
        FROM completion cp
        JOIN enrollment en ON en.enrollment_id = cp.enrollment_id
        LEFT JOIN proficiency_assessment a ON a.completion_id = cp.completion_id
        WHERE en.employee_id = %(id)s
        ORDER BY cp.completion_id
        """,
        p,
    )
    by_enrollment = {}
    for event in events:
        by_enrollment.setdefault(event["enrollment_id"], []).append(event)
    completions_by = {}
    for completion in completions:
        completions_by.setdefault(completion["enrollment_id"], []).append(completion)
    for enrollment in enrollments:
        enrollment["events"] = by_enrollment.get(enrollment["enrollment_id"], [])
        enrollment["completions"] = completions_by.get(enrollment["enrollment_id"], [])
    employee["enrollments"] = enrollments

    employee["assessments"] = db.fetch_all(
        """
        SELECT a.*, s.skill_name FROM proficiency_assessment a
        JOIN skill s ON s.skill_id = a.skill_id
        WHERE a.employee_id = %(id)s
        ORDER BY a.assessed_on, a.assessment_id
        """,
        p,
    )
    return employee


# ---------------------------------------------------------------------------
# Path preview: the same engine as the January run, on any date.
# ---------------------------------------------------------------------------

PREVIEW_TABLES = (
    "course",
    "course_skill",
    "course_prerequisite",
    "course_offering",
    "role_skill_target",
    "budget",
    "proficiency_assessment",
    "completion",
    "enrollment",
    "enrollment_event",
    # For the money already allocated to other people's open funded steps.
    "recommendation",
    "employee",
)


@lru_cache(maxsize=1)
def _all_tables():
    """
    Every table the engine needs, read once. The data is static once
    loaded (the API is read-only), so the cache is safe; restart the API
    after loading a different dataset.
    """
    return {name: db.fetch_all(f"SELECT * FROM {name}") for name in PREVIEW_TABLES}


def preview_path(employee_id, planning_date, period_start, period_end):
    employee = db.fetch_one(
        "SELECT employee_id, employment_status, target_role_id, department_code FROM employee WHERE employee_id = %(id)s",
        {"id": employee_id},
    )
    if employee is None:
        return None

    tables = _all_tables()
    # The schema already refuses periods outside the budget year; the
    # budget is still picked by the period's year, never assumed.
    catalog = snapshot.build_catalog(tables, fiscal_year=period_start.year)
    settings = recommend.Settings(planning_date, period_start, period_end)
    planner = recommend.Planner(catalog, settings)
    snap = snapshot.build_snapshot(tables, catalog, planning_date, period_start, period_end)
    ledger = schedule.SeatLedger(snapshot.free_seats(catalog, snap))
    rows, gap_rows = planner.recommend(employee, snap, ledger)

    titles = {c["course_id"]: c["course_title"] for c in tables["course"]}
    skills = {r["skill_id"]: r["skill_name"] for r in db.fetch_all("SELECT skill_id, skill_name FROM skill")}
    for row in rows:
        row["course_title"] = titles[row["course_id"]]
        row["target_skill_name"] = skills[row["target_skill_id"]]
        row["required_for_title"] = titles.get(row["required_for_course_id"])
    for gap in gap_rows:
        gap["skill_name"] = skills[gap["skill_id"]]

    path = [r for r in rows if r["decision"] == "RECOMMENDED"]
    spent = snap.spent.get(employee_id, 0.0)
    department = employee["department_code"]
    limit = catalog.department_limit[department]
    committed = snap.committed.get(department, 0.0)
    reserved_for_others = snap.reserved.get(department, 0.0) - snap.reserved_by_employee.get(employee_id, 0.0)
    return {
        "employee_id": employee_id,
        "planning_date": planning_date,
        "period_start": period_start,
        "period_end": period_end,
        "path": path,
        "not_recommended": [r for r in rows if r["decision"] == "NOT_RECOMMENDED"],
        "gaps": gap_rows,
        "path_cost": sum(r["estimated_cost"] for r in path),
        "allowance": pipeline_config.LEARNING_ALLOWANCE_PER_EMPLOYEE,
        "already_spent": spent,
        "department_code": department,
        "fiscal_year": period_start.year,
        "department_limit": limit,
        "department_committed": committed,
        "department_reserved_for_others": reserved_for_others,
        # BR-09(b): what the whole path was checked against.
        "department_free": snap.department_free(catalog, employee),
        # A preview is a proposal: it is not funded until the budget is
        # allocated to it, so nothing here is marked FUNDED.
        "funding_note": "Proposed only. Funding is decided when the department budget is allocated.",
    }


# ---------------------------------------------------------------------------
# Courses
# ---------------------------------------------------------------------------


def list_courses(search, category, level, available, limit, offset):
    params = {
        "search": f"%{search.strip()}%" if search.strip() else None,
        "category": category or None,
        "level": level or None,
        "available": available,
        "start": pipeline_config.PERIOD_START,
        "end": pipeline_config.PERIOD_END,
        "limit": limit,
        "offset": offset,
    }
    base = """
        FROM course c
        LEFT JOIN LATERAL (
            SELECT bool_or(o.start_date BETWEEN %(start)s AND %(end)s) AS in_period, count(*) AS offerings
            FROM course_offering o WHERE o.course_id = c.course_id
        ) o ON true
        WHERE (%(search)s IS NULL OR c.course_title ILIKE %(search)s OR c.course_id ILIKE %(search)s)
          AND (%(category)s IS NULL OR c.skill_category = %(category)s)
          AND (%(level)s IS NULL OR c.course_level = %(level)s)
          AND (%(available)s IS NULL OR
               (c.course_status = 'ACTIVE' AND coalesce(o.in_period, false)) = %(available)s)
    """
    total = db.fetch_one(f"SELECT count(*) AS n {base}", params)["n"]
    rows = db.fetch_all(
        f"""
        SELECT c.*, coalesce(o.offerings, 0) AS offerings,
               (c.course_status = 'ACTIVE' AND coalesce(o.in_period, false)) AS available,
               (SELECT count(*) FROM course_prerequisite p WHERE p.course_id = c.course_id) AS prerequisites
        {base}
        ORDER BY c.course_id
        LIMIT %(limit)s OFFSET %(offset)s
        """,
        params,
    )
    return {"total": total, "results": rows}


def course_detail(course_id):
    p = {"id": course_id, "start": pipeline_config.PERIOD_START, "end": pipeline_config.PERIOD_END}
    course = db.fetch_one("SELECT * FROM course WHERE course_id = %(id)s", p)
    if course is None:
        return None
    course["skills"] = db.fetch_all(
        """
        SELECT cs.*, s.skill_name, s.skill_category FROM course_skill cs
        JOIN skill s ON s.skill_id = cs.skill_id
        WHERE cs.course_id = %(id)s ORDER BY cs.skill_role, cs.skill_id
        """,
        p,
    )
    course["prerequisites"] = db.fetch_all(
        """
        SELECT c.course_id, c.course_title, c.course_level, c.course_status FROM course_prerequisite p
        JOIN course c ON c.course_id = p.prerequisite_course_id
        WHERE p.course_id = %(id)s ORDER BY c.course_id
        """,
        p,
    )
    course["required_by"] = db.fetch_all(
        """
        SELECT c.course_id, c.course_title, c.course_level, c.course_status FROM course_prerequisite p
        JOIN course c ON c.course_id = p.course_id
        WHERE p.prerequisite_course_id = %(id)s ORDER BY c.course_id
        """,
        p,
    )
    course["offerings"] = db.fetch_all(
        """
        SELECT o.*, (o.start_date BETWEEN %(start)s AND %(end)s) AS in_period
        FROM course_offering o WHERE o.course_id = %(id)s ORDER BY o.start_date
        """,
        p,
    )
    course["available"] = course["course_status"] == "ACTIVE" and any(o["in_period"] for o in course["offerings"])
    return course


# ---------------------------------------------------------------------------
# Budgets, exceptions, evaluation
# ---------------------------------------------------------------------------


def budgets():
    """
    One row per department, with every figure needed to read the status.

    Two different questions are answered here, and they must not be mixed:

    - Spending: committed_amount (approved so far) and remaining_amount
      (limit - committed). This is cash used to date.
    - Obligations: funded_amount (money the January allocation promised
      to funded steps) + outside_plan_amount (approvals of steps that were
      never funded). budget_status is EXCEEDED when obligations are above
      the limit, even if less has been spent so far.

    unallocated_amount = limit - obligations, so a negative number is the
    amount the department is over-committed by.
    """
    rows = db.fetch_all(
        """
        SELECT b.*, d.department_name,
               (SELECT count(*) FROM enrollment_event ev
                JOIN enrollment en ON en.enrollment_id = ev.enrollment_id
                WHERE en.budget_id = b.budget_id AND ev.reason_code = 'BUDGET_EXHAUSTED') AS budget_rejections,
               (SELECT count(*) FROM enrollment en WHERE en.budget_id = b.budget_id) AS enrollments,
               (SELECT coalesce(sum(en.cost_amount), 0) FROM enrollment en
                JOIN recommendation r ON r.recommendation_id = en.recommendation_id
                WHERE en.budget_id = b.budget_id
                  AND r.funding_status <> 'FUNDED'
                  AND EXISTS (SELECT 1 FROM enrollment_event ev
                              WHERE ev.enrollment_id = en.enrollment_id AND ev.to_status = 'APPROVED')
               ) AS outside_plan_amount,
               (SELECT count(*) FROM enrollment en
                JOIN recommendation r ON r.recommendation_id = en.recommendation_id
                WHERE en.budget_id = b.budget_id
                  AND r.funding_status <> 'FUNDED'
                  AND EXISTS (SELECT 1 FROM enrollment_event ev
                              WHERE ev.enrollment_id = en.enrollment_id AND ev.to_status = 'APPROVED')
               ) AS outside_plan_count
        FROM budget b JOIN department d ON d.department_code = b.department_code
        ORDER BY b.department_code
        """
    )
    for row in rows:
        limit = float(row["limit_amount"])
        obligations = float(row["funded_amount"]) + float(row["outside_plan_amount"])
        row["obligations_amount"] = obligations
        row["unallocated_amount"] = limit - obligations
        row["obligations_pct"] = round(100 * obligations / limit, 2)
        if row["budget_status"] == "EXCEEDED":
            row["status_reason"] = (
                f"{row['outside_plan_count']} enrollment(s) worth {float(row['outside_plan_amount']):,.0f} "
                "were approved outside the funded plan, so funded steps plus those approvals "
                f"come to {obligations:,.0f}, which is {obligations - limit:,.0f} over the limit."
            )
        else:
            row["status_reason"] = "Funded steps plus any approvals outside the plan fit within the limit."
    return rows


def exceptions(issue_type, limit, offset):
    params = {"issue_type": issue_type or None, "limit": limit, "offset": offset}
    where = "WHERE (%(issue_type)s IS NULL OR d.issue_type = %(issue_type)s)"
    total = db.fetch_one(f"SELECT count(*) AS n FROM eval.detected_issue d {where}", params)["n"]
    counts = db.fetch_all("SELECT issue_type, count(*) AS n FROM eval.detected_issue GROUP BY issue_type ORDER BY issue_type")
    rows = db.fetch_all(
        f"""
        SELECT d.*, g.case_id, g.employee_id, g.expected_decision, (g.case_id IS NOT NULL) AS labelled
        FROM eval.detected_issue d
        LEFT JOIN eval.ground_truth g ON g.issue_type = d.issue_type AND g.record_id = d.record_id
        {where}
        ORDER BY d.issue_type, d.record_id
        LIMIT %(limit)s OFFSET %(offset)s
        """,
        params,
    )
    return {"total": total, "by_type": {r["issue_type"]: r["n"] for r in counts}, "results": rows}


def evaluation():
    checks = db.fetch_all("SELECT * FROM eval.validation_result ORDER BY kind DESC, check_id")
    metrics = db.fetch_all("SELECT * FROM eval.metric ORDER BY metric_group, metric_name, dimension")
    labelled = db.fetch_all("SELECT issue_type, count(*) AS n FROM eval.ground_truth GROUP BY issue_type ORDER BY issue_type")
    employees = db.fetch_one("SELECT count(*) AS n FROM employee")["n"]
    scale = "full" if employees == pipeline_config.FULL.employees else "starter"
    report = config.OUTPUT_DIR / "reproducibility" / f"report_{scale}.json"
    reproducibility = None
    if report.exists():
        data = json.loads(report.read_text(encoding="utf-8"))
        reproducibility = {
            "scale": data["scale"],
            "seed": data["seed"],
            "identical": data["identical"],
            "files": len(data["files"]),
            "matching": sum(1 for f in data["files"] if f["identical"]),
        }
    return {
        "scale": scale,
        "checks": checks,
        "metrics": metrics,
        "labelled": {r["issue_type"]: r["n"] for r in labelled},
        "reproducibility": reproducibility,
    }
