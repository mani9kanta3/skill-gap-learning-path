"""
s03: baseline proficiency.

One BASELINE assessment per (employee, skill) for every skill of the
current role and the target role, dated in Q4 2025.

The baseline is the starting state, so its level is drawn directly: for a
current-role skill, level = max(0, target - d). The score is then drawn
inside that level's band, so BR-15 (level = band(score)) holds for every
assessment, baseline included.

Assessment IDs are not given here. They are numbered once in s10 (see
ARCHITECTURE.md 3.2); until then each row is known by its natural key.
"""

from .. import config, rng
from .common import pick, random_date, uniform_int


def run(tables, plan):
    random = rng.stage_rng(rng.PROFICIENCY)

    targets_by_role = {}
    for row in tables["role_skill_target"]:
        targets_by_role.setdefault(row["role_id"], {})[row["skill_id"]] = row["target_level"]

    assessments = []
    employee_skills = []
    for employee in tables["employee"]:
        current = targets_by_role[employee["role_id"]]
        target = targets_by_role[employee["target_role_id"]]
        for skill_id in sorted(set(current) | set(target)):
            if skill_id in current:
                drop = pick(random, config.BASELINE_GAP_SHARE)
                level = max(0, current[skill_id] - drop)
            else:
                level = int(random.choice(config.TARGET_ONLY_SKILL_LEVELS))

            low, high = config.SCORE_BANDS[level]
            assessments.append(
                {
                    "assessment_id": None,
                    "employee_id": employee["employee_id"],
                    "skill_id": skill_id,
                    "assessment_type": "BASELINE",
                    "assessed_on": random_date(
                        random, config.BASELINE_ASSESSMENT_FROM, config.BASELINE_ASSESSMENT_TO
                    ),
                    "assessment_score": uniform_int(random, low, high),
                    "proficiency_level": level,
                    "assessor_type": "MANAGER"
                    if random.random() < config.BASELINE_MANAGER_SHARE
                    else "SKILL_TEST",
                    "completion_id": None,
                }
            )
            employee_skills.append(
                {
                    "employee_id": employee["employee_id"],
                    "skill_id": skill_id,
                    "baseline_level": level,
                    # The rest is derived in s10.
                    "current_level": None,
                    "last_assessment_id": None,
                    "last_assessed_on": None,
                }
            )

    tables["proficiency_assessment"] = assessments
    tables["employee_skill"] = employee_skills
    return tables
