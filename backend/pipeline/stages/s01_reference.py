"""
s01: departments, skills, roles and the role skill targets.

Each department gets one career ladder of five roles, and one ladder list
of ten skills (home skills first, then shared ones; how many of each
depends on the scale, see config.check_scale). A level-L role targets the
first 5 + L skills of that list. Targets never go down as you climb.
"""

from .. import config, ids, rng, vocab


def run(tables, plan):
    random = rng.stage_rng(rng.REFERENCE)

    tables["department"] = [
        {"department_code": code, "department_name": name, "home_category": home}
        for code, name, home in config.DEPARTMENTS
    ]

    # Skills: a seeded sample of the 50 names per category, numbered in
    # category order, then name order.
    skills_by_category = {}
    skill_rows = []
    counter = ids.IdCounter(ids.skill_id)
    for category in config.CATEGORIES:
        names = [f"{topic} {aspect}" for topic in vocab.TOPICS[category] for aspect in vocab.ASPECTS]
        chosen = sorted(random.choice(names, size=plan.skills_per_category, replace=False).tolist())
        skills_by_category[category] = []
        for name in chosen:
            skill_id = counter.next()
            skill_rows.append({"skill_id": skill_id, "skill_name": name, "skill_category": category})
            skills_by_category[category].append(skill_id)
    tables["skill"] = skill_rows

    shared_pool = [s for category in config.SHARED_CATEGORIES for s in skills_by_category[category]]

    roles = []
    targets = []
    role_counter = ids.IdCounter(ids.role_id)
    for code, name, home in config.DEPARTMENTS:
        home_skills = random.choice(
            skills_by_category[home], size=plan.home_ladder_skills, replace=False
        ).tolist()
        shared_skills = random.choice(
            shared_pool, size=plan.shared_ladder_skills, replace=False
        ).tolist()
        ladder = home_skills + shared_skills
        base_levels = [int(random.choice(config.BASE_TARGET_LEVELS)) for _ in ladder]

        department_roles = []
        for level in config.CAREER_LEVELS:
            role_id = role_counter.next()
            department_roles.append(role_id)
            roles.append(
                {
                    "role_id": role_id,
                    "role_title": f"{name} {vocab.LEVEL_TITLES[level]}",
                    "department_code": code,
                    "career_level": level,
                    "next_role_id": None,
                }
            )
            for position, skill_id in enumerate(ladder[: config.LADDER_BASE_SKILLS + level]):
                targets.append(
                    {
                        "role_id": role_id,
                        "skill_id": skill_id,
                        "target_level": min(5, base_levels[position] + (level - 1) // 2),
                        "importance": "CORE" if position < config.CORE_SKILL_COUNT else "SUPPORTING",
                        "effective_from": config.PERIOD_START,
                        "effective_to": None,
                    }
                )
        # Link the ladder: each role points at the next level up.
        for lower, upper in zip(department_roles, department_roles[1:]):
            next(r for r in roles if r["role_id"] == lower)["next_role_id"] = upper

    tables["job_role"] = roles
    tables["role_skill_target"] = targets
    return tables
