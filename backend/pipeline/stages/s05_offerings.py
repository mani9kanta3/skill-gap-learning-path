"""
s05: course offerings.

ACTIVE courses run 3 to 6 times in 2026 on Monday starts. A few ACTIVE
courses only run in 2027, which makes them unavailable in the planning
period (BR-04). RETIRED courses never run.
"""

from .. import config, ids, rng
from ..rules import schedule
from .common import mondays, uniform_int


def run(tables, plan):
    random = rng.stage_rng(rng.OFFERINGS)
    this_year = mondays(config.FIRST_OFFERING_START, config.LAST_OFFERING_START)
    next_year = mondays(config.NEXT_YEAR_FIRST_START, config.NEXT_YEAR_LAST_START)

    drafts = []
    for course in tables["course"]:
        if course["course_status"] != "ACTIVE":
            continue
        if random.random() < config.NEXT_YEAR_ONLY_SHARE:
            pool, count_range = next_year, config.NEXT_YEAR_OFFERINGS
        else:
            pool, count_range = this_year, config.OFFERINGS_PER_COURSE
        count = uniform_int(random, *count_range)
        picks = sorted(random.choice(len(pool), size=count, replace=False).tolist())
        for index in picks:
            start = pool[index]
            drafts.append(
                {
                    "course_id": course["course_id"],
                    "start_date": start,
                    "end_date": schedule.end_date(start, course["duration_hours"]),
                    "capacity": config.CAPACITY[course["delivery_mode"]],
                    "seats_planned": None,
                    "seats_approved": None,
                }
            )

    drafts.sort(key=lambda o: (o["course_id"], o["start_date"]))
    counter = ids.IdCounter(ids.offering_id)
    tables["course_offering"] = [{"offering_id": counter.next(), **draft} for draft in drafts]
    return tables
