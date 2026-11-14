"""
BR-08: placing a path's courses on the calendar, one after another, in
offerings that still have a free seat.

The seat ledger is shared by every employee in one planning run, so a
plan can never book more seats in an offering than it has.
"""

from datetime import timedelta

from .. import config


def end_date(start_date, duration_hours):
    """Courses run at 4 hours a week. A 12-hour course starting on a Monday ends on the Sunday of week 3."""
    if duration_hours % config.HOURS_PER_WEEK != 0:
        raise ValueError(f"duration_hours must be a multiple of {config.HOURS_PER_WEEK}.")
    weeks = duration_hours // config.HOURS_PER_WEEK
    return start_date + timedelta(days=weeks * 7 - 1)


def next_slot(previous_end):
    """The earliest start for the step after a course that ends on previous_end."""
    return previous_end + timedelta(days=config.SCHEDULE_GAP_DAYS)


def first_slot(planning_date, busy_until=None):
    """
    The earliest start for step 1: 14 days after the planning date, or
    14 days after a course the employee is already approved for or taking.
    """
    slot = planning_date + timedelta(days=config.SCHEDULE_GAP_DAYS)
    if busy_until is not None:
        slot = max(slot, next_slot(busy_until))
    return slot


class SeatLedger:
    """Free seats per offering, as of the planning date, minus what this run has booked."""

    def __init__(self, free_seats):
        self._free = dict(free_seats)

    def free(self, offering_id):
        return self._free.get(offering_id, 0)

    def book(self, offering_id):
        if self._free.get(offering_id, 0) <= 0:
            raise ValueError(f"No free seat left in {offering_id}.")
        self._free[offering_id] -= 1


def place(course_ids, slot, period_end, offerings_by_course, ledger):
    """
    Place courses in order, each in the earliest offering that starts on or
    after the current slot, on or before period_end, and has a free seat.

    offerings_by_course: course_id -> list of dicts with offering_id,
    start_date and end_date, sorted by start_date.

    Returns a list of (course_id, offering) in order, or None if any course
    cannot be placed. Nothing is booked here: the caller books the seats
    only after every other check has passed.
    """
    placed = []
    for course_id in course_ids:
        chosen = None
        for offering in offerings_by_course.get(course_id, ()):
            if offering["start_date"] < slot:
                continue
            if offering["start_date"] > period_end:
                break
            if ledger.free(offering["offering_id"]) > 0:
                chosen = offering
                break
        if chosen is None:
            return None
        placed.append((course_id, chosen))
        slot = next_slot(chosen["end_date"])
    return placed
