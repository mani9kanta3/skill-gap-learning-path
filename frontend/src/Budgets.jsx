import React, { useEffect, useState } from "react";

import api from "./api";
import getErrorMessage from "./errorMessage";
import money, { inWords } from "./money";
import PageHeader from "./PageHeader";
import StatusBadge from "./StatusBadge";

/*
  Department budgets, for the HR partner.

  The numbers per department tell the story in order: what people
  proposed in January, what the limit is, which proposed steps the limit
  was allocated to (the funded plan), and what was actually committed.
  Departments fund less than they propose on purpose. Only funded steps
  can be approved, so a request for an unfunded step is rejected. An
  EXCEEDED badge means something was approved outside the funded plan,
  so the department now owes more than its limit.
*/
function Budgets() {
  const [rows, setRows] = useState([]);
  const [load, setLoad] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/budgets")
      .then((response) => setRows(response.data))
      .catch((err) => setError(getErrorMessage(err, "Could not load budgets.")))
      .finally(() => setLoad(false));
  }, []);

  return (
    <div>
      <PageHeader icon="fa-wallet" title="Budgets" subtitle="Proposed, funded and committed spend per department, 2026." />

      {error && <div className="alert alert-danger">{error}</div>}
      {load && <p className="info-text">Loading ...</p>}

      <div className="row g-3">
        {rows.map((b) => {
          const used = Math.min(100, b.utilization_pct);
          return (
            <div className="col-md-6" key={b.budget_id}>
              <div className="panel corners p-3 h-100">
                <div className="d-flex justify-content-between align-items-start">
                  <div>
                    <div className="fw-bold">{b.department_name}</div>
                    <div className="mono text-muted">{b.budget_id}</div>
                  </div>
                  <StatusBadge status={b.budget_status} />
                </div>

                <div className="bar mt-3" title={`${b.utilization_pct}% of the limit`}>
                  <div className={`bar-fill ${b.utilization_pct > 100 ? "over" : ""}`} style={{ width: `${used}%` }}></div>
                </div>
                <div className="d-flex justify-content-between info-text mt-1">
                  <span>{b.utilization_pct.toFixed(2)}% used</span>
                  <span>{money(b.remaining_amount)} left</span>
                </div>

                <table className="table table-sm data-table mt-2">
                  <tbody>
                    <tr>
                      <td>Proposed in January</td>
                      <td className="text-end">{money(b.planned_amount)}</td>
                      <td className="text-end info-text">{inWords(b.planned_amount)}</td>
                    </tr>
                    <tr>
                      <td>Limit</td>
                      <td className="text-end">{money(b.limit_amount)}</td>
                      <td className="text-end info-text">{inWords(b.limit_amount)}</td>
                    </tr>
                    <tr>
                      <td>Funded plan</td>
                      <td className="text-end">{money(b.funded_amount)}</td>
                      <td className="text-end info-text">{inWords(b.funded_amount)}</td>
                    </tr>
                    <tr>
                      <td>Committed</td>
                      <td className="text-end">{money(b.committed_amount)}</td>
                      <td className="text-end info-text">{inWords(b.committed_amount)}</td>
                    </tr>
                    <tr>
                      <td>Rejected for budget</td>
                      <td className="text-end">{b.budget_rejections}</td>
                      <td className="text-end info-text">of {b.enrollments} requests</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default Budgets;
