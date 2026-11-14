import React from "react";

/*
  One small coloured badge for every status in the app. The colour
  carries meaning (good, waiting, stopped), so it is chosen here once
  instead of on every page.
*/
const TONE = {
  // enrollment
  REQUESTED: "wait",
  APPROVED: "info",
  IN_PROGRESS: "info",
  COMPLETED: "good",
  REJECTED: "stop",
  WITHDRAWN: "muted",
  // completion
  PASSED: "good",
  FAILED: "stop",
  // gaps
  NO_GAP: "muted",
  CLOSED: "good",
  OPEN: "wait",
  PLANNED: "good",
  // recommendation
  RECOMMENDED: "good",
  NOT_RECOMMENDED: "stop",
  // budget and checks
  WITHIN_LIMIT: "good",
  EXCEEDED: "stop",
  PASS: "good",
  FAIL: "stop",
  ACTIVE: "good",
  ON_LEAVE: "muted",
  RETIRED: "muted",
};

function StatusBadge({ status, text }) {
  if (!status) {
    return null;
  }
  const tone = TONE[status] || "wait";
  return <span className={`status-badge tone-${tone}`}>{text || status.replaceAll("_", " ")}</span>;
}

export default StatusBadge;
