import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import api from "./api";
import getErrorMessage from "./errorMessage";
import { DEPARTMENTS } from "./options";
import PageHeader from "./PageHeader";
import StatusBadge from "./StatusBadge";
import useDebounce from "./useDebounce";

const PAGE = 50;

/*
  The employee list, for managers and HR.

  A manager filters by their own ID to see their team. The filters live
  in the URL (?manager_id=EMP-000553), so a manager's team view is a link
  they can bookmark or send.
*/
function Employees() {
  const [params, setParams] = useSearchParams();
  const [search, setSearch] = useState(params.get("search") || "");
  const department = params.get("department") || "";
  const managerId = params.get("manager_id") || "";
  const status = params.get("status") || "";
  const page = Number(params.get("page") || 0);

  const settledSearch = useDebounce(search);
  const [data, setData] = useState({ total: 0, results: [] });
  const [load, setLoad] = useState(true);
  const [error, setError] = useState("");

  function update(key, value) {
    const next = new URLSearchParams(params);
    if (value) {
      next.set(key, value);
    } else {
      next.delete(key);
    }
    if (key !== "page") {
      next.delete("page");
    }
    setParams(next);
  }

  useEffect(() => {
    let current = true;
    setLoad(true);
    api
      .get("/employees", {
        params: {
          search: settledSearch,
          department: department || undefined,
          manager_id: managerId || undefined,
          status: status || undefined,
          limit: PAGE,
          offset: page * PAGE,
        },
      })
      .then((response) => {
        if (current) {
          setData(response.data);
          setError("");
        }
      })
      .catch((err) => current && setError(getErrorMessage(err, "Could not load employees.")))
      .finally(() => current && setLoad(false));
    // Ignore an answer that arrives after the filters have changed again.
    return () => {
      current = false;
    };
  }, [settledSearch, department, managerId, status, page]);

  const pages = Math.max(1, Math.ceil(data.total / PAGE));

  return (
    <div>
      <PageHeader
        icon="fa-users"
        title="Employees"
        subtitle={`${data.total.toLocaleString("en-IN")} employees match. Open one to see their gaps, path and results.`}
      />

      <div className="panel corners p-3 mb-3">
        <div className="row g-3">
          <div className="col-md-4">
            <label className="field-label form-label">Search</label>
            <input
              className="form-control"
              placeholder="Name or EMP-000001"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                update("search", e.target.value);
              }}
            />
          </div>
          <div className="col-md-3">
            <label className="field-label form-label">Department</label>
            <select className="form-select" value={department} onChange={(e) => update("department", e.target.value)}>
              <option value="">All departments</option>
              {DEPARTMENTS.map((d) => (
                <option key={d.code} value={d.code}>
                  {d.name}
                </option>
              ))}
            </select>
          </div>
          <div className="col-md-3">
            <label className="field-label form-label">Manager ID</label>
            <input
              className="form-control"
              placeholder="EMP-000553"
              value={managerId}
              onChange={(e) => update("manager_id", e.target.value.trim().toUpperCase())}
            />
          </div>
          <div className="col-md-2">
            <label className="field-label form-label">Status</label>
            <select className="form-select" value={status} onChange={(e) => update("status", e.target.value)}>
              <option value="">Any</option>
              <option value="ACTIVE">Active</option>
              <option value="ON_LEAVE">On leave</option>
            </select>
          </div>
        </div>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}

      <div className="panel corners table-wrap">
        <table className="table data-table">
          <thead>
            <tr>
              <th>Employee</th>
              <th>Department</th>
              <th>Role</th>
              <th>Working towards</th>
              <th className="text-end">Open gaps</th>
              <th className="text-end">Path courses</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {data.results.map((e) => (
              <tr key={e.employee_id}>
                <td>
                  <Link to={`/employees/${e.employee_id}`}>
                    {e.first_name} {e.last_name}
                  </Link>
                  <div className="mono text-muted">{e.employee_id}</div>
                </td>
                <td>{e.department_code}</td>
                <td>{e.role_title}</td>
                <td>
                  {e.target_role_title}
                  {e.on_career_path && <span className="chip ms-2">promotion</span>}
                </td>
                <td className="text-end">{e.open_gaps}</td>
                <td className="text-end">{e.path_courses}</td>
                <td>
                  <StatusBadge status={e.employment_status} />
                </td>
              </tr>
            ))}
            {!load && data.results.length === 0 && (
              <tr>
                <td colSpan="7" className="info-text text-center py-4">
                  No employee matches these filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="d-flex align-items-center justify-content-between mt-3">
        <span className="info-text">
          {load ? "Loading ..." : `Page ${page + 1} of ${pages}`}
        </span>
        <div className="d-flex gap-2">
          <button className="btn btn-light" disabled={page === 0 || load} onClick={() => update("page", String(page - 1))}>
            Previous
          </button>
          <button className="btn btn-light" disabled={page + 1 >= pages || load} onClick={() => update("page", String(page + 1))}>
            Next
          </button>
        </div>
      </div>
    </div>
  );
}

export default Employees;
