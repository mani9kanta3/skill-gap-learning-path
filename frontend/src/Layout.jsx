import React, { useState } from "react";
import { Outlet } from "react-router-dom";

import Sidebar from "./Sidebar";
import Topbar from "./Topbar";

/*
  The shell every page sits inside.

  This is a tool people work in, not a site they visit once, so it uses
  the usual dashboard layout: navigation fixed down the left, a thin bar
  across the top with the dataset's dates, and the page in the rest of
  the space. On a phone the sidebar hides and slides in from the menu
  button, with a dark backdrop that closes it again.
*/
function Layout() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="shell">
      <Sidebar open={menuOpen} onNavigate={() => setMenuOpen(false)} />
      <div className={`backdrop ${menuOpen ? "open" : ""}`} onClick={() => setMenuOpen(false)}></div>

      <div className="main">
        <Topbar onMenu={() => setMenuOpen(!menuOpen)} />
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default Layout;
