"""Freshness label and threshold logic for graph context (KIK-427/428).

Determines how stale cached context is, and what action the LLM should take
(skip re-fetch, diff-update, or full refresh).
"""

import os
from datetime import date, datetime


def _fresh_hours() -> int:
    """Return CONTEXT_FRESH_HOURS threshold (default 24)."""
    try:
        return int(os.environ.get("CONTEXT_FRESH_HOURS", "24"))
    except (ValueError, TypeError):
        return 24


def _recent_hours() -> int:
    """Return CONTEXT_RECENT_HOURS threshold (default 168 = 7 days)."""
    try:
        return int(os.environ.get("CONTEXT_RECENT_HOURS", "168"))
    except (ValueError, TypeError):
        return 168


def _days_since(date_str: str) -> int:
    """Return days between date_str and today. Returns 9999 on parse error."""
    try:
        d = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        return (date.today() - d).days
    except (ValueError, TypeError):
        return 9999


def _hours_since(date_str: str) -> float:
    """Return hours between date_str and now. Returns 999999 on parse error."""
    try:
        d = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return (datetime.now() - d).total_seconds() / 3600
    except (ValueError, TypeError):
        return 999999


def freshness_label(date_str: str) -> str:
    """Return freshness label for a date string.

    Returns one of: FRESH, RECENT, STALE, NONE.
    """
    if not date_str:
        return "NONE"
    h = _hours_since(date_str)
    if h <= _fresh_hours():
        return "FRESH"
    if h <= _recent_hours():
        return "RECENT"
    return "STALE"


def freshness_action(label: str) -> str:
    """Return recommended action for a freshness label."""
    return {
        "FRESH": "Use context",
        "RECENT": "Diff mode recommended",
        "STALE": "Full re-fetch recommended",
        "NONE": "New fetch",
    }.get(label, "New fetch")


def _action_directive(label: str) -> str:
    """Return action directive string for a freshness label.

    Placed at the top of context output so LLM immediately knows
    whether to run a skill or use existing context (KIK-428).
    """
    return {
        "FRESH": "⛔ FRESH — No skill execution needed. Answer using this context only.",
        "RECENT": "⚡ RECENT — Lightweight update in diff mode.",
        "STALE": "🔄 STALE — Full re-fetch. Run the skill.",
        "NONE": "🆕 NONE — No data. Run the skill.",
    }.get(label, "🆕 NONE — No data. Run the skill.")


def _best_freshness(labels: list[str]) -> str:
    """Return the freshest (best) label from a list."""
    priority = {"FRESH": 0, "RECENT": 1, "STALE": 2, "NONE": 3}
    if not labels:
        return "NONE"
    return min(labels, key=lambda l: priority.get(l, 3))
