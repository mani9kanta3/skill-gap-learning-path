"""
The API. Read-only, plus a path preview that saves nothing.

    uvicorn app.main:app --reload        (from backend/)
    http://localhost:8000/docs
"""

from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from pipeline import config as pipeline_config
from pipeline import dictionary

from . import config, queries
from .schemas import PreviewRequest

app = FastAPI(
    title="Skill Gap to Learning Path API",
    description="Skill gaps, learning paths, enrollments, budgets and data-quality results.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Literal[...] of a tuple means "one of these values", so FastAPI rejects
# anything else with a 422 before a query runs.
IssueType = Literal[dictionary.ISSUE_TYPE]  # type: ignore[valid-type]
Department = Literal[pipeline_config.DEPARTMENT_CODES]  # type: ignore[valid-type]


def _not_found(what):
    raise HTTPException(status_code=404, detail=f"No {what} with that id.")


@app.get("/api/health")
def health():
    try:
        return queries.health()
    except Exception:
        raise HTTPException(status_code=503, detail="The database is not reachable.")


@app.get("/api/summary")
def summary():
    return queries.summary()


@app.get("/api/departments")
def departments():
    return queries.departments()


@app.get("/api/skills/categories")
def skill_categories():
    return queries.skill_categories()


@app.get("/api/employees")
def list_employees(
    search: str = "",
    department: Optional[Department] = None,
    manager_id: Optional[str] = Query(None, pattern=r"^EMP-[0-9]{6}$"),
    status: Optional[Literal["ACTIVE", "ON_LEAVE"]] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return queries.list_employees(search, department, manager_id, status, limit, offset)


@app.get("/api/employees/{employee_id}")
def employee_detail(employee_id: str):
    result = queries.employee_detail(employee_id)
    if result is None:
        _not_found("employee")
    return result


@app.post("/api/recommendations/preview")
def preview(request: PreviewRequest):
    result = queries.preview_path(
        request.employee_id, request.planning_date, request.period_start, request.period_end
    )
    if result is None:
        _not_found("employee")
    return result


@app.get("/api/courses")
def list_courses(
    search: str = "",
    category: Optional[str] = None,
    level: Optional[Literal["FOUNDATION", "INTERMEDIATE", "ADVANCED"]] = None,
    available: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return queries.list_courses(search, category, level, available, limit, offset)


@app.get("/api/courses/{course_id}")
def course_detail(course_id: str):
    result = queries.course_detail(course_id)
    if result is None:
        _not_found("course")
    return result


@app.get("/api/budgets")
def budgets():
    return queries.budgets()


@app.get("/api/exceptions")
def exceptions(
    issue_type: Optional[IssueType] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    return queries.exceptions(issue_type, limit, offset)


@app.get("/api/evaluation")
def evaluation():
    return queries.evaluation()
