import React, { useEffect, useState } from "react";

import api from "./api";
import { DATASET } from "./options";

/*
  The bar across the top.

  It shows the two dates every number in the app depends on (when the
  plan was made, and the day the data is a snapshot of), so nobody reads
  a figure without knowing "as of when". On the right, a small dot says
  whether the API is reachable. If it is red, every page will fail, and
  this tells you why before the pages do.
*/
function Topbar({ onMenu }) {
  const [apiState, setApiState] = useState("checking");

  useEffect(() => {
    api
      .get("/health")
      .then(() => setApiState("ok"))
      .catch(() => setApiState("down"));
  }, []);

  const dot = { ok: "dot-good", down: "dot-stop", checking: "dot-wait" }[apiState];
  const text = { ok: "API connected", down: "API not reachable", checking: "Checking API ..." }[apiState];

  return (
    <header className="topbar">
      <button type="button" className="menu-button" aria-label="Open navigation" onClick={onMenu}>
        <i className="fa-solid fa-bars"></i>
      </button>

      <div className="topbar-context">
        <span className="context-item">
          Plan made <strong>{DATASET.planningDate}</strong>
        </span>
        <span className="context-item">
          Data as of <strong>{DATASET.asOfDate}</strong>
        </span>
        <span className="context-item">
          Budget year <strong>{DATASET.fiscalYear}</strong>
        </span>
      </div>

      <div className="api-status">
        <span className={`dot ${dot}`}></span>
        {text}
      </div>
    </header>
  );
}

export default Topbar;
