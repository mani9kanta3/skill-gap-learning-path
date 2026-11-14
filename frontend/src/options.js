/*
  Human labels for the codes the API sends back. The data keeps the
  codes (they are what the rules and the validator use); the pages show
  these words.
*/

export const DEPARTMENTS = [
  { code: "ENG", name: "Engineering" },
  { code: "DAT", name: "Data & Analytics" },
  { code: "ITS", name: "IT Services" },
  { code: "SAL", name: "Sales" },
  { code: "MKT", name: "Marketing" },
  { code: "FIN", name: "Finance" },
  { code: "HRM", name: "Human Resources" },
  { code: "OPS", name: "Operations" },
];

export const COURSE_LEVELS = ["FOUNDATION", "INTERMEDIATE", "ADVANCED"];

export const ISSUE_TYPES = {
  PREREQUISITE_VIOLATION: {
    label: "Recommendation skips a prerequisite",
    rule: "BR-05",
    help: "A course was recommended without its prerequisite being passed or planned earlier in the path.",
  },
  COURSE_UNAVAILABLE: {
    label: "Course not running in the planning period",
    rule: "BR-04",
    help: "A course was recommended that has no run starting in 2026.",
  },
  BUDGET_EXCEEDED: {
    label: "Approved over the department budget",
    rule: "BR-11",
    help: "An enrollment was approved when the department had less left than the course costs.",
  },
  DUPLICATE_COMPLETION: {
    label: "Completion counted twice",
    rule: "BR-13",
    help: "One enrollment has two completion records.",
  },
  GAP_NOT_REASSESSED: {
    label: "Gap left open with no reassessment",
    rule: "BR-17",
    help: "A gap-closing course was completed, but no post-course assessment followed.",
  },
};

export const REASONS = {
  CLOSES_GAP: "Closes the gap",
  PREREQUISITE_FOR: "Prerequisite",
  COURSE_UNAVAILABLE: "Not running in the period",
  PREREQUISITE_UNAVAILABLE: "A prerequisite is not available",
  PATH_LIMIT: "Path already has 4 courses",
  OVER_BUDGET: "Over the learning allowance",
  NO_SCHEDULE: "No run with a free seat fits the timeline",
};

export const PLAN_STATUS = {
  NO_GAP: "No gap",
  PLANNED: "Planned",
  NO_COURSE: "No course covers it",
  EMPLOYEE_ON_LEAVE: "On leave",
  COURSE_UNAVAILABLE: "Course not running",
  PREREQUISITE_UNAVAILABLE: "Prerequisite not available",
  PATH_LIMIT: "Path full",
  OVER_BUDGET: "Over allowance",
  NO_SCHEDULE: "No date or seat fits",
};

export function label(map, code) {
  return (map[code] && (map[code].label || map[code])) || code;
}
