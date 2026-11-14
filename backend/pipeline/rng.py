"""
Seeded random streams, one per stage.

Every stage gets its own generator built from [seed, stage, stream].
If all stages shared one generator, adding a single random draw to s02
would shift every number drawn after it, and the courses in s04 would
change for no visible reason. With separate streams, changing one stage
only changes that stage's data.

`stream` lets one stage keep separate streams for separate jobs. s09 uses
one stream per edge-case type for the same reason.

Only stages/ may import this. rules/ must stay free of randomness.
"""

import numpy as np

from . import config

# Stage numbers, matching the file names in stages/.
REFERENCE = 1
EMPLOYEES = 2
PROFICIENCY = 3
CATALOG = 4
OFFERINGS = 5
BUDGETS = 7
PLAN = 6
SIMULATE = 8
INJECT = 9
FINALIZE = 10

STAGES = (
    REFERENCE,
    EMPLOYEES,
    PROFICIENCY,
    CATALOG,
    OFFERINGS,
    BUDGETS,
    PLAN,
    SIMULATE,
    INJECT,
    FINALIZE,
)


def stage_rng(stage, stream=0, seed=config.SEED):
    """A numpy Generator that depends only on (seed, stage, stream)."""
    if stage not in STAGES:
        raise ValueError(f"Unknown stage {stage!r}.")
    if not isinstance(stream, int) or stream < 0:
        raise ValueError(f"stream must be a non-negative int, got {stream!r}.")
    return np.random.default_rng([seed, stage, stream])
