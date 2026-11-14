import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import api from "./api";
import getErrorMessage from "./errorMessage";
import money from "./money";
import { PLAN_STATUS, REASONS, label } from "./options";

/*
  Re-plan one employee from any date.

  The planning date and the period are required on purpose: the plan
  only uses what was known on that date (their level then, courses
  passed by then, seats and budget left then) and only runs that start
  at least 14 days later. It is the same engine as the January run, and
  nothing is saved. The result is a proposal: it is not funded until the
  department budget is allocated to it.

  The period has to stay inside the budget year, because there is no
  budget for any other year to check the money against.
*/
const YEAR_START = "2026-01-01";
const YEAR_END = "2026-12-31";
function PathPreview({ employeeId }) {
  const [form, setForm] = useState({
    planning_date: "2026-07-01",
    period_start: "2026-01-01",
    period_end: "2026-12-31",
  });
  const [result, setResult] = useState(null);
  const [load, setLoad] = useState(false);
  const [error, setError] = useState("");

  // A result belongs to one employee. Moving to another employee clears it,
  // so one person's path is never shown under someone else's name.
  // (EmployeeDetail also keys this component by employee ID.)
  useEffect(() => {
    setResult(null);
    setError("");
  }, [employeeId]);

  async function preview(event) {
    event.preventDefault();
    try {
      setLoad(true);
      setError("");
      const response = await api.post("/recommendations/preview", { employee_id: employeeId, ...form });
      setResult(response.data);
    } catch (err) {
      setError(getErrorMessage(err, "Could not build a preview."));
      setResult(null);
    } finally {
      setLoad(false);
    }
  }

  const field = (name, text) => (
    <div className="col-md-3">
      <label className="field-label form-label">{text}</label>
      <input
        type="date"
        className="form-control"
        min={YEAR_START}
        max={YEAR_END}
        value={form[name]}
        onChange={(e) => setForm({ ...form, [name]: e.target.value })}
        disabled={load}
        required
      />
    </div>
  );

  return (
    <div className="panel corners p-4">
      <h2 className="section-title mb-1">
        <i className="fa-solid fa-wand-magic-sparkles me-2 text-brand"></i>
        Preview a path from another date
      </h2>
      <p className="info-text">
        Uses only what was known on the planning date, within the 2026 budget
        year. The result is a proposal, not a funded plan. Nothing is saved.
      </p>

      <form onSubmit={preview} className="row g-3 align-items-end">
        {field("planning_date", "Planning date")}
        {field("period_start", "Period start")}
        {field("period_end", "Period end")}
        <div className="col-md-3">
          <button type="submit" className="btn btn-brand w-100" disabled={load}>
            {load ? "Planning ..." : "Preview path"}
          </button>
        </div>
      </form>

      {error && <div className="alert alert-danger mt-3 mb-0">{error}</div>}

      {result && (
        <div className="mt-4">
          <div className="row g-3 mb-3">
            <div className="col-md-4">
              <div className="tile">
                <div className="tile-label">Path cost</div>
                <div className="tile-value">{money(result.path_cost)}</div>
              </div>
            </div>
            <div className="col-md-4">
              <div className="tile">
                <div className="tile-label">Allowance left</div>
                <div className="tile-value">{money(result.allowance - result.already_spent)}</div>
                <div className="tile-note">of {money(result.allowance)}, {money(result.already_spent)} already spent</div>
              </div>
            </div>
            <div className="col-md-4">
              <div className="tile">
                <div className="tile-label">{result.department_code} budget free</div>
                <div className="tile-value">{money(result.department_free)}</div>
                <div className="tile-note">
                  {money(result.department_limit)} limit, {money(result.department_committed)} committed,{" "}
                  {money(result.department_reserved_for_others)} held for other funded steps, as of {result.planning_date}
                </div>
              </div>
            </div>
          </div>

          {result.path.length === 0 ? (
            <div className="note note-warn">No feasible course could be planned from this date.</div>
          ) : (
            <div className="table-wrap">
              <table className="table data-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Course</th>
                    <th>Why</th>
                    <th>For skill</th>
                    <th>Run</th>
                    <th className="text-end">Cost</th>
                  </tr>
                </thead>
                <tbody>
                  {result.path.map((r) => (
                    <tr key={r.recommendation_id}>
                      <td>{r.path_sequence}</td>
                      <td>
                        <Link to={`/courses/${r.course_id}`}>{r.course_title}</Link>
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
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {result.not_recommended.length > 0 && (
            <>
              <p className="field-label mt-3 mb-1">Turned down</p>
              <ul className="info-text mb-0">
                {result.not_recommended.map((r) => (
                  <li key={r.recommendation_id}>
                    {r.course_title} for {r.target_skill_name}: <strong>{label(REASONS, r.reason_code)}</strong>
                  </li>
                ))}
              </ul>
            </>
          )}

          <p className="field-label mt-3 mb-1">Every gap on that date</p>
          <div className="d-flex flex-wrap gap-2">
            {result.gaps.map((g) => (
              <span className="chip" key={g.skill_id} title={`level ${g.planning_level} of target ${g.target_level}`}>
                {g.skill_name}: {label(PLAN_STATUS, g.plan_status)}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default PathPreview;
