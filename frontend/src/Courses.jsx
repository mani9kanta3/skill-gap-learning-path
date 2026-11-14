import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import api from "./api";
import Card from "./Card";
import getErrorMessage from "./errorMessage";
import money from "./money";
import { COURSE_LEVELS } from "./options";
import PageHeader from "./PageHeader";
import StatusBadge from "./StatusBadge";
import useDebounce from "./useDebounce";

const PAGE = 50;

/*
  The course catalog, with the two facts a planner needs at a glance:
  is it running in the planning period, and does it need prerequisites.
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
    api
      .get("/skills/categories")
      .then((response) => setCategories(response.data))
      .catch(() => {});
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
      <PageHeader
        eyebrow="Learning"
        title="Course catalog"
        subtitle="Every course, the level it teaches to, its cost, and whether it runs in 2026."
      />

      <Card>
        <div className="toolbar">
          <div className="field" style={{ flexGrow: 2 }}>
            <label className="field-label">Search</label>
            <input className="form-control" placeholder="Title or CRS-000001" value={search} onChange={change(setSearch)} />
          </div>
          <div className="field">
            <label className="field-label">Category</label>
            <select className="form-select" value={category} onChange={change(setCategory)}>
              <option value="">All categories</option>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label className="field-label">Level</label>
            <select className="form-select" value={level} onChange={change(setLevel)}>
              <option value="">Any</option>
              {COURSE_LEVELS.map((l) => (
                <option key={l} value={l}>
                  {l.toLowerCase()}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label className="field-label">Runs in 2026</label>
            <select className="form-select" value={available} onChange={change(setAvailable)}>
              <option value="">Either</option>
              <option value="true">Yes</option>
              <option value="false">No</option>
            </select>
          </div>
        </div>
      </Card>

      {error && <div className="alert alert-danger">{error}</div>}

      <Card title={`${data.total.toLocaleString("en-IN")} courses`} flush>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Course</th>
                <th>Category</th>
                <th>Level</th>
                <th>Mode</th>
                <th className="text-end">Hours</th>
                <th className="text-end">Cost</th>
                <th className="text-end">Prerequisites</th>
                <th>2026</th>
              </tr>
            </thead>
            <tbody>
              {data.results.map((c) => (
                <tr key={c.course_id}>
                  <td>
                    <Link className="cell-main" to={`/courses/${c.course_id}`}>
                      {c.course_title}
                    </Link>
                    <div className="mono">{c.course_id}</div>
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
              {!load && data.results.length === 0 && (
                <tr>
                  <td colSpan="8" className="empty-row">
                    No course matches these filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="pager">
          <span>{load ? "Loading ..." : `Page ${page + 1} of ${pages}`}</span>
          <div className="d-flex gap-2">
            <button className="btn-quiet" disabled={page === 0 || load} onClick={() => setPage(page - 1)}>
              Previous
            </button>
            <button className="btn-quiet" disabled={page + 1 >= pages || load} onClick={() => setPage(page + 1)}>
              Next
            </button>
          </div>
        </div>
      </Card>
    </div>
  );
}

export default Courses;
