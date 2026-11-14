import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import api from "./api";
import Card from "./Card";
import getErrorMessage from "./errorMessage";
import money from "./money";
import { FUNDING, PLAN_STATUS, REASONS, label } from "./options";
import PageHeader from "./PageHeader";
import PathPreview from "./PathPreview";
import StatCard from "./StatCard";
import StatusBadge from "./StatusBadge";

/*
  One employee, the whole workflow for one person.

  A profile card on top answers "who is this and where are they heading".
  Below it, tabs split the rest so nothing has to scroll for ever:

    Skill gaps      target vs level at planning and now
    Learning path   what was proposed, what was funded, what was turned down
    Enrollments     every request with its event history and results
    Re-plan         the same engine, run from another date

  The tab is kept in state, and reset to the first one when you move to
  another employee.
*/
const TABS = [
  ["gaps", "Skill gaps"],
  ["path", "Learning path"],
  ["enrollments", "Enrollments and results"],
  ["replan", "Re-plan from a date"],
];

export function Levels({ level, target }) {
  return (
    <span className="level-dots" title={`level ${level} of 5, target ${target}`}>
      {[1, 2, 3, 4, 5].map((n) => (
        <span key={n} className={`level-dot ${n <= level ? "on" : ""} ${n === target ? "target" : ""}`}></span>
      ))}
    </span>
  );
}

function initials(employee) {
  return `${employee.first_name[0]}${employee.last_name[0]}`;
}

