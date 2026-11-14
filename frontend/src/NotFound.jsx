import React from "react";
import { Link } from "react-router-dom";

/*
  Anything that is not a real route lands here, inside the normal shell
  so the sidebar is still there to get back.
*/
function NotFound() {
  return (
    <div className="not-found">
      <div className="display-4 fw-bold mb-2">404</div>
      <h2 className="page-title mb-2">That page does not exist</h2>
      <p className="muted mb-4">The link may be old, or the address may have a typo in it.</p>
      <Link className="btn-primary-app" to="/">
        Back to the dashboard
      </Link>
    </div>
  );
}

export default NotFound;
