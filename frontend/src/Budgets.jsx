import React, { useEffect, useState } from "react";

import api from "./api";
import BarList from "./BarList";
import Card from "./Card";
import getErrorMessage from "./errorMessage";
import money, { inWords } from "./money";
import PageHeader from "./PageHeader";
import StatCard from "./StatCard";
import StatusBadge from "./StatusBadge";

/*
  Department budgets, for the HR partner.

  The numbers tell the story in order: what people proposed in January,
  the limit, the part of the proposals the limit was allocated to (the
  funded plan), and what was actually committed. Departments fund less
  than they propose on purpose. Only funded steps can be approved, so a
  request for an unfunded one is rejected. EXCEEDED means something was
  approved outside the funded plan, so the department now owes more than
  its limit.

  One table for comparing departments side by side, one chart for seeing
  at a glance how much of each budget has been used.
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

  const total = (key) => rows.reduce((sum, b) => sum + Number(b[key]), 0);
  const rejections = rows.reduce((sum, b) => sum + b.budget_rejections, 0);

  return (
    <div>
      <PageHeader
        eyebrow="Budget"
        title="Department budgets"
        subtitle="Proposed, funded and committed spend per department for 2026."
      />

      {error && <div className="alert alert-danger">{error}</div>}
      {load && <p className="loading">Loading ...</p>}

      {rows.length > 0 && (
        <>
          <div className="row g-3 mb-4">
            <div className="col-6 col-lg-3">
              <StatCard label="Proposed in January" value={inWords(total("planned_amount"))} note="what people asked for" />
            </div>
            <div className="col-6 col-lg-3">
              <StatCard label="Total limit" value={inWords(total("limit_amount"))} note="85% of proposed" tone="primary" />
            </div>
            <div className="col-6 col-lg-3">
              <StatCard label="Committed" value={inWords(total("committed_amount"))} note="approved enrollments" />
            </div>
            <div className="col-6 col-lg-3">
              <StatCard label="Rejected for budget" value={rejections} note="requests for unfunded steps" tone="wait" />
            </div>
          </div>

          <Card title="Budget used" subtitle="Bar = committed spend. Black line = the department's limit.">
            <BarList
              items={rows.map((b) => ({
                label: b.department_name,
                value: b.committed_amount,
                marker: b.limit_amount,
                display: `${b.utilization_pct.toFixed(1)}%`,
              }))}
            />
          </Card>

          <Card title="By department" flush>
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Department</th>
                    <th className="text-end">Proposed</th>
                    <th className="text-end">Limit</th>
                    <th className="text-end">Funded plan</th>
                    <th className="text-end">Committed</th>
                    <th className="text-end">Left</th>
                    <th className="text-end">Used</th>
                    <th className="text-end">Rejected for budget</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((b) => (
                    <tr key={b.budget_id}>
                      <td>
                        <span className="cell-main">{b.department_name}</span>
                        <div className="mono">{b.budget_id}</div>
                      </td>
                      <td className="text-end">{money(b.planned_amount)}</td>
                      <td className="text-end">{money(b.limit_amount)}</td>
                      <td className="text-end">{money(b.funded_amount)}</td>
                      <td className="text-end">{money(b.committed_amount)}</td>
                      <td className="text-end">{money(b.remaining_amount)}</td>
                      <td className="text-end">{b.utilization_pct.toFixed(1)}%</td>
                      <td className="text-end">
                        {b.budget_rejections} <span className="muted small-text">/ {b.enrollments}</span>
                      </td>
                      <td>
                        <StatusBadge status={b.budget_status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}

export default Budgets;
