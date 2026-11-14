import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import api from "./api";
import Card from "./Card";
import getErrorMessage from "./errorMessage";
import { ISSUE_TYPES } from "./options";
import PageHeader from "./PageHeader";

/*
  Every record that breaks a business rule, found by re-checking every
  rule on the final data.

  The detector only reads the input tables. The "Labelled" column comes
  from ground truth afterwards, so you can see each finding was expected
  (the Validation page shows that none were missed).
*/
function recordLink(row) {
  const id = row.record_id;
  if (id.startsWith("REC-") || id.startsWith("ENR-")) {
    return <Link to={`/employees/${id.slice(4, 14)}`}>{id}</Link>;
  }
  if (row.employee_id) {
    return (
      <>
        <span className="mono">{id}</span> <Link to={`/employees/${row.employee_id}`}>({row.employee_id})</Link>
      </>
    );
  }
  return <span className="mono">{id}</span>;
}

function Exceptions() {
  const [issueType, setIssueType] = useState("");
  const [data, setData] = useState({ total: 0, by_type: {}, results: [] });
  const [load, setLoad] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoad(true);
    api
      .get("/exceptions", { params: { issue_type: issueType || undefined, limit: 500 } })
      .then((response) => {
        setData(response.data);
        setError("");
      })
      .catch((err) => setError(getErrorMessage(err, "Could not load exceptions.")))
      .finally(() => setLoad(false));
  }, [issueType]);

  const all = Object.values(data.by_type).reduce((a, b) => a + b, 0);

  return (
    <div>
      <PageHeader
        eyebrow="Data quality"
        title="Exceptions"
        subtitle="Records that break a business rule. Each one names the rule and the evidence."
      />

      <Card>
        <div className="segments">
          <button type="button" className={`segment ${issueType === "" ? "active" : ""}`} onClick={() => setIssueType("")}>
            All ({all})
          </button>
          {Object.entries(ISSUE_TYPES).map(([code, info]) => (
            <button
              key={code}
              type="button"
              className={`segment ${issueType === code ? "active" : ""}`}
              onClick={() => setIssueType(code)}
            >
              {info.rule} · {info.label} ({data.by_type[code] || 0})
            </button>
          ))}
        </div>
        {issueType && <div className="note mt-3">{ISSUE_TYPES[issueType].help}</div>}
      </Card>

      {error && <div className="alert alert-danger">{error}</div>}

      <Card title={load ? "Loading ..." : `${data.total} exceptions`} flush>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Rule</th>
                <th>Exception</th>
                <th>Record</th>
                <th>Evidence</th>
                <th>Should have been</th>
                <th>Labelled</th>
              </tr>
            </thead>
            <tbody>
              {data.results.map((row) => (
                <tr key={`${row.issue_type}-${row.record_id}`}>
                  <td className="mono">{row.rule_code}</td>
                  <td className="text-nowrap">{ISSUE_TYPES[row.issue_type].label}</td>
                  <td className="text-nowrap">{recordLink(row)}</td>
                  <td className="muted small-text">{row.evidence}</td>
                  <td className="mono">{row.expected_decision || "-"}</td>
                  <td>
                    {row.labelled ? (
                      <span className="badge-status tone-good">yes</span>
                    ) : (
                      <span className="badge-status tone-stop">no</span>
                    )}
                  </td>
                </tr>
              ))}
              {!load && data.results.length === 0 && (
                <tr>
                  <td colSpan="6" className="empty-row">
                    No exceptions found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

export default Exceptions;
