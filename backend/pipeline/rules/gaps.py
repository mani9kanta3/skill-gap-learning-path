"""
BR-01: the skill gap, and the gap status shown in skill_gap.
"""


def gap(target_level, level):
    """max(0, target - level). Being above target is no gap, not a negative one."""
    return max(0, target_level - level)


def gap_status(planning_gap, current_gap):
    """NO_GAP if there was nothing to close, CLOSED if it was closed, OPEN otherwise."""
    if planning_gap == 0:
        return "NO_GAP"
    if current_gap == 0:
        return "CLOSED"
    return "OPEN"
