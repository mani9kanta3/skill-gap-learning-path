import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import api from "./api";
import getErrorMessage from "./errorMessage";
import money, { inWords } from "./money";

/*
  The landing page: what the system does in five steps, and the headline
  numbers from the loaded dataset. The steps mirror the brief's workflow,
  so a reviewer can find each one in the app.
*/
const STEPS = [
  {
    icon: "fa-bullseye",
    title: "Measure the gap",
    text: "Each role sets a target level per skill. The gap is target minus the employee's assessed level, never below zero.",
  },
  {
    icon: "fa-route",
    title: "Plan a feasible path",
    text: "Up to four courses, prerequisites first, in runs that have a free seat, inside the employee's learning allowance.",
  },
  {
    icon: "fa-clipboard-check",
    title: "Fund, then approve",
    text: "Each department's budget is shared out over the proposed steps, everyone's first course first. Only funded steps are approved; asking for an unfunded one is rejected, and the reason is recorded.",
  },
  {
    icon: "fa-graduation-cap",
    title: "Complete and reassess",
    text: "Finishing a course is not the same as learning. A post-course test decides whether the gap is actually closed.",
  },
  {
    icon: "fa-magnifying-glass-chart",
    title: "Check everything",
    text: "Every rule is re-checked on the final data, and labelled exceptions are matched record by record.",
  },
];

function Home() {
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/summary")
      .then((response) => setSummary(response.data))
      .catch((err) => setError(getErrorMessage(err, "Could not load the summary.")));
  }, []);

  const tiles = summary
    ? [
        { label: "Employees", value: summary.employees.toLocaleString("en-IN"), note: `${summary.active_employees.toLocaleString("en-IN")} active` },
        { label: "Skill gaps at planning", value: summary.planning_gaps.toLocaleString("en-IN"), note: `${summary.planned_gaps.toLocaleString("en-IN")} covered by a proposal` },
        { label: "Funded steps", value: summary.funded_steps.toLocaleString("en-IN"), note: `of ${summary.recommended.toLocaleString("en-IN")} proposed` },
        { label: "Gaps closed", value: summary.closed_gaps.toLocaleString("en-IN"), note: "confirmed by a post-course test" },
        { label: "Enrollments", value: summary.enrollments.toLocaleString("en-IN"), note: `${(summary.enrollments_by_status.COMPLETED || 0).toLocaleString("en-IN")} completed` },
        { label: "Budget committed", value: inWords(summary.budget_committed), note: `of ${money(summary.budget_limit)}` },
        { label: "Exceptions found", value: summary.detected_issues, note: "matched against ground truth" },
      ]
    : [];

  return (
    <div className="home">
      <section className="hero text-center">
        <h1 className="hero-title">From skill gap to a learning path that can actually happen</h1>
        <p className="hero-subtitle">
          Every recommendation here respects prerequisites, course dates, free
          seats and budgets, and every exception to those rules is shown, not
          hidden.
        </p>
        <div className="d-flex justify-content-center flex-wrap gap-2 mt-4">
          <Link className="btn btn-brand btn-lg" to="/employees">
            <i className="fa-solid fa-users me-2"></i>
            Find an employee
          </Link>
          <Link className="btn btn-outline-brand btn-lg" to="/evaluation">
            <i className="fa-solid fa-chart-simple me-2"></i>
            See the checks
          </Link>
        </div>
      </section>

      {error && <div className="alert alert-danger">{error}</div>}

      {summary && (
        <section className="row g-3 mt-1">
          {tiles.map((tile) => (
            <div className="col-6 col-md-3" key={tile.label}>
              <div className="tile">
                <div className="tile-label">{tile.label}</div>
                <div className="tile-value">{tile.value}</div>
                <div className="tile-note">{tile.note}</div>
              </div>
            </div>
          ))}
        </section>
      )}

      <section className="row g-3 mt-3">
        {STEPS.map((step, index) => (
          <div className="col-md-6 col-lg" key={step.title}>
            <div className="info-card corners h-100 p-3">
              <div className="d-flex align-items-center gap-2 mb-2">
                <span className="step-number">{index + 1}</span>
                <span className="info-icon">
                  <i className={`fa-solid ${step.icon}`}></i>
                </span>
              </div>
              <h5>{step.title}</h5>
              <p className="info-text mb-0">{step.text}</p>
            </div>
          </div>
        ))}
      </section>

      {summary && (
        <p className="info-text text-center mt-4 mb-0">
          Plan made on {summary.planning_date}. Data as of {summary.as_of_date}.
        </p>
      )}
    </div>
  );
}

export default Home;
