import React, { useState } from "react";
import { NavLink, Link } from "react-router-dom";

/*
  The top bar.

  NavLink hands over an isActive flag, so the current page is highlighted
  without tracking the URL by hand. The collapse is a little state flag
  rather than Bootstrap's JavaScript, which this app does not load.
*/
const LINKS = [
  { to: "/employees", label: "Employees", icon: "fa-users" },
  { to: "/courses", label: "Courses", icon: "fa-book-open" },
  { to: "/budgets", label: "Budgets", icon: "fa-wallet" },
  { to: "/exceptions", label: "Exceptions", icon: "fa-triangle-exclamation" },
  { to: "/evaluation", label: "Evaluation", icon: "fa-chart-simple" },
];

function Navbar() {
  const [open, setOpen] = useState(false);

  return (
    <nav className="navbar navbar-expand-lg app-navbar">
      <div className="container">
        <Link className="navbar-brand d-flex align-items-center" to="/" onClick={() => setOpen(false)}>
          <span className="brand-mark me-2">
            <i className="fa-solid fa-route"></i>
          </span>
          <span className="brand-text">Skill Gap to Learning Path</span>
        </Link>

        <button
          className="navbar-toggler"
          type="button"
          aria-label="Toggle navigation"
          onClick={() => setOpen(!open)}
        >
          <span className="navbar-toggler-icon"></span>
        </button>

        <div className={`collapse navbar-collapse ${open ? "show" : ""}`}>
          <ul className="navbar-nav ms-auto">
            {LINKS.map((link) => (
              <li className="nav-item" key={link.to}>
                <NavLink
                  to={link.to}
                  onClick={() => setOpen(false)}
                  className={({ isActive }) =>
                    isActive ? "nav-link nav-link-active" : "nav-link"
                  }
                >
                  <i className={`fa-solid ${link.icon} me-2`}></i>
                  {link.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
