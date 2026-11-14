import React from "react";

/*
  One headline number. The coloured top edge carries meaning only when
  the number does (red for a problem, green for done); plain numbers get
  the accent colour or none.
*/
function StatCard({ label, value, note, tone = "" }) {
  return (
    <div className={`kpi ${tone ? `tone-${tone}` : ""}`}>
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
      {note && <div className="kpi-note">{note}</div>}
    </div>
  );
}

export default StatCard;
