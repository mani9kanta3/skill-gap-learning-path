"""
Request models. The preview is the only endpoint that takes a body, and
its dates are checked here so a bad request gets a 422 that names the
problem, before any query runs.
"""

from datetime import date

from pydantic import BaseModel, Field, model_validator

from pipeline import config


class PreviewRequest(BaseModel):
    employee_id: str = Field(pattern=r"^EMP-[0-9]{6}$", examples=["EMP-000001"])
    planning_date: date = Field(description="The plan only uses data dated on or before this day (BR-20).")
    period_start: date
    period_end: date

    @model_validator(mode="after")
    def dates_make_sense(self):
        # Budgets exist for one fiscal year only. A period outside it would
        # be checked against the wrong year's money, so it is refused.
        first, last = config.PERIOD_START, config.PERIOD_END
        if not (first <= self.period_start and self.period_end <= last):
            raise ValueError(
                f"The period must fall inside the {config.FISCAL_YEAR} budget year "
                f"({first.isoformat()} to {last.isoformat()})."
            )
        if self.period_end <= self.period_start:
            raise ValueError("period_end must be after period_start.")
        if not self.period_start <= self.planning_date <= self.period_end:
            raise ValueError("planning_date must be inside the period.")
        return self
