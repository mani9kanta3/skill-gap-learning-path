import React, { useEffect, useState } from "react";

import api from "./api";
import getErrorMessage from "./errorMessage";
import { percent } from "./money";
import { ISSUE_TYPES } from "./options";
import PageHeader from "./PageHeader";
import StatusBadge from "./StatusBadge";

/*
  How well the data and the system hold up, straight from the last run.

  Three questions, in order:
  1. Is the data valid? Every check, with how many records failed it.
  2. Were the planted exceptions found, and nothing else? Precision and
     recall per type, matched record by record.
  3. Does the same seed give the same data? The reproducibility result.
  Below that: the outcome numbers, where attending, passing and actually
  closing a gap are kept apart.
*/
function metric(metrics, group, name, dimension = "ALL") {
  const found = metrics.find((m) => m.metric_group === group && m.metric_name === name && m.dimension === dimension);
  return found ? found.value : null;
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
    return <p className="info-text">Loading ...</p>;
  }

  const { checks, metrics, reproducibility } = data;
  const passed = checks.filter((c) => c.status === "PASS").length;
  const ruleChecks = checks.filter((c) => c.kind === "RULE");
  const shown = showAll ? checks : checks.filter((c) => c.kind === "RULE" || c.status === "FAIL");
  const funnel = ["recommended", "requested", "approved", "rejected", "started", "withdrawn", "completed", "passed", "reassessed"];

  return (
    <div>
      <PageHeader icon="fa-chart-simple" title="Evaluation" subtitle={`Results of the last generator run on the ${data.scale} dataset.`} />

      <div className="row g-3 mb-4">
        <div className="col-md-4">
          <div className="tile">
            <div className="tile-label">Validation checks</div>
            <div className="tile-value">
              {passed} / {checks.length}
            </div>
            <div className="tile-note">passed, {ruleChecks.length} of them matched to ground truth by ID</div>
          </div>
        </div>
        <div className="col-md-4">
          <div className="tile">
            <div className="tile-label">Detector</div>
            <div className="tile-value">
              {metric(metrics, "detection", "precision")?.toFixed(3)} / {metric(metrics, "detection", "recall")?.toFixed(3)}
            </div>
            <div className="tile-note">precision / recall over {Object.values(data.labelled).reduce((a, b) => a + b, 0)} labelled records</div>
          </div>
        </div>
        <div className="col-md-4">
          <div className="tile">
            <div className="tile-label">Reproducibility</div>
            {reproducibility ? (
              <>
                <div className="tile-value">
                  {reproducibility.matching} / {reproducibility.files}
                </div>
                <div className="tile-note">
                  files byte-identical across two runs with seed {reproducibility.seed}
                </div>
              </>
            ) : (
              <div className="tile-note">Run scripts/check_reproducibility.py to fill this in.</div>
            )}
          </div>
        </div>
      </div>

      <h2 className="section-title mb-2">Detection by type</h2>
      <div className="panel corners table-wrap mb-4">
        <table className="table data-table">
          <thead>
            <tr>
              <th>Exception</th>
              <th>Rule</th>
              <th className="text-end">Labelled</th>
              <th className="text-end">Found (TP)</th>
              <th className="text-end">False alarms</th>
              <th className="text-end">Missed</th>
              <th className="text-end">Precision</th>
              <th className="text-end">Recall</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(ISSUE_TYPES).map(([code, info]) => (
              <tr key={code}>
                <td>{info.label}</td>
                <td>{info.rule}</td>
                <td className="text-end">{data.labelled[code] || 0}</td>
                <td className="text-end">{metric(metrics, "detection", "tp", code)}</td>
                <td className="text-end">{metric(metrics, "detection", "fp", code)}</td>
                <td className="text-end">{metric(metrics, "detection", "fn", code)}</td>
                <td className="text-end">{metric(metrics, "detection", "precision", code)?.toFixed(3)}</td>
                <td className="text-end">{metric(metrics, "detection", "recall", code)?.toFixed(3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="row g-3 mb-4">
        <div className="col-md-6">
          <h2 className="section-title mb-2">Funnel</h2>
          <div className="panel corners table-wrap">
            <table className="table data-table">
              <tbody>
                {funnel.map((name) => (
                  <tr key={name}>
                    <td className="text-capitalize">{name}</td>
                    <td className="text-end">{Number(metric(metrics, "funnel", name)).toLocaleString("en-IN")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="col-md-6">
          <h2 className="section-title mb-2">Attending, passing and learning</h2>
          <div className="panel corners table-wrap">
            <table className="table data-table">
              <tbody>
                <tr>
                  <td>Completed, of started</td>
                  <td className="text-end">{percent(metric(metrics, "outcomes", "completion_rate_of_started"))}</td>
                </tr>
                <tr>
                  <td>Passed, of completed</td>
                  <td className="text-end">{percent(metric(metrics, "outcomes", "pass_rate_of_completed"))}</td>
                </tr>
                <tr>
                  <td>Gap actually closed, of reassessed</td>
                  <td className="text-end">{percent(metric(metrics, "outcomes", "gap_closed_rate_of_reassessed"))}</td>
                </tr>
                <tr>
                  <td>Level gained after passing</td>
                  <td className="text-end">{metric(metrics, "outcomes", "average_level_uplift", "PASSED")?.toFixed(2)}</td>
                </tr>
                <tr>
                  <td>Level gained after failing</td>
                  <td className="text-end">{metric(metrics, "outcomes", "average_level_uplift", "FAILED")?.toFixed(2)}</td>
                </tr>
                <tr>
                  <td>Due reassessments that happened</td>
                  <td className="text-end">{percent(metric(metrics, "outcomes", "reassessment_coverage_of_due"))}</td>
                </tr>
                <tr>
                  <td>Proposed steps passing every planning check</td>
                  <td className="text-end">{percent(metric(metrics, "feasibility", "share_feasible_all_checks"))}</td>
                </tr>
                <tr>
                  <td>Proposed steps funded by the budget</td>
                  <td className="text-end">{percent(metric(metrics, "funding", "share_funded"))}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="d-flex align-items-center justify-content-between mb-2">
        <h2 className="section-title mb-0">Validation checks</h2>
        <button type="button" className="btn btn-sm btn-outline-brand" onClick={() => setShowAll(!showAll)}>
          {showAll ? "Show rule checks only" : `Show all ${checks.length}`}
        </button>
      </div>
      <div className="panel corners table-wrap">
        <table className="table data-table">
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
                <td>{c.rule_code || ""}</td>
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
      <p className="info-text mt-2">
        Structural checks must fail on nothing. Rule checks must fail on exactly the labelled records of their type.
      </p>
    </div>
  );
}

export default Evaluation;
