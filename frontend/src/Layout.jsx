import React from "react";
import { Outlet } from "react-router-dom";

import Navbar from "./Navbar";

/*
  The shell every page sits inside: the nav bar on top, the page below.
  Outlet is where React Router puts the page.
*/
function Layout() {
  return (
    <div className="app-shell">
      <Navbar />
      <div className="app-content">
        <Outlet />
      </div>
      <footer className="app-footer text-center">
        <p className="mb-0">
          Every employee, course and number here is synthetic, generated with a
          fixed seed. No real person or company data is used.
        </p>
      </footer>
    </div>
  );
}

export default Layout;
