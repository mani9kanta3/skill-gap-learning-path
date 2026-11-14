import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import api from "./api";
import BarList from "./BarList";
import Card from "./Card";
import getErrorMessage from "./errorMessage";
import { inWords, percent } from "./money";
import { ISSUE_TYPES } from "./options";
import PageHeader from "./PageHeader";
import StatCard from "./StatCard";

/*
  The first screen: where the learning programme stands, in one look.

  Read top to bottom it follows the workflow of the brief:
  gaps found -> courses proposed and funded -> enrollments -> results,
  then money by department, then whether the data can be trusted.

  Three calls are made at once (summary, budgets, evaluation) because
  the page needs all three before it makes sense.
*/
const STEPS = [
  ["Measure the gap", "Target level for the role minus the assessed level, never below zero."],
  ["Propose a path", "Up to four courses, prerequisites first, in runs with a free seat, within the allowance."],
  ["Fund it", "Each department's budget is shared over the proposals, everyone's first course first."],
  ["Approve and run", "Only funded steps are approved. Every status change is kept as an event."],
  ["Reassess", "A post-course test decides whether the gap actually closed."],
];

function metric(metrics, group, name, dimension = "ALL") {
  const found = metrics.find((m) => m.metric_group === group && m.metric_name === name && m.dimension === dimension);
  return found ? Number(found.value) : 0;
}

