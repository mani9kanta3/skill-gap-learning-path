import React from "react";
import { Link, NavLink } from "react-router-dom";

/*
  The left navigation.

  Links are grouped by the question each group answers, which also lines
  up with who uses it: managers and employees live in People, HR partners
  in Learning and Budget, IT and operations in Data quality. NavLink tells
  us which page is open, so the current item is highlighted without
  tracking the URL by hand.
*/
const GROUPS = [
  {
    title: "Overview",
    links: [{ to: "/", label: "Dashboard", icon: "fa-gauge-high", end: true }],
  },
  {
    title: "People",
    links: [{ to: "/employees", label: "Employees", icon: "fa-users" }],
  },
  {
    title: "Learning",
    links: [{ to: "/courses", label: "Course catalog", icon: "fa-book-open" }],
  },
  {
    title: "Budget",
    links: [{ to: "/budgets", label: "Department budgets", icon: "fa-wallet" }],
  },
  {
    title: "Data quality",
    links: [
      { to: "/exceptions", label: "Exceptions", icon: "fa-triangle-exclamation" },
      { to: "/evaluation", label: "Validation", icon: "fa-clipboard-check" },
    ],
  },
];

function Sidebar({ open, onNavigate }) {
  return (
    <aside className={`sidebar ${open ? "open" : ""}`}>
      <Link className="sidebar-brand" to="/" onClick={onNavigate}>
        <span className="brand-mark">
          <i className="fa-solid fa-route"></i>
        </span>
        <span>
          Skill Gap
          <span className="brand-subtitle">to Learning Path</span>
        </span>
      </Link>

      <nav>
        {GROUPS.map((group) => (
          <div className="nav-group" key={group.title}>
            <div className="nav-group-title">{group.title}</div>
            {group.links.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.end}
                onClick={onNavigate}
                className={({ isActive }) => (isActive ? "nav-item active" : "nav-item")}
              >
                <i className={`fa-solid ${link.icon}`}></i>
                {link.label}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        Synthetic data, seed 20261022.
        <br />
        No real people or companies.
      </div>
    </aside>
  );
}

export default Sidebar;
