import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import api from "./api";
import getErrorMessage from "./errorMessage";
import money from "./money";
import { PLAN_STATUS, REASONS, label } from "./options";
import PageHeader from "./PageHeader";
import PathPreview from "./PathPreview";
import StatusBadge from "./StatusBadge";

/*
  One employee: the whole workflow for one person, top to bottom.

  1. Skill gaps against the target role, at planning time and now.
  2. The January learning path, with the reason for every course, and the
     courses that were considered and turned down, with why.
  3. Enrollments with their full event history.
  4. Results, where completion, passing and the post-course test sit side
     by side, because finishing a course and closing a gap are different
     things.
  5. A preview that re-plans from any date.
*/
export function Levels({ level, target }) {
  return (
    <span className="level-dots" title={`level ${level} of 5, target ${target}`}>
      {[1, 2, 3, 4, 5].map((n) => (
        <span key={n} className={`level-dot ${n <= level ? "on" : ""} ${n === target ? "target" : ""}`}></span>
      ))}
    </span>
  );
}

function EmployeeDetail() {
  const { id } = useParams();
  const [employee, setEmployee] = useState(null);
  const [load, setLoad] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoad(true);
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
    return <p className="info-text">Loading ...</p>;
  }
  if (error) {
    return <div className="alert alert-danger">{error}</div>;
  }

  const path = employee.recommendations.filter((r) => r.decision === "RECOMMENDED");
  const turnedDown = employee.recommendations.filter((r) => r.decision === "NOT_RECOMMENDED");
  const careerPath = employee.target_role_id !== employee.role_id;

  return (
    <div>
      <PageHeader
        icon="fa-user"
        title={`${employee.first_name} ${employee.last_name}`}
        subtitle={`${employee.employee_id} · ${employee.department_name} · ${employee.role_title}`}
      >
        <StatusBadge status={employee.employment_status} />
      </PageHeader>

      <div className="row g-3 mb-4">
        <div className="col-md-4">
          <div className="tile">
            <div className="tile-label">Working towards</div>
            <div className="fw-bold">{employee.target_role_title}</div>
            <div className="tile-note">{careerPath ? "Career pathway: the next role up" : "Growing in the current role"}</div>
          </div>
        </div>
        <div className="col-md-4">
          <div className="tile">
            <div className="tile-label">Manager</div>
            {employee.manager_id ? (
              <>
                <Link className="fw-bold" to={`/employees/${employee.manager_id}`}>
                  {employee.manager_first_name} {employee.manager_last_name}
                </Link>
                <div className="tile-note">
                  <Link to={`/employees?manager_id=${employee.manager_id}`}>See the whole team</Link>
                </div>
              </>
            ) : (
              <div className="fw-bold">None (top of the ladder)</div>
            )}
          </div>
        </div>
        <div className="col-md-4">
          <div className="tile">
            <div className="tile-label">January plan</div>
            <div className="fw-bold">{path.length} courses · {money(path.reduce((s, r) => s + r.estimated_cost, 0))}</div>
            <div className="tile-note">{turnedDown.length} courses considered and turned down</div>
          </div>
        </div>
      </div>

      {/* 1. Gaps */}
      <h2 className="section-title mb-2">Skill gaps</h2>
      <div className="panel corners table-wrap mb-4">
        <table className="table data-table">
          <thead>
            <tr>
              <th>Skill</th>
              <th>Importance</th>
              <th>At planning</th>
              <th>Now</th>
              <th className="text-end">Gap then / now</th>
              <th>Plan</th>
              <th>Gap</th>
            </tr>
          </thead>
          <tbody>
            {employee.gaps.map((g) => (
              <tr key={g.skill_id}>
                <td>
                  {g.skill_name}
                  <div className="mono text-muted">{g.skill_id}</div>
                </td>
                <td>{g.importance}</td>
                <td>
                  <Levels level={g.planning_level} target={g.target_level} /> <span className="ms-1">{g.planning_level}/{g.target_level}</span>
                </td>
                <td>
                  <Levels level={g.current_level} target={g.target_level} /> <span className="ms-1">{g.current_level}/{g.target_level}</span>
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

      {/* 2. Path */}
      <h2 className="section-title mb-2">January learning path</h2>
      <div className="panel corners table-wrap mb-3">
        <table className="table data-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Course</th>
              <th>Why</th>
              <th>For skill</th>
              <th>Planned run</th>
              <th className="text-end">Cost</th>
              <th className="text-end">Running total</th>
              <th>Enrollment</th>
            </tr>
          </thead>
          <tbody>
            {path.map((r) => (
              <tr key={r.recommendation_id}>
                <td>{r.path_sequence}</td>
                <td>
                  <Link to={`/courses/${r.course_id}`}>{r.course_title}</Link>
                  <div className="mono text-muted">{r.course_id}</div>
                </td>
                <td>
                  {label(REASONS, r.reason_code)}
                  {r.required_for_title && <div className="info-text">before {r.required_for_title}</div>}
                </td>
                <td>{r.target_skill_name}</td>
                <td className="text-nowrap">
                  {r.planned_start_date} → {r.planned_end_date}
                </td>
                <td className="text-end">{money(r.estimated_cost)}</td>
                <td className="text-end">{money(r.cumulative_cost)}</td>
                <td>{r.enrollment_status ? <StatusBadge status={r.enrollment_status} /> : <span className="info-text">not requested</span>}</td>
              </tr>
            ))}
            {path.length === 0 && (
              <tr>
                <td colSpan="8" className="info-text text-center py-3">
                  No path: {employee.employment_status === "ON_LEAVE" ? "the employee is on leave." : "no gap could be planned."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {turnedDown.length > 0 && (
        <div className="panel corners p-3 mb-4">
          <p className="field-label mb-2">Considered and turned down</p>
          <ul className="mb-0 info-text">
            {turnedDown.map((r) => (
              <li key={r.recommendation_id}>
                <Link to={`/courses/${r.course_id}`}>{r.course_title}</Link> for {r.target_skill_name}:{" "}
                <strong>{label(REASONS, r.reason_code)}</strong>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 3 and 4. Enrollments and results */}
      <h2 className="section-title mb-2">Enrollments and results</h2>
      {employee.enrollments.length === 0 && <p className="info-text">No enrollments yet.</p>}
      <div className="row g-3 mb-4">
        {employee.enrollments.map((e) => (
          <div className="col-md-6" key={e.enrollment_id}>
            <div className="panel corners p-3 h-100">
              <div className="d-flex justify-content-between align-items-start gap-2">
                <div>
                  <Link className="fw-bold" to={`/courses/${e.course_id}`}>
                    {e.course_title}
                  </Link>
                  <div className="mono text-muted">{e.enrollment_id}</div>
                </div>
                <StatusBadge status={e.current_status} />
              </div>
              <p className="info-text mb-2">
                Runs {e.start_date} → {e.end_date} · {money(e.cost_amount)}
              </p>
              <ul className="timeline mb-2">
                {e.events.map((ev) => (
                  <li key={ev.event_id}>
                    {ev.event_on}: <strong>{ev.to_status.replaceAll("_", " ")}</strong> by {ev.actor.replace("_", " ").toLowerCase()}
                    {ev.reason_code && ` (${ev.reason_code.replaceAll("_", " ").toLowerCase()})`}
                  </li>
                ))}
              </ul>
              {e.completions.map((c) => (
                <div className="note mt-2" key={c.completion_id}>
                  <div>
                    <strong>Completion</strong> {c.completion_id}: attendance {c.attendance_pct}%, exam {c.final_score}{" "}
                    <StatusBadge status={c.result} />
                  </div>
                  <div className="mt-1">
                    <strong>Learning outcome:</strong>{" "}
                    {c.assessment_id
                      ? `post-course test ${c.post_score} on ${c.assessed_on}, level ${c.post_level}`
                      : "no post-course test recorded"}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* 5. Preview */}
      <PathPreview employeeId={employee.employee_id} />
    </div>
  );
}

export default EmployeeDetail;
