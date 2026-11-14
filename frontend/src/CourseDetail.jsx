import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import api from "./api";
import BarList from "./BarList";
import Card from "./Card";
import getErrorMessage from "./errorMessage";
import money from "./money";
import PageHeader from "./PageHeader";
import StatCard from "./StatCard";
import StatusBadge from "./StatusBadge";

/*
  One course: what it teaches and up to which level, its prerequisite
  chain in both directions, and every run with its seats. The seat chart
  shows how full each run is from plans (booked in January) and from
  approvals (what actually happened).
*/
function CourseList({ title, subtitle, courses }) {
  return (
    <Card title={title} subtitle={subtitle}>
      {courses.length === 0 ? (
        <span className="muted">None.</span>
      ) : (
        <ul className="mb-0">
          {courses.map((c) => (
            <li key={c.course_id}>
              <Link to={`/courses/${c.course_id}`}>{c.course_title}</Link>{" "}
              <span className="muted small-text">({c.course_level.toLowerCase()})</span>{" "}
              {c.course_status === "RETIRED" && <StatusBadge status="RETIRED" />}
            </li>
          ))}
        </ul>
      )}
    </Card>
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
    return <p className="loading">Loading ...</p>;
  }

  const seatBars = course.offerings.map((o) => ({
    label: `${o.start_date}${o.in_period ? "" : " (2027)"}`,
    value: o.seats_approved,
    marker: o.seats_planned,
    display: `${o.seats_approved} / ${o.capacity}`,
  }));
  const capacity = Math.max(1, ...course.offerings.map((o) => o.capacity));

  return (
    <div>
      <PageHeader eyebrow="Learning" title={course.course_title} subtitle={`${course.course_id} · ${course.skill_category}`}>
        <Link className="btn-quiet" to="/courses">
          <i className="fa-solid fa-arrow-left me-2"></i>Catalog
        </Link>
      </PageHeader>

      <div className="row g-0 mb-4 kpi-strip">
        <div className="col-6 col-lg-3">
          <StatCard label="Level" value={course.course_level.toLowerCase()} note={course.delivery_mode.toLowerCase()} />
        </div>
        <div className="col-6 col-lg-3">
          <StatCard label="Length" value={`${course.duration_hours} h`} note="4 hours a week" />
        </div>
        <div className="col-6 col-lg-3">
          <StatCard label="Cost" value={money(course.cost_amount)} tone="primary" />
        </div>
        <div className="col-6 col-lg-3">
          <StatCard
            label="In the 2026 period"
            value={course.course_status === "RETIRED" ? "Retired" : course.available ? "Running" : "Not running"}
            tone={course.available ? "good" : "stop"}
          />
        </div>
      </div>

      <div className="row g-3">
        <div className="col-lg-6">
          <Card title="Skills taught" flush>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Skill</th>
                  <th>Role</th>
                  <th className="text-end">Up to level</th>
                </tr>
              </thead>
              <tbody>
                {course.skills.map((s) => (
                  <tr key={s.skill_id}>
                    <td>
                      <span className="cell-main">{s.skill_name}</span>
                      <div className="mono">{s.skill_id}</div>
                    </td>
                    <td>{s.skill_role.toLowerCase()}</td>
                    <td className="text-end">{s.target_level}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </div>
        <div className="col-lg-6">
          <CourseList title="Needs these first" subtitle="Prerequisites" courses={course.prerequisites} />
          <CourseList title="Unlocks" subtitle="Courses that list this one as a prerequisite" courses={course.required_by} />
        </div>
      </div>

      <Card title="Runs and seats" subtitle="Bar = seats approved. Black line = seats booked by January plans. Right = approved / capacity.">
        {course.offerings.length === 0 ? <span className="muted">This course has no runs.</span> : <BarList items={seatBars} max={capacity} />}
      </Card>
    </div>
  );
}

export default CourseDetail;
