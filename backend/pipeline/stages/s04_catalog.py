"""
s04: courses, the skills they teach, and their prerequisites.

Every skill gets two PRIMARY courses. A prerequisite is always in the same
category and at a strictly lower level, so the prerequisite graph can
never contain a cycle, and the longest chain is ADVANCED -> INTERMEDIATE
-> FOUNDATION.
"""

from .. import config, ids, rng, vocab
from .common import pick, uniform_int

LEVEL_ORDER = {"FOUNDATION": 0, "INTERMEDIATE": 1, "ADVANCED": 2}


def _hours(random, level):
    low, high = config.DURATION_RANGE[level]
    step = config.HOURS_PER_WEEK
    return uniform_int(random, low // step, high // step) * step


def run(tables, plan):
    random = rng.stage_rng(rng.CATALOG)
    category_order = {c: i for i, c in enumerate(config.CATEGORIES)}
    skills_by_category = {}
    for skill in tables["skill"]:
        skills_by_category.setdefault(skill["skill_category"], []).append(skill)

    drafts = []
    for skill in tables["skill"]:
        levels = (
            pick(random, config.FIRST_COURSE_LEVEL_SHARE),
            pick(random, config.SECOND_COURSE_LEVEL_SHARE),
        )
        suffixes = (vocab.FIRST_COURSE_SUFFIX, vocab.SECOND_COURSE_SUFFIX)
        for level, suffix in zip(levels, suffixes):
            mode = pick(random, config.DELIVERY_MODE_SHARE)
            hours = _hours(random, level)
            primary_target = int(random.choice(config.PRIMARY_TARGET_LEVELS[level]))

            others = [s["skill_id"] for s in skills_by_category[skill["skill_category"]] if s["skill_id"] != skill["skill_id"]]
            low, high = config.SECONDARY_SKILLS_RANGE
            count = min(uniform_int(random, low, high), len(others))
            secondary = sorted(random.choice(others, size=count, replace=False).tolist()) if count else []

            drafts.append(
                {
                    "course_title": f"{skill['skill_name']} {suffix[level]}",
                    "skill_category": skill["skill_category"],
                    "course_level": level,
                    "delivery_mode": mode,
                    "duration_hours": hours,
                    "cost_amount": hours * config.HOURLY_RATE[mode],
                    "currency": config.CURRENCY,
                    "course_status": "RETIRED" if random.random() < config.RETIRED_COURSE_SHARE else "ACTIVE",
                    "_skills": [(skill["skill_id"], "PRIMARY", primary_target)]
                    + [(s, "SECONDARY", max(1, primary_target - 1)) for s in secondary],
                }
            )

    drafts.sort(key=lambda d: (category_order[d["skill_category"]], LEVEL_ORDER[d["course_level"]], d["course_title"]))
    counter = ids.IdCounter(ids.course_id)
    courses, course_skills = [], []
    for draft in drafts:
        course_id = counter.next()
        for skill_id, role, target in draft.pop("_skills"):
            course_skills.append(
                {"course_id": course_id, "skill_id": skill_id, "skill_role": role, "target_level": target}
            )
        courses.append({"course_id": course_id, **draft})

    # Prerequisites, drawn after the IDs exist so they point at final IDs.
    by_category_level = {}
    for course in courses:
        by_category_level.setdefault((course["skill_category"], course["course_level"]), []).append(course["course_id"])

    prerequisites = []

    def add(course, level):
        pool = by_category_level.get((course["skill_category"], level), [])
        if pool:
            prerequisites.append(
                {"course_id": course["course_id"], "prerequisite_course_id": str(random.choice(pool))}
            )

    for course in courses:
        if course["course_level"] == "INTERMEDIATE" and random.random() < config.INTERMEDIATE_PREREQ_SHARE:
            add(course, "FOUNDATION")
        elif course["course_level"] == "ADVANCED":
            add(course, "INTERMEDIATE")
            if random.random() < config.ADVANCED_EXTRA_FOUNDATION_SHARE:
                add(course, "FOUNDATION")

    tables["course"] = courses
    tables["course_skill"] = course_skills
    tables["course_prerequisite"] = prerequisites
    return tables
