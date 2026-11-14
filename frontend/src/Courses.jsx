import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import api from "./api";
import getErrorMessage from "./errorMessage";
import money from "./money";
import { COURSE_LEVELS } from "./options";
import PageHeader from "./PageHeader";
import StatusBadge from "./StatusBadge";
import useDebounce from "./useDebounce";

const PAGE = 50;

/*
  The course catalog, with the two facts a planner needs at a glance:
  is it running in the planning period, and does it have prerequisites.
*/
function Courses() {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [level, setLevel] = useState("");
  const [available, setAvailable] = useState("");
  const [page, setPage] = useState(0);
  const [categories, setCategories] = useState([]);
  const [data, setData] = useState({ total: 0, results: [] });
  const [load, setLoad] = useState(true);
  const [error, setError] = useState("");
  const settledSearch = useDebounce(search);

  useEffect(() => {
    api.get("/skills/categories").then((response) => setCategories(response.data)).catch(() => {});
  }, []);

  useEffect(() => {
    let current = true;
    setLoad(true);
    api
      .get("/courses", {
        params: {
          search: settledSearch,
          category: category || undefined,
          level: level || undefined,
          available: available === "" ? undefined : available,
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
      .catch((err) => current && setError(getErrorMessage(err, "Could not load courses.")))
      .finally(() => current && setLoad(false));
    return () => {
      current = false;
    };
  }, [settledSearch, category, level, available, page]);

  const change = (setter) => (e) => {
    setter(e.target.value);
    setPage(0);
  };
  const pages = Math.max(1, Math.ceil(data.total / PAGE));

  return (
    <div>
      <PageHeader icon="fa-book-open" title="Courses" subtitle={`${data.total.toLocaleString("en-IN")} courses match.`} />

      <div className="panel corners p-3 mb-3">
        <div className="row g-3">
          <div className="col-md-4">
            <label className="field-label form-label">Search</label>
            <input className="form-control" placeholder="Title or CRS-000001" value={search} onChange={change(setSearch)} />
          </div>
          <div className="col-md-3">
            <label className="field-label form-label">Category</label>
            <select className="form-select" value={category} onChange={change(setCategory)}>
              <option value="">All categories</option>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
          <div className="col-md-2">
            <label className="field-label form-label">Level</label>
            <select className="form-select" value={level} onChange={change(setLevel)}>
              <option value="">Any</option>
              {COURSE_LEVELS.map((l) => (
                <option key={l} value={l}>
                  {l.toLowerCase()}
                </option>
              ))}
            </select>
          </div>
          <div className="col-md-3">
            <label className="field-label form-label">Running in 2026</label>
            <select className="form-select" value={available} onChange={change(setAvailable)}>
              <option value="">Either</option>
              <option value="true">Yes</option>
              <option value="false">No</option>
            </select>
          </div>
        </div>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}

      <div className="panel corners table-wrap">
        <table className="table data-table">
          <thead>
            <tr>
              <th>Course</th>
              <th>Category</th>
              <th>Level</th>
              <th>Mode</th>
              <th className="text-end">Hours</th>
              <th className="text-end">Cost</th>
              <th className="text-end">Prereqs</th>
              <th>2026</th>
            </tr>
          </thead>
          <tbody>
            {data.results.map((c) => (
              <tr key={c.course_id}>
                <td>
                  <Link to={`/courses/${c.course_id}`}>{c.course_title}</Link>
                  <div className="mono text-muted">{c.course_id}</div>
                </td>
                <td>{c.skill_category}</td>
                <td>{c.course_level.toLowerCase()}</td>
                <td>{c.delivery_mode.toLowerCase()}</td>
                <td className="text-end">{c.duration_hours}</td>
                <td className="text-end">{money(c.cost_amount)}</td>
                <td className="text-end">{c.prerequisites}</td>
                <td>
                  {c.course_status === "RETIRED" ? (
                    <StatusBadge status="RETIRED" />
                  ) : (
                    <StatusBadge status={c.available ? "PASS" : "FAIL"} text={c.available ? "running" : "not running"} />
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="d-flex align-items-center justify-content-between mt-3">
        <span className="info-text">{load ? "Loading ..." : `Page ${page + 1} of ${pages}`}</span>
        <div className="d-flex gap-2">
          <button className="btn btn-light" disabled={page === 0 || load} onClick={() => setPage(page - 1)}>
            Previous
          </button>
          <button className="btn btn-light" disabled={page + 1 >= pages || load} onClick={() => setPage(page + 1)}>
            Next
          </button>
        </div>
      </div>
    </div>
  );
}

export default Courses;