function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const [summary, budgets, evaluation] = await Promise.all([
          api.get("/summary"),
          api.get("/budgets"),
          api.get("/evaluation"),
        ]);
        setData({ summary: summary.data, budgets: budgets.data, evaluation: evaluation.data });
      } catch (err) {
        setError(getErrorMessage(err, "Could not load the dashboard."));
      }
    }
    load();
  }, []);

  if (error) {
    return <div className="alert alert-danger">{error}</div>;
  }
  if (!data) {
    return <p className="loading">Loading the dashboard ...</p>;
  }

  const { summary, budgets, evaluation } = data;
  const metrics = evaluation.metrics;
  const n = (value) => Number(value).toLocaleString("en-IN");
  const checksPassed = evaluation.checks.filter((c) => c.status === "PASS").length;

  const funnel = [
    { label: "Proposed", value: summary.recommended },
    { label: "Funded", value: summary.funded_steps },
    { label: "Requested", value: metric(metrics, "funnel", "requested") },
    { label: "Approved", value: metric(metrics, "funnel", "approved") },
    { label: "Started", value: metric(metrics, "funnel", "started") },
    { label: "Completed", value: metric(metrics, "funnel", "completed") },
    { label: "Passed", value: metric(metrics, "funnel", "passed") },
    { label: "Reassessed", value: metric(metrics, "funnel", "reassessed"), tone: "muted" },
  ].map((item) => ({ ...item, display: n(item.value) }));

  const gapTotal = summary.closed_gaps + summary.open_gaps;
  const closedShare = gapTotal ? (100 * summary.closed_gaps) / gapTotal : 0;

  const budgetBars = budgets.map((b) => ({
    label: b.department_name,
    value: b.committed_amount,
    marker: b.limit_amount,
    display: `${b.utilization_pct.toFixed(0)}% of limit`,
  }));

  const exceptionBars = Object.entries(ISSUE_TYPES).map(([code, info]) => ({
    label: info.label,
    value: evaluation.labelled[code] || 0,
    tone: "stop",
  }));

  return (
    <div>
      <PageHeader
        eyebrow="Overview"
        title="Learning plan dashboard"
        subtitle="Skill gaps, the learning paths planned to close them, what was funded, and what actually happened in 2026."
      />

      <div className="row g-3 mb-4">
        <div className="col-6 col-xl-2">
          <StatCard label="Employees" value={n(summary.employees)} note={`${n(summary.active_employees)} active`} />
        </div>
        <div className="col-6 col-xl-2">
          <StatCard
            label="Skill gaps at planning"
            value={n(summary.planning_gaps)}
            note={`${percent(summary.planned_gaps / summary.planning_gaps, 0)} covered by a proposal`}
          />
        </div>
        <div className="col-6 col-xl-2">
          <StatCard
            label="Proposed course steps"
            value={n(summary.recommended)}
            note={`${percent(summary.funded_steps / summary.recommended, 0)} funded`}
            tone="primary"
          />
        </div>
        <div className="col-6 col-xl-2">
          <StatCard
            label="Enrollments"
            value={n(summary.enrollments)}
            note={`${n(summary.enrollments_by_status.REJECTED || 0)} rejected`}
          />
        </div>
        <div className="col-6 col-xl-2">
          <StatCard label="Gaps closed" value={n(summary.closed_gaps)} note="confirmed by a post-course test" tone="good" />
        </div>
        <div className="col-6 col-xl-2">
          <StatCard
            label="Exceptions found"
            value={n(summary.detected_issues)}
            note={`${checksPassed}/${evaluation.checks.length} checks pass`}
            tone="stop"
          />
        </div>
      </div>

      <div className="row g-3">
        <div className="col-lg-7">
          <Card title="Learning funnel" subtitle="From proposal to a confirmed result. Reassessed counts passed and failed gap-closing courses.">
            <BarList items={funnel} />
          </Card>
        </div>
        <div className="col-lg-5">
          <Card title="Skill gaps" subtitle={`${n(gapTotal)} gaps existed when the plan was made`}>
            <div className="stack" title={`${closedShare.toFixed(1)}% closed`}>
              <span style={{ width: `${closedShare}%`, background: "var(--good)" }}></span>
              <span style={{ width: `${100 - closedShare}%`, background: "var(--wait)" }}></span>
            </div>
            <div className="legend">
              <span>
                <i style={{ background: "var(--good)" }}></i>Closed {n(summary.closed_gaps)}
              </span>
              <span>
                <i style={{ background: "var(--wait)" }}></i>Still open {n(summary.open_gaps)}
              </span>
            </div>
            <hr />
            <div className="row g-3 small-text">
              <div className="col-6">
                <div className="fact-label">Completed, of started</div>
                <div className="fact-value">{percent(metric(metrics, "outcomes", "completion_rate_of_started"))}</div>
              </div>
              <div className="col-6">
                <div className="fact-label">Passed, of completed</div>
                <div className="fact-value">{percent(metric(metrics, "outcomes", "pass_rate_of_completed"))}</div>
              </div>
              <div className="col-6">
                <div className="fact-label">Gap closed, of reassessed</div>
                <div className="fact-value">{percent(metric(metrics, "outcomes", "gap_closed_rate_of_reassessed"))}</div>
              </div>
              <div className="col-6">
                <div className="fact-label">Level gained when passed</div>
                <div className="fact-value">+{metric(metrics, "outcomes", "average_level_uplift", "PASSED").toFixed(2)}</div>
              </div>
            </div>
            <p className="muted small-text mt-3 mb-0">
              Attending, passing and learning are three different numbers. Only the post-course test counts as learning.
            </p>
          </Card>
        </div>
      </div>

      <div className="row g-3">
        <div className="col-lg-7">
          <Card
            title="Budget use by department"
            subtitle="Bar = committed spend. Black line = the department's limit."
            actions={
              <Link className="btn-quiet" to="/budgets">
                Details
              </Link>
            }
          >
            <BarList items={budgetBars} />
            <p className="muted small-text mt-3 mb-0">
              Total committed {inWords(summary.budget_committed)} of {inWords(summary.budget_limit)}.
            </p>
          </Card>
        </div>
        <div className="col-lg-5">
          <Card
            title="Labelled exceptions"
            subtitle={`Detector precision ${metric(metrics, "detection", "precision").toFixed(3)}, recall ${metric(metrics, "detection", "recall").toFixed(3)}`}
            actions={
              <Link className="btn-quiet" to="/exceptions">
                Review
              </Link>
            }
          >
            <BarList items={exceptionBars} />
          </Card>
        </div>
      </div>

      <Card title="How the workflow runs">
        <div className="workflow">
          {STEPS.map(([title, text], index) => (
            <div className="workflow-step" key={title}>
              <div className="fw-bold mb-1">
                <span className="step-number">{index + 1}</span>
                {title}
              </div>
              <div className="muted small-text">{text}</div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

export default Dashboard;
