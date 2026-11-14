import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import api from "./api";
import getErrorMessage from "./errorMessage";
import { ISSUE_TYPES } from "./options";
import PageHeader from "./PageHeader";

/*
  Every exception the detector found, by type.

  The detector only reads the input tables. The "labelled" column comes
  from ground truth afterwards, so you can see each finding was expected
  (and the Evaluation page shows none were missed).
*/
function recordLink(row) {
  const id = row.record_id;
  if (id.startsWith("REC-") || id.startsWith("ENR-")) {
    const employee = id.slice(4, 14);
    return <Link to={`/employees/${employee}`}>{id}</Link>;
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

  return (
    <div>
      <PageHeader
        icon="fa-triangle-exclamation"
        title="Exceptions"
        subtitle="Records that break a business rule, found by re-checking every rule on the final data."
      />

      <div className="row g-3 mb-3">
        {Object.entries(ISSUE_TYPES).map(([code, info]) => (
          <div className="col-md" key={code}>
            <button
              type="button"
              className={`tile text-start w-100 ${issueType === code ? "border-2 border-success" : ""}`}
              onClick={() => setIssueType(issueType === code ? "" : code)}
            >
              <div className="tile-label">{info.rule}</div>
              <div className="tile-value">{data.by_type[code] || 0}</div>
              <div className="tile-note">{info.label}</div>
            </button>
          </div>
        ))}
      </div>

      {issueType && <div className="note mb-3">{ISSUE_TYPES[issueType].help}</div>}
      {error && <div className="alert alert-danger">{error}</div>}

      <div className="panel corners table-wrap">
        <table className="table data-table">
          <thead>
            <tr>
              <th>Type</th>
              <th>Record</th>
              <th>Evidence</th>
              <th>Expected decision</th>
              <th>Labelled</th>
            </tr>
          </thead>
          <tbody>
            {data.results.map((row) => (
              <tr key={`${row.issue_type}-${row.record_id}`}>
                <td className="text-nowrap">{ISSUE_TYPES[row.issue_type].label}</td>
                <td className="text-nowrap">{recordLink(row)}</td>
                <td className="info-text">{row.evidence}</td>
                <td className="mono">{row.expected_decision || "-"}</td>
                <td>{row.labelled ? <span className="status-badge tone-good">yes</span> : <span className="status-badge tone-stop">no</span>}</td>
              </tr>
            ))}
            {!load && data.results.length === 0 && (
              <tr>
                <td colSpan="5" className="info-text text-center py-4">
                  No exceptions found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <p className="info-text mt-2">{load ? "Loading ..." : `${data.total} shown.`}</p>
    </div>
  );
}

export default Exceptions;
