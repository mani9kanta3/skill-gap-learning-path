"""
s02: employees.

Department sizes and career levels follow the shares in config, split
with exact whole numbers so the total is always right. Every department
staffs every career level, so everyone below level 5 has a possible
manager one level up.

IDs are given after sorting by department, hire date and name, and only
then are managers and target roles picked, so they point at final IDs.
"""

from .. import config, ids, rng, vocab
from .common import allocate, random_date


def run(tables, plan):
    random = rng.stage_rng(rng.EMPLOYEES)
    roles = {(r["department_code"], r["career_level"]): r for r in tables["job_role"]}
    department_order = {code: i for i, code in enumerate(config.DEPARTMENT_CODES)}

    per_department = allocate(plan.scale.employees, config.DEPARTMENT_SHARE)

    people = []
    for code in config.DEPARTMENT_CODES:
        per_level = allocate(per_department[code], config.CAREER_LEVEL_SHARE, minimum=1)
        for level in config.CAREER_LEVELS:
            for _ in range(per_level[level]):
                people.append(
                    {
                        "first_name": str(random.choice(vocab.FIRST_NAMES)),
                        "last_name": str(random.choice(vocab.LAST_NAMES)),
                        "department_code": code,
                        "career_level": level,
                        "role_id": roles[(code, level)]["role_id"],
                        "hire_date": random_date(random, config.HIRE_DATE_FROM, config.HIRE_DATE_TO),
                        "employment_status": "ON_LEAVE"
                        if random.random() < config.ON_LEAVE_SHARE
                        else "ACTIVE",
                    }
                )

    people.sort(
        key=lambda p: (department_order[p["department_code"]], p["hire_date"], p["last_name"], p["first_name"])
    )
    counter = ids.IdCounter(ids.employee_id)
    for person in people:
        person["employee_id"] = counter.next()

    by_department_level = {}
    for person in people:
        key = (person["department_code"], person["career_level"])
        by_department_level.setdefault(key, []).append(person["employee_id"])

    employees = []
    for person in people:
        code, level = person["department_code"], person["career_level"]
        manager = None
        if level < max(config.CAREER_LEVELS):
            manager = str(random.choice(by_department_level[(code, level + 1)]))

        target_role = person["role_id"]
        role = roles[(code, level)]
        if (
            person["employment_status"] == "ACTIVE"
            and role["next_role_id"] is not None
            and random.random() < config.CAREER_PATH_SHARE
        ):
            target_role = role["next_role_id"]

        employees.append(
            {
                "employee_id": person["employee_id"],
                "first_name": person["first_name"],
                "last_name": person["last_name"],
                "department_code": code,
                "role_id": person["role_id"],
                "target_role_id": target_role,
                "manager_id": manager,
                "hire_date": person["hire_date"],
                "employment_status": person["employment_status"],
            }
        )

    tables["employee"] = employees
    return tables
