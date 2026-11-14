import React, { useEffect, useState } from "react";

import api from "./api";
import BarList from "./BarList";
import Card from "./Card";
import getErrorMessage from "./errorMessage";
import { percent } from "./money";
import { ISSUE_TYPES } from "./options";
import PageHeader from "./PageHeader";
import StatCard from "./StatCard";
import StatusBadge from "./StatusBadge";

/*
  Can the data be trusted? Straight from the last generator run.

  Three questions, in order:
  1. Is the data valid? Every check, with how many records failed it.
  2. Were the planted exceptions found, and nothing else? Precision and
     recall per type, matched record by record.
  3. Does the same seed give the same data? The reproducibility result.
  Then the plan quality: how many proposed steps pass every planning
  check, and how many were funded.
*/
function metric(metrics, group, name, dimension = "ALL") {
  const found = metrics.find((m) => m.metric_group === group && m.metric_name === name && m.dimension === dimension);
  return found ? Number(found.value) : null;
}

function Evaluation() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    api
      .get("/evaluation")
      .then((response) => setData(response.data))
      .catch((err) => setError(getErrorMessage(err, "Could not load the evaluation.")));
  }, []);

  if (error) {
    return <div className="alert alert-danger">{error}</div>;
  }
  if (!data) {
    return <p className="loading">Loading ...</p>;
  }

  const { checks, metrics, reproducibility } = data;
  const passed = checks.filter((c) => c.status === "PASS").length;
  const ruleChecks = checks.filter((c) => c.kind === "RULE");
  const shown = showAll ? checks : checks.filter((c) => c.kind === "RULE" || c.status === "FAIL");
  const labelled = Object.values(data.labelled).reduce((a, b) => a + b, 0);

  const planBars = [
    { label: "Pass every planning check", value: 100 * metric(metrics, "feasibility", "share_feasible_all_checks") },
    { label: "Funded by the budget", value: 100 * metric(metrics, "funding", "share_funded") },
    { label: "Feasible and funded", value: 100 * metric(metrics, "funding", "share_feasible_and_funded") },
  ].map((item) => ({ ...item, display: `${item.value.toFixed(1)}%` }));

  return (
    <div>
      <PageHeader
        eyebrow="Data quality"
        title="Validation"
        subtitle={`Results of the last generator run on the ${data.scale} dataset.`}
      />

      <div className="row g-0 mb-4 kpi-strip">
        <div className="col-md-4">
          <StatCard
            label="Validation checks passed"
            value={`${passed} / ${checks.length}`}
            note={`${ruleChecks.length} of them matched to ground truth by record ID`}
            tone={passed === checks.length ? "good" : "stop"}
          />
        </div>
        <div className="col-md-4">
          <StatCard
            label="Detector precision / recall"
            value={`${metric(metrics, "detection", "precision")?.toFixed(3)} / ${metric(metrics, "detection", "recall")?.toFixed(3)}`}
            note={`over ${labelled} labelled records`}
            tone="primary"
          />
        </div>
        <div className="col-md-4">
          {reproducibility ? (
            <StatCard
              label="Reproducibility"
              value={`${reproducibility.matching} / ${reproducibility.files} files`}
              note={`byte-identical across two runs, seed ${reproducibility.seed}`}
              tone={reproducibility.identical ? "good" : "stop"}
            />
          ) : (
            <StatCard label="Reproducibility" value="not run" note="run scripts/check_reproducibility.py" />
          )}
        </div>
      </div>

      <div className="row g-3">
        <div className="col-lg-7">
          <Card title="Detection by exception type" subtitle="Matched by record ID, not by count." flush>
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Exception</th>
                    <th>Rule</th>
                    <th className="text-end">Labelled</th>
                    <th className="text-end">Found</th>
                    <th className="text-end">False alarms</th>
                    <th className="text-end">Missed</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(ISSUE_TYPES).map(([code, info]) => (
                    <tr key={code}>
                      <td>{info.label}</td>
                      <td className="mono">{info.rule}</td>
                      <td className="text-end">{data.labelled[code] || 0}</td>
                      <td className="text-end">{metric(metrics, "detection", "tp", code)}</td>
                      <td className="text-end">{metric(metrics, "detection", "fp", code)}</td>
                      <td className="text-end">{metric(metrics, "detection", "fn", code)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
        <div className="col-lg-5">
          <Card title="Plan quality" subtitle="Share of proposed course steps">
            <BarList items={planBars} max={100} />
            <hr />
            <div className="row g-3 small-text">
              <div className="col-6">
                <div className="fact-label">Due reassessments done</div>
                <div className="fact-value">{percent(metric(metrics, "outcomes", "reassessment_coverage_of_due"))}</div>
              </div>
              <div className="col-6">
                <div className="fact-label">Gap closed, of reassessed</div>
                <div className="fact-value">{percent(metric(metrics, "outcomes", "gap_closed_rate_of_reassessed"))}</div>
              </div>
            </div>
          </Card>
        </div>
      </div>

      <Card
        title="Validation checks"
        subtitle="Structural checks must fail on nothing. Rule checks must fail on exactly the labelled records of their type."
        actions={
          <button type="button" className="btn-quiet" onClick={() => setShowAll(!showAll)}>
            {showAll ? "Rule checks only" : `Show all ${checks.length}`}
          </button>
        }
        flush
      >
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Check</th>
                <th>Rule</th>
                <th>Table</th>
                <th>Kind</th>
                <th className="text-end">Failing</th>
                <th className="text-end">Expected</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((c) => (
                <tr key={c.check_id}>
                  <td className="mono">{c.check_id}</td>
                  <td className="mono">{c.rule_code || ""}</td>
                  <td>{c.table_name}</td>
                  <td>{c.kind.toLowerCase()}</td>
                  <td className="text-end">{c.failing_count}</td>
                  <td className="text-end">{c.expected_count}</td>
                  <td>
                    <StatusBadge status={c.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

export default Evaluation;
