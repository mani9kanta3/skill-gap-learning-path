import React from "react";

/*
  A horizontal bar chart made of plain divs.

  The charts in this app are all "how big is each of these" questions
  (funnel steps, departments, issue types), and bars answer that best.
  Plain divs are enough for that, so there is no chart library to load
  or learn.

  items: [{ label, value, display, tone, marker }]
    value    the number that sets the bar length
    display  what to print on the right (defaults to value)
    tone     good / wait / stop / muted, only when the bar carries meaning
    marker   optional position (same units as value) for a thin line,
             used for "the limit" on budget bars
  max: the value of a full bar (defaults to the largest value or marker)
*/
function BarList({ items, max }) {
  const top = max || Math.max(1, ...items.map((item) => Math.max(item.value, item.marker || 0)));

  return (
    <div className="bar-list">
      {items.map((item) => (
        <div className="bar-row" key={item.label}>
          <div className="bar-label" title={item.label}>
            {item.label}
          </div>
          <div className="bar-track">
            <div
              className={`bar-fill ${item.tone ? `tone-${item.tone}` : ""}`}
              style={{ width: `${Math.min(100, (100 * item.value) / top)}%` }}
            ></div>
            {item.marker !== undefined && (
              <span className="bar-marker" style={{ left: `${Math.min(100, (100 * item.marker) / top)}%` }}></span>
            )}
          </div>
          <div className="bar-value">{item.display !== undefined ? item.display : item.value}</div>
        </div>
      ))}
    </div>
  );
}

export default BarList;
