import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import api from "./api";
import Card from "./Card";
import getErrorMessage from "./errorMessage";
import money from "./money";
import { PLAN_STATUS, REASONS, label } from "./options";
import StatCard from "./StatCard";

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
    period_start: YEAR_START,
    period_end: YEAR_END,
  });
  const [result, setResult] = useState(null);
  const [load, setLoad] = useState(false);
  const [error, setError] = useState("");

  // A result belongs to one employee. Moving to another employee clears it,
  // so one person's path is never shown under someone else's name.
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
    <div className="field">
      <label className="field-label">{text}</label>
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
    <>
      <Card
        title="Re-plan from another date"
        subtitle="Uses only what was known on the planning date, inside the 2026 budget year. The result is a proposal, not a funded plan. Nothing is saved."
      >
        <form onSubmit={preview} className="toolbar">
          {field("planning_date", "Planning date")}
          {field("period_start", "Period start")}
          {field("period_end", "Period end")}
          <div className="field" style={{ flexGrow: 0 }}>
            <button type="submit" className="btn-primary-app" disabled={load}>
              {load ? "Planning ..." : "Build proposal"}
            </button>
          </div>
        </form>
        {error && <div className="alert alert-danger mt-3 mb-0">{error}</div>}
      </Card>

      {result && (
        <>
          <div className="row g-3 mb-4">
            <div className="col-md-4">
              <StatCard label="Proposed path cost" value={money(result.path_cost)} tone="primary" />
            </div>
            <div className="col-md-4">
              <StatCard
                label="Allowance left"
                value={money(result.allowance - result.already_spent)}
                note={`of ${money(result.allowance)}; ${money(result.already_spent)} already spent`}
              />
            </div>
            <div className="col-md-4">
              <StatCard
                label={`${result.department_code} budget free`}
                value={money(result.department_free)}
                note={`${money(result.department_limit)} limit − ${money(result.department_committed)} committed − ${money(
                  result.department_reserved_for_others
                )} held for other funded steps`}
              />
            </div>
          </div>

          <Card title={`Proposed path as of ${result.planning_date}`} flush>
            <div className="table-wrap">
              <table className="data-table">
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
                        <Link className="cell-main" to={`/courses/${r.course_id}`}>
                          {r.course_title}
                        </Link>
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
                    </tr>
                  ))}
                  {result.path.length === 0 && (
                    <tr>
                      <td colSpan="6" className="empty-row">
                        No feasible course could be planned from this date.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>

          <div className="row g-3">
            <div className="col-lg-6">
              <Card title="Turned down">
                {result.not_recommended.length === 0 ? (
                  <span className="muted">Nothing was turned down.</span>
                ) : (
                  <ul className="mb-0 small-text">
                    {result.not_recommended.map((r) => (
                      <li key={r.recommendation_id}>
                        {r.course_title} for {r.target_skill_name}: <strong>{label(REASONS, r.reason_code)}</strong>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
            </div>
            <div className="col-lg-6">
              <Card title="Every gap on that date">
                <div className="d-flex flex-wrap gap-2">
                  {result.gaps.map((g) => (
                    <span className="chip" key={g.skill_id} title={`level ${g.planning_level} of target ${g.target_level}`}>
                      {g.skill_name}: {label(PLAN_STATUS, g.plan_status)}
                    </span>
                  ))}
                </div>
              </Card>
            </div>
          </div>
        </>
      )}
    </>
  );
}

export default PathPreview;
