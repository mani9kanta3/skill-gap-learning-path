"""
Run the stages in order and return the finished tables.

    s01..s05  masters and catalog
    s06       January plan
    s07       budgets (set from the plan, see s07_budgets)
    s08       2026 event simulation
    s09       labelled edge cases (skipped with inject=False)
    s10       assessment IDs and every derived column

With inject=False the result is the clean baseline: it must pass every
check with zero failures, which is how we know the baseline is valid
before anything is broken on purpose.
"""

from . import config
from .stages import (
    s01_reference,
    s02_employees,
    s03_proficiency,
    s04_catalog,
    s05_offerings,
    s06_plan,
    s07_budgets,
    s08_simulate,
    s09_inject,
    s10_finalize,
)


def generate(scale_name, inject=True):
    plan = config.check_scale(config.get_scale(scale_name))
    tables = {}
    for stage in (s01_reference, s02_employees, s03_proficiency, s04_catalog, s05_offerings, s06_plan, s07_budgets):
        stage.run(tables, plan)
    simulation = s08_simulate.run(tables, plan)
    if inject:
        s09_inject.run(tables, plan, simulation)
    else:
        tables["ground_truth"] = []
    s10_finalize.run(tables, plan)
    return tables, plan
