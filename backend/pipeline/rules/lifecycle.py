"""
BR-12: the enrollment lifecycle.

The status of an enrollment is never stored on its own. It is always the
to_status of its last event, so the history and the status cannot disagree.
"""

FIRST_STATUS = "REQUESTED"

ALLOWED = frozenset(
    {
        ("REQUESTED", "APPROVED"),
        ("REQUESTED", "REJECTED"),
        ("APPROVED", "IN_PROGRESS"),
        ("APPROVED", "WITHDRAWN"),
        ("IN_PROGRESS", "COMPLETED"),
        ("IN_PROGRESS", "WITHDRAWN"),
    }
)

TERMINAL = frozenset({"REJECTED", "COMPLETED", "WITHDRAWN"})

# Who makes each move (ARCHITECTURE.md 3.7). REJECTED depends on the reason.
ACTOR = {
    "REQUESTED": "EMPLOYEE",
    "APPROVED": "MANAGER",
    "IN_PROGRESS": "SYSTEM",
    "COMPLETED": "SYSTEM",
    "WITHDRAWN": "EMPLOYEE",
}
REJECTION_ACTOR = {"NO_SEATS": "SYSTEM", "BUDGET_EXHAUSTED": "HR_PARTNER"}


def is_allowed(from_status, to_status):
    return (from_status, to_status) in ALLOWED


def actor_for(to_status, reason_code=None):
    if to_status == "REJECTED":
        return REJECTION_ACTOR[reason_code]
    return ACTOR[to_status]


def current_status(events):
    """to_status of the event with the highest event_seq."""
    if not events:
        raise ValueError("An enrollment always has at least one event.")
    return max(events, key=lambda e: e["event_seq"])["to_status"]


def sequence_problems(events):
    """
    Everything wrong with one enrollment's history, as readable strings.
    An empty list means the history is valid.
    """
    problems = []
    ordered = sorted(events, key=lambda e: e["event_seq"])
    if not ordered:
        return ["no events"]

    seqs = [e["event_seq"] for e in ordered]
    if seqs != list(range(1, len(ordered) + 1)):
        problems.append(f"event_seq is {seqs}, expected 1..{len(ordered)}")

    first = ordered[0]
    if first["to_status"] != FIRST_STATUS or first["from_status"] is not None:
        problems.append("first event is not a REQUESTED with no from_status")

    for before, after in zip(ordered, ordered[1:]):
        if after["from_status"] != before["to_status"]:
            problems.append(
                f"event {after['event_seq']} starts from {after['from_status']} "
                f"but the previous event ended in {before['to_status']}"
            )
        if not is_allowed(after["from_status"], after["to_status"]):
            problems.append(f"{after['from_status']} -> {after['to_status']} is not allowed")
        if after["event_on"] < before["event_on"]:
            problems.append(f"event {after['event_seq']} is dated before the event before it")
        if before["to_status"] in TERMINAL:
            problems.append(f"an event follows the terminal status {before['to_status']}")

    return problems
