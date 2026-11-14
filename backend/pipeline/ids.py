"""
Every ID format in the project, and nothing else.

An ID is assigned when its row is created and never changes afterwards
(ARCHITECTURE.md 3.2). Stages never build ID strings by hand: they call
these functions, so a format can only be wrong in one place.

Counters are zero-padded to six digits. A number outside 1..999999 is an
error rather than a seven-digit ID, because a silently wider ID would
break every regex check downstream.
"""

import re

from . import config

DIGITS = 6
MAX_NUMBER = 10**DIGITS - 1

# The regex for every ID kind. dictionary.py uses these for its format
# checks, so the formatter and the validator can never disagree.
#
# [0-9] and not \d on purpose: in Python, \d also matches digits from
# other scripts (Arabic-Indic, Devanagari...), so "EMP-००००01" would pass.
PATTERNS = {
    "role": r"^ROL-[0-9]{6}$",
    "skill": r"^SKL-[0-9]{6}$",
    "employee": r"^EMP-[0-9]{6}$",
    "course": r"^CRS-[0-9]{6}$",
    "offering": r"^OFF-[0-9]{6}$",
    "assessment": r"^ASM-[0-9]{6}$",
    "event": r"^EVT-[0-9]{6}$",
    "completion": r"^CMP-[0-9]{4}-[0-9]{6}$",
    "budget": r"^BUD-[A-Z]{3}-[0-9]{4}$",
    "recommendation": r"^REC-EMP-[0-9]{6}-CRS-[0-9]{6}$",
    "enrollment": r"^ENR-EMP-[0-9]{6}-CRS-[0-9]{6}$",
    "ground_truth": r"^GT-[0-9]{6}$",
    "department": r"^[A-Z]{3}$",
}

_COMPILED = {kind: re.compile(pattern) for kind, pattern in PATTERNS.items()}


def matches(kind, value):
    """True if value is a well-formed ID of this kind."""
    # fullmatch, not match: "$" in Python also matches just before a
    # trailing newline, so match() would accept "EMP-000001\n".
    return isinstance(value, str) and bool(_COMPILED[kind].fullmatch(value))


def _check(kind, value):
    if not matches(kind, value):
        raise ValueError(f"{value!r} is not a valid {kind} id.")
    return value


def _numbered(prefix, number):
    # bool is a subclass of int, and True would quietly become 000001.
    if not isinstance(number, int) or isinstance(number, bool):
        raise ValueError(f"An id number must be an int, got {number!r}.")
    if not 1 <= number <= MAX_NUMBER:
        raise ValueError(f"An id number must be between 1 and {MAX_NUMBER}, got {number}.")
    return f"{prefix}-{number:0{DIGITS}d}"


def role_id(number):
    return _numbered("ROL", number)


def skill_id(number):
    return _numbered("SKL", number)


def employee_id(number):
    return _numbered("EMP", number)


def course_id(number):
    return _numbered("CRS", number)


def offering_id(number):
    return _numbered("OFF", number)


def assessment_id(number):
    return _numbered("ASM", number)


def event_id(number):
    return _numbered("EVT", number)


def ground_truth_id(number):
    return _numbered("GT", number)


def completion_id(number, year=config.FISCAL_YEAR):
    """CMP-2026-000001. The year is part of the ID, as the brief asks."""
    return _numbered(f"CMP-{year}", number)


def budget_id(department_code, year=config.FISCAL_YEAR):
    """BUD-ENG-2026. Only the eight real department codes are accepted."""
    if department_code not in config.DEPARTMENT_CODES:
        raise ValueError(f"{department_code!r} is not a department code.")
    return f"BUD-{department_code}-{year}"


def recommendation_id(employee, course):
    """
    REC-EMP-000001-CRS-000042.

    Built from the pair, like the enrollment ID, so there is no counter and
    an injected recommendation looks exactly like a normal one.
    """
    return f"REC-{_check('employee', employee)}-{_check('course', course)}"


def enrollment_id(employee, course):
    """ENR-EMP-000001-CRS-000042. One per pair, because there are no retakes."""
    return f"ENR-{_check('employee', employee)}-{_check('course', course)}"


def split_pair(pair_id):
    """
    The (employee_id, course_id) inside a REC- or ENR- ID.

    The validator uses this to check that the ID agrees with the row's own
    employee_id and course_id columns.
    """
    if not (matches("recommendation", pair_id) or matches("enrollment", pair_id)):
        raise ValueError(f"{pair_id!r} is not a recommendation or enrollment id.")
    # "ENR-EMP-000001-CRS-000042" -> ["ENR", "EMP", "000001", "CRS", "000042"]
    parts = pair_id.split("-")
    return f"EMP-{parts[2]}", f"CRS-{parts[4]}"


class IdCounter:
    """
    Hands out numbered IDs in the order they are asked for.

    One counter per ID kind per run. Because the stages create rows in a
    fixed order, the same seed always gives the same numbers.
    """

    def __init__(self, formatter):
        self._formatter = formatter
        self._last = 0

    def next(self):
        self._last += 1
        return self._formatter(self._last)

    @property
    def issued(self):
        """How many IDs have been handed out so far."""
        return self._last
