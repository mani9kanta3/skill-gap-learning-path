"""
Small helpers the stages share: splitting a total by shares, picking from
weighted options, and drawing dates. All take the stage's own generator.
"""

import math
from datetime import date, timedelta


def allocate(total, shares, minimum=0):
    """
    Split total into whole numbers by shares, summing exactly to total.

    Largest remainder: everyone gets the floor of their share, then the
    leftover units go to the biggest fractional parts (ties by key order).
    `minimum` then lifts any part below it, taking units from the largest.
    """
    keys = list(shares)
    exact = {k: total * shares[k] for k in keys}
    counts = {k: math.floor(exact[k]) for k in keys}
    leftover = total - sum(counts.values())
    order = sorted(keys, key=lambda k: (-(exact[k] - counts[k]), keys.index(k)))
    for k in order[:leftover]:
        counts[k] += 1

    for k in keys:
        while counts[k] < minimum:
            donor = max(keys, key=lambda d: (counts[d], -keys.index(d)))
            if counts[donor] <= minimum:
                raise ValueError(f"Cannot give every part at least {minimum} out of {total}.")
            counts[donor] -= 1
            counts[k] += 1
    return counts


def pick(rng, shares):
    """One key from a {key: probability} dict."""
    keys = list(shares)
    probabilities = [shares[k] for k in keys]
    return keys[int(rng.choice(len(keys), p=probabilities))]


def uniform_int(rng, low, high):
    """An int in [low, high], both ends included."""
    return int(rng.integers(low, high + 1))


def random_date(rng, start, end):
    """A date in [start, end], both ends included."""
    return start + timedelta(days=uniform_int(rng, 0, (end - start).days))


def mondays(start, end):
    """Every Monday from start to end. start must itself be a Monday."""
    if start.weekday() != 0:
        raise ValueError(f"{start} is not a Monday.")
    days = []
    day = start
    while day <= end:
        days.append(day)
        day += timedelta(days=7)
    return days


def days(n):
    return timedelta(days=n)


def as_date(value):
    """Accept a date or an ISO string."""
    return value if isinstance(value, date) else date.fromisoformat(value)
