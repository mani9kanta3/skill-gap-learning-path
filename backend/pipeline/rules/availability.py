"""
BR-04: is a course available in the planning period?
"""


def starts_in_period(start_date, period_start, period_end):
    return period_start <= start_date <= period_end


def is_available(course_status, offering_starts, period_start, period_end):
    """ACTIVE, and at least one offering starts inside the period."""
    if course_status != "ACTIVE":
        return False
    return any(starts_in_period(start, period_start, period_end) for start in offering_starts)
