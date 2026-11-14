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

  A budget answers two different questions, and this page keeps them
  apart so they cannot be confused:

  1. Is the department over-committed?  (the status)
     Obligations = money promised to funded steps in January
                 + approvals of steps that were never funded.
     If obligations are above the limit, the department has promised more
     than it has, even if most of it is not spent yet. That is what the
     "Over-committed" badge means, and the reason is shown next to it.

  2. How much has been spent so far?  (cash)
     Committed = approved enrollments to date. "Not yet spent" is
     limit - committed. A department can have money not yet spent and
     still be over-committed, because funded steps later in the year will
     use it.
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
  const outsideCount = rows.reduce((sum, b) => sum + b.outside_plan_count, 0);
  const overCommitted = rows.filter((b) => b.budget_status === "EXCEEDED");

  return (
    <div>
      <PageHeader
        eyebrow="Budget"
        title="Department budgets"
        subtitle="What each department promised (obligations) and what it has spent so far, against its 2026 limit."
      />

      {error && <div className="alert alert-danger">{error}</div>}
      {load && <p className="loading">Loading ...</p>}

      {rows.length > 0 && (
        <>
          <div className="row g-3 mb-4">
            <div className="col-6 col-lg-3">
              <StatCard label="Total limit" value={inWords(total("limit_amount"))} note="85% of what was proposed" tone="primary" />
            </div>
            <div className="col-6 col-lg-3">
              <StatCard label="Promised to funded steps" value={inWords(total("funded_amount"))} note="the January allocation" />
            </div>
            <div className="col-6 col-lg-3">
              <StatCard
                label="Approved outside the plan"
                value={money(total("outside_plan_amount"))}
                note={`${outsideCount} enrollments that were never funded`}
                tone={outsideCount ? "stop" : ""}
              />
            </div>
            <div className="col-6 col-lg-3">
              <StatCard
                label="Spent so far"
                value={inWords(total("committed_amount"))}
                note={`${total("budget_rejections")} requests rejected for budget`}
              />
            </div>
          </div>

          {overCommitted.length > 0 && (
            <div className="note note-warn mb-4">
              <strong>
                {overCommitted.length} of {rows.length} departments are over-committed.
              </strong>{" "}
              Each one approved enrollments for steps its budget never funded. Its funded steps plus those approvals now
              add up to more than its limit. Most of that money is not spent yet, which is why "not yet spent" can still
              be large.
            </div>
          )}

          {/*
            Two charts, one question each. Obligations sit within about 1% of
            every limit, so a bar of obligations would only show department
            size. The useful view is how far over each one is, in rupees.
          */}
          <div className="row g-3">
            <div className="col-lg-6">
              <Card title="Over-committed by" subtitle="Obligations minus the limit, per department.">
                <BarList
                  items={rows.map((b) => ({
                    label: b.department_name,
                    value: Math.max(0, -b.unallocated_amount),
                    tone: "stop",
                    display: b.unallocated_amount < 0 ? money(-b.unallocated_amount) : "within limit",
                  }))}
                />
              </Card>
            </div>
            <div className="col-lg-6">
              <Card title="Spent so far" subtitle="Approved enrollments as a share of the limit.">
                <BarList
                  max={100}
                  items={rows.map((b) => ({
                    label: b.department_name,
                    value: b.utilization_pct,
                    display: `${b.utilization_pct.toFixed(1)}%`,
                  }))}
                />
              </Card>
            </div>
          </div>

          <Card title="By department" subtitle="Hover a status to read the reason." flush>
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Department</th>
                    <th className="text-end">Limit</th>
                    <th className="text-end">Funded steps</th>
                    <th className="text-end">Outside plan</th>
                    <th className="text-end">Obligations</th>
                    <th className="text-end">Unallocated</th>
                    <th className="text-end">Spent so far</th>
                    <th className="text-end">Not yet spent</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((b) => {
                    const over = b.budget_status === "EXCEEDED";
                    return (
                      <tr key={b.budget_id}>
                        <td>
                          <span className="cell-main">{b.department_name}</span>
                          <div className="mono">{b.budget_id}</div>
                        </td>
                        <td className="text-end">{money(b.limit_amount)}</td>
                        <td className="text-end">{money(b.funded_amount)}</td>
                        <td className="text-end">
                          {money(b.outside_plan_amount)}
                          <div className="muted small-text">{b.outside_plan_count} approvals</div>
                        </td>
                        <td className="text-end fw-semibold">{money(b.obligations_amount)}</td>
                        <td className="text-end" style={{ color: b.unallocated_amount < 0 ? "var(--stop)" : undefined }}>
                          {money(b.unallocated_amount)}
                        </td>
                        <td className="text-end">
                          {money(b.committed_amount)}
                          <div className="muted small-text">{b.utilization_pct.toFixed(1)}% of limit</div>
                        </td>
                        <td className="text-end">{money(b.remaining_amount)}</td>
                        <td title={b.status_reason}>
                          <StatusBadge status={b.budget_status} text={over ? "Over-committed" : "Within limit"} />
                          {over && (
                            <div className="small-text" style={{ color: "var(--stop)" }}>
                              by {money(-b.unallocated_amount)}
                            </div>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>

          <Card title="How to read these numbers">
            <div className="row g-3 small-text">
              <div className="col-md-6">
                <div className="fact-label">Obligations (decides the status)</div>
                <p className="mb-0">
                  Funded steps + approvals outside the plan. <strong>Unallocated</strong> = limit − obligations. Below
                  zero means the department has promised more than its limit: <strong>over-committed</strong>.
                </p>
              </div>
              <div className="col-md-6">
                <div className="fact-label">Spending (cash so far)</div>
                <p className="mb-0">
                  <strong>Spent so far</strong> = approved enrollments to date. <strong>Not yet spent</strong> = limit −
                  spent. Money promised to funded courses later in the year is not spent yet, so this stays large even
                  when the department is over-committed.
                </p>
              </div>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}

export default Budgets;
