"""
Learning outcome rules: BR-14 (pass/fail), BR-15 (score bands), BR-16 (cap).

Every random number (the exam score, the attendance, the noise on the
post-course test) is drawn in the simulation and passed in. These
functions only turn evidence into results, so the validator can recompute
every result here from the stored scores.
"""

import math

from .. import config


def round_half_up(value):
    """
    Round .5 upwards.

    Python's round() sends 2.5 to 2 and 3.5 to 4 (banker's rounding). A
    score of 69.5 becoming 70 or 69 depending on the digit before it would
    be very hard to explain, so every score uses this instead.
    """
    return int(math.floor(value + 0.5))


def clip(value, low, high):
    return max(low, min(high, value))


def band(score):
    """BR-15: the proficiency level a 0..100 score falls in."""
    if not 0 <= score <= 100:
        raise ValueError(f"A score must be between 0 and 100, got {score}.")
    for level, (low, high) in config.SCORE_BANDS.items():
        if low <= score <= high:
            return level
    raise ValueError(f"No band holds score {score}.")  # unreachable: bands cover 0..100


def band_bottom(level):
    return config.SCORE_BANDS[level][0]


def band_top(level):
    return config.SCORE_BANDS[level][1]


def completion_result(attendance_pct, final_score):
    """BR-14: PASSED needs both enough attendance and a high enough score."""
    passed = attendance_pct >= config.PASS_MIN_ATTENDANCE and final_score >= config.PASS_MIN_SCORE
    return "PASSED" if passed else "FAILED"


def entry_level(primary_target_level):
    """The level a course expects a learner to start from."""
    return max(0, primary_target_level - 2)


def final_score_mean(pre_level, primary_target_level):
    """
    The expected exam score. Someone who starts above the course's entry
    level does better, someone below it does worse.
    """
    low, high = config.FINAL_SCORE_MEAN_RANGE
    raw = config.FINAL_SCORE_BASE_MEAN + config.FINAL_SCORE_STEP * (
        pre_level - entry_level(primary_target_level)
    )
    return clip(raw, low, high)


def uplift(final_score, result):
    """How many score points a course adds to the post-course test."""
    if result == "PASSED":
        return config.UPLIFT_PASSED * (final_score - config.UPLIFT_FLOOR)
    return config.UPLIFT_FAILED * max(0, final_score - config.UPLIFT_FLOOR)


def post_course_score(pre_score, final_score, result, noise, course_target_level):
    """
    BR-16: the post-course test score.

    pre_score + uplift + noise, kept inside 0..100, and never above the top
    of the band for the level this course can certify.
    """
    raw = clip(round_half_up(pre_score + uplift(final_score, result) + noise), 0, 100)
    return min(band_top(course_target_level), raw)
