import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import api from "./api";
import getErrorMessage from "./errorMessage";
import money from "./money";
import PageHeader from "./PageHeader";
import StatusBadge from "./StatusBadge";

/*
  One course: what it teaches and up to which level, its prerequisite
  chain in both directions, and every run with planned and approved seats.
*/
function CourseList({ title, courses }) {
  return (
    <div className="panel corners p-3 h-100">
      <p className="field-label mb-2">{title}</p>
      {courses.length === 0 ? (
        <p className="info-text mb-0">None.</p>
      ) : (
        <ul className="mb-0">
          {courses.map((c) => (
            <li key={c.course_id}>
              <Link to={`/courses/${c.course_id}`}>{c.course_title}</Link>{" "}
              <span className="info-text">({c.course_level.toLowerCase()})</span>{" "}
              {c.course_status === "RETIRED" && <StatusBadge status="RETIRED" />}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function CourseDetail() {
  const { id } = useParams();
  const [course, setCourse] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setCourse(null);
    api
      .get(`/courses/${id}`)
      .then((response) => {
        setCourse(response.data);
        setError("");
      })
      .catch((err) => setError(getErrorMessage(err, "Could not load this course.")));
  }, [id]);

  if (error) {
    return <div className="alert alert-danger">{error}</div>;
  }
  if (!course) {
    return <p className="info-text">Loading ...</p>;
  }

  return (
    <div>
      <PageHeader
        icon="fa-book"
        title={course.course_title}
        subtitle={`${course.course_id} · ${course.skill_category} · ${course.course_level.toLowerCase()} · ${course.delivery_mode.toLowerCase()} · ${course.duration_hours} hours · ${money(course.cost_amount)}`}
      >
        {course.course_status === "RETIRED" ? (
          <StatusBadge status="RETIRED" />
        ) : (
          <StatusBadge status={course.available ? "PASS" : "FAIL"} text={course.available ? "running in 2026" : "not running in 2026"} />
        )}
      </PageHeader>

      <h2 className="section-title mb-2">Skills taught</h2>
      <div className="panel corners table-wrap mb-4">
        <table className="table data-table">
          <thead>
            <tr>
              <th>Skill</th>
              <th>Role</th>
              <th className="text-end">Brings a learner up to level</th>
            </tr>
          </thead>
          <tbody>
            {course.skills.map((s) => (
              <tr key={s.skill_id}>
                <td>
                  {s.skill_name} <span className="mono text-muted">{s.skill_id}</span>
                </td>
                <td>{s.skill_role.toLowerCase()}</td>
                <td className="text-end">{s.target_level}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="row g-3 mb-4">
        <div className="col-md-6">
          <CourseList title="Needs these first" courses={course.prerequisites} />
        </div>
        <div className="col-md-6">
          <CourseList title="Is a prerequisite for" courses={course.required_by} />
        </div>
      </div>

      <h2 className="section-title mb-2">Runs</h2>
      <div className="panel corners table-wrap">
        <table className="table data-table">
          <thead>
            <tr>
              <th>Run</th>
              <th>Dates</th>
              <th className="text-end">Capacity</th>
              <th className="text-end">Booked by plans</th>
              <th className="text-end">Approved</th>
              <th>Period</th>
            </tr>
          </thead>
          <tbody>
            {course.offerings.map((o) => (
              <tr key={o.offering_id}>
                <td className="mono">{o.offering_id}</td>
                <td className="text-nowrap">
                  {o.start_date} → {o.end_date}
                </td>
                <td className="text-end">{o.capacity}</td>
                <td className="text-end">{o.seats_planned}</td>
                <td className="text-end">{o.seats_approved}</td>
                <td>{o.in_period ? <span className="chip">2026</span> : <span className="chip">next year</span>}</td>
              </tr>
            ))}
            {course.offerings.length === 0 && (
              <tr>
                <td colSpan="6" className="info-text text-center py-3">
                  This course has no runs.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default CourseDetail;