function EmployeeDetail() {
  const { id } = useParams();
  const [employee, setEmployee] = useState(null);
  const [tab, setTab] = useState("gaps");
  const [load, setLoad] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoad(true);
    setTab("gaps");
    api
      .get(`/employees/${id}`)
      .then((response) => {
        setEmployee(response.data);
        setError("");
      })
      .catch((err) => setError(getErrorMessage(err, "Could not load this employee.")))
      .finally(() => setLoad(false));
  }, [id]);

  if (load) {
    return <p className="loading">Loading ...</p>;
  }
  if (error) {
    return <div className="alert alert-danger">{error}</div>;
  }

  const path = employee.recommendations.filter((r) => r.decision === "RECOMMENDED");
  const funded = path.filter((r) => r.funding_status === "FUNDED");
  const turnedDown = employee.recommendations.filter((r) => r.decision === "NOT_RECOMMENDED");
  const openGaps = employee.gaps.filter((g) => g.gap_status === "OPEN").length;
  const closedGaps = employee.gaps.filter((g) => g.gap_status === "CLOSED").length;
  const counts = {
    gaps: employee.gaps.length,
    path: path.length,
    enrollments: employee.enrollments.length,
  };

  return (
    <div>
      <PageHeader eyebrow="People" title="Employee profile">
        <Link className="btn-quiet" to="/employees">
          <i className="fa-solid fa-arrow-left me-2"></i>All employees
        </Link>
      </PageHeader>

      <Card>
        <div className="profile">
          <span className="avatar">{initials(employee)}</span>
          <div>
            <div className="page-title mb-0">
              {employee.first_name} {employee.last_name}
            </div>
            <div className="muted">
              {employee.employee_id} · {employee.department_name} · {employee.role_title}
            </div>
          </div>
          <div className="ms-auto">
            <StatusBadge status={employee.employment_status} />
          </div>
        </div>
        <div className="facts">
          <div>
            <div className="fact-label">Working towards</div>
            <div className="fact-value">{employee.target_role_title}</div>
            <div className="muted small-text">
              {employee.target_role_id !== employee.role_id ? "Career pathway: next role up" : "Growing in the current role"}
            </div>
          </div>
          <div>
            <div className="fact-label">Manager</div>
            {employee.manager_id ? (
              <>
                <div className="fact-value">
                  <Link to={`/employees/${employee.manager_id}`}>
                    {employee.manager_first_name} {employee.manager_last_name}
                  </Link>
                </div>
                <Link className="small-text" to={`/employees?manager_id=${employee.manager_id}`}>
                  See the whole team
                </Link>
              </>
            ) : (
              <div className="fact-value">None (top of the ladder)</div>
            )}
          </div>
          <div>
            <div className="fact-label">Hired</div>
            <div className="fact-value">{employee.hire_date}</div>
          </div>
        </div>
      </Card>

      <div className="row g-3 mb-4">
        <div className="col-6 col-lg-3">
          <StatCard label="Gaps still open" value={openGaps} tone={openGaps ? "wait" : ""} />
        </div>
        <div className="col-6 col-lg-3">
          <StatCard label="Gaps closed" value={closedGaps} tone={closedGaps ? "good" : ""} />
        </div>
        <div className="col-6 col-lg-3">
          <StatCard label="Courses proposed" value={path.length} note={`${funded.length} funded`} tone="primary" />
        </div>
        <div className="col-6 col-lg-3">
          <StatCard
            label="Funded cost"
            value={money(funded.reduce((s, r) => s + r.estimated_cost, 0))}
            note={`of ${money(path.reduce((s, r) => s + r.estimated_cost, 0))} proposed`}
          />
        </div>
      </div>

      <div className="tabs" role="tablist">
        {TABS.map(([key, text]) => (
          <button
            key={key}
            type="button"
            role="tab"
            className={`tab ${tab === key ? "active" : ""}`}
            onClick={() => setTab(key)}
          >
            {text}
            {counts[key] !== undefined && <span className="tab-count">{counts[key]}</span>}
          </button>
        ))}
      </div>

      {tab === "gaps" && (
        <Card title="Skill gaps against the target role" subtitle="Orange ring = target level. Filled dots = assessed level." flush>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Skill</th>
                  <th>Importance</th>
                  <th>At planning</th>
                  <th>Now</th>
                  <th className="text-end">Gap then / now</th>
                  <th>Plan</th>
                  <th>Result</th>
                </tr>
              </thead>
              <tbody>
                {employee.gaps.map((g) => (
                  <tr key={g.skill_id}>
                    <td>
                      <span className="cell-main">{g.skill_name}</span>
                      <div className="mono">{g.skill_id}</div>
                    </td>
                    <td>{g.importance.toLowerCase()}</td>
                    <td>
                      <Levels level={g.planning_level} target={g.target_level} />{" "}
                      <span className="small-text muted ms-1">
                        {g.planning_level}/{g.target_level}
                      </span>
                    </td>
                    <td>
                      <Levels level={g.current_level} target={g.target_level} />{" "}
                      <span className="small-text muted ms-1">
                        {g.current_level}/{g.target_level}
                      </span>
                    </td>
                    <td className="text-end">
                      {g.planning_gap} / {g.current_gap}
                    </td>
                    <td>{label(PLAN_STATUS, g.plan_status)}</td>
                    <td>
                      <StatusBadge status={g.gap_status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {tab === "path" && (
        <>
          <Card
            title="January learning path"
            subtitle="Proposed in the planning run on 5 Jan 2026, then funded (or not) when the department budget was allocated."
            flush
          >
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Course</th>
                    <th>Why</th>
                    <th>For skill</th>
                    <th>Planned run</th>
                    <th className="text-end">Cost</th>
                    <th className="text-end">Running total</th>
                    <th>Funding</th>
                    <th>Enrollment</th>
                  </tr>
                </thead>
                <tbody>
                  {path.map((r) => (
                    <tr key={r.recommendation_id}>
                      <td>{r.path_sequence}</td>
                      <td>
                        <Link className="cell-main" to={`/courses/${r.course_id}`}>
                          {r.course_title}
                        </Link>
                        <div className="mono">{r.course_id}</div>
                      </td>
                      <td>
                        {label(REASONS, r.reason_code)}
                        {r.required_for_title && <div className="muted small-text">before {r.required_for_title}</div>}
                      </td>
                      <td>{r.target_skill_name}</td>
                      <td className="text-nowrap">
                        {r.planned_start_date} → {r.planned_end_date}
                      </td>
                      <td className="text-end">{money(r.estimated_cost)}</td>
                      <td className="text-end">{money(r.cumulative_cost)}</td>
                      <td>
                        <StatusBadge status={r.funding_status} text={label(FUNDING, r.funding_status)} />
                      </td>
                      <td>
                        {r.enrollment_status ? (
                          <StatusBadge status={r.enrollment_status} />
                        ) : (
                          <span className="muted small-text">not requested</span>
                        )}
                      </td>
                    </tr>
                  ))}
                  {path.length === 0 && (
                    <tr>
                      <td colSpan="9" className="empty-row">
                        No path: {employee.employment_status === "ON_LEAVE" ? "the employee is on leave." : "no gap could be planned."}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>

          <Card title="Considered and turned down" subtitle="Every course the engine looked at and did not use, with the reason." flush>
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Course</th>
                    <th>For skill</th>
                    <th>Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {turnedDown.map((r) => (
                    <tr key={r.recommendation_id}>
                      <td>
                        <Link to={`/courses/${r.course_id}`}>{r.course_title}</Link>
                      </td>
                      <td>{r.target_skill_name}</td>
                      <td>{label(REASONS, r.reason_code)}</td>
                    </tr>
                  ))}
                  {turnedDown.length === 0 && (
                    <tr>
                      <td colSpan="3" className="empty-row">
                        Nothing was turned down.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}

      {tab === "enrollments" && (
        <>
          {employee.enrollments.length === 0 && <Card>No enrollments yet.</Card>}
          <div className="row g-3">
            {employee.enrollments.map((e) => (
              <div className="col-lg-6" key={e.enrollment_id}>
                <Card
                  title={
                    <Link to={`/courses/${e.course_id}`} className="text-reset">
                      {e.course_title}
                    </Link>
                  }
                  subtitle={`${e.start_date} → ${e.end_date} · ${money(e.cost_amount)}`}
                  actions={<StatusBadge status={e.current_status} />}
                >
                  <ul className="timeline">
                    {e.events.map((ev) => (
                      <li key={ev.event_id}>
                        <span className="muted">{ev.event_on}</span> <strong>{ev.to_status.replaceAll("_", " ").toLowerCase()}</strong> by{" "}
                        {ev.actor.replace("_", " ").toLowerCase()}
                        {ev.reason_code && ` (${ev.reason_code.replaceAll("_", " ").toLowerCase()})`}
                      </li>
                    ))}
                  </ul>
                  {e.completions.map((c) => (
                    <div className="outcome" key={c.completion_id}>
                      <div className="d-flex justify-content-between">
                        <span>
                          Attendance {c.attendance_pct}% · exam {c.final_score}
                        </span>
                        <StatusBadge status={c.result} />
                      </div>
                      <div className="mt-1">
                        <strong>Learning outcome: </strong>
                        {c.assessment_id
                          ? `post-course test ${c.post_score}, level ${c.post_level} (${c.assessed_on})`
                          : "no post-course test recorded"}
                      </div>
                    </div>
                  ))}
                  <div className="mono mt-2">{e.enrollment_id}</div>
                </Card>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Keyed by employee, so a preview never carries over to another person. */}
      {tab === "replan" && <PathPreview key={employee.employee_id} employeeId={employee.employee_id} />}
    </div>
  );
}

export default EmployeeDetail;
