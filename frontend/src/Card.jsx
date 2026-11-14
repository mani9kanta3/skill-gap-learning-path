import React from "react";

/*
  A white box with an optional title row. Every section of every page is
  one of these, so spacing and borders are the same everywhere.

  flush removes the inner padding, for tables that should run edge to edge.
*/
function Card({ title, subtitle, actions, flush, children }) {
  return (
    <section className="card-box">
      {(title || actions) && (
        <div className="card-head">
          <div>
            {title && <h2 className="card-title">{title}</h2>}
            {subtitle && <p className="card-subtitle">{subtitle}</p>}
          </div>
          {actions}
        </div>
      )}
      <div className={`card-body ${flush ? "flush" : ""}`}>{children}</div>
    </section>
  );
}

export default Card;
