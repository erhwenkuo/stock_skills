"""Action item detector for proactive suggestions (KIK-472, KIK-489).

Converts proactive engine suggestions and health check data into structured
action items suitable for Linear issue creation and Neo4j storage.
"""

import re
from datetime import date

# Regex patterns for ticker symbol extraction (KIK-489)
# Note: \b doesn't work at JP character boundaries, so we use
# (?<![A-Za-z0-9]) and (?![A-Za-z0-9]) instead.
_B_L = r"(?<![A-Za-z0-9.])"  # left boundary
_B_R = r"(?![A-Za-z0-9.])"   # right boundary
# JP: 7203.T, 9856.T (4-5 digits + dot + 1-2 uppercase)
_RE_JP_SYMBOL = re.compile(_B_L + r"(\d{4,5}\.[A-Z]{1,2})" + _B_R)
# International dotted: BBL.BK, D05.SI, AUTO.JK (alphanumeric + dot + letters)
_RE_INTL_SYMBOL = re.compile(_B_L + r"([A-Z][A-Z0-9]*\.[A-Z]{1,3})" + _B_R)
# US: 2-5 uppercase letters (e.g. AAPL, NVDA)
_RE_US_SYMBOL = re.compile(_B_L + r"([A-Z]{2,5})" + _B_R)


# Keyword → trigger mapping
_TRIGGER_MAP: list[tuple[list[str], str, int, str]] = [
    # (keywords, trigger_type, linear_priority, title_format)
    (["撤退", "EXIT", "exit"], "exit", 2, "[Action] {symbol} Consider selling"),
    (["決算", "earnings", "Earnings"], "earnings", 2, "[Action] {symbol} Pre-earnings check"),
    (["テーゼ", "thesis", "投資テーゼ"], "thesis_review", 3, "[Action] {symbol} Thesis review"),
    (["懸念", "concern", "リスク確認"], "concern", 3, "[Action] {symbol} Confirm concern"),
]


def _match_trigger(text: str) -> tuple[str, int, str] | None:
    """Match text against trigger patterns.

    Returns (trigger_type, priority, title_format) or None.
    """
    for keywords, trigger_type, priority, title_fmt in _TRIGGER_MAP:
        for kw in keywords:
            if kw in text:
                return trigger_type, priority, title_fmt
    return None


def detect_action_items(
    suggestions: list[dict],
    health_data: dict | None = None,
    context: dict | None = None,
) -> list[dict]:
    """Convert proactive suggestions into structured action items.

    Args:
        suggestions: Output from proactive_engine.get_suggestions().
        health_data: Output from health_check.run_health_check() (optional).
        context: Graph context dict (optional, reserved for future use).

    Returns:
        List of action item dicts:
        [{trigger_type, title, description, symbol, priority, urgency, action_id}]
    """
    items: list[dict] = []
    today = date.today().isoformat()
    seen_keys: set[str] = set()

    # 1. Extract from suggestions
    for s in suggestions:
        title_text = s.get("title", "")
        reason = s.get("reason", "")
        urgency = s.get("urgency", "medium")
        combined = f"{title_text} {reason}"

        match = _match_trigger(combined)
        if not match:
            continue

        trigger_type, priority, title_fmt = match

        # Extract symbol from suggestion (heuristic: first word of title after emoji)
        symbol = _extract_symbol_from_suggestion(s)
        title = title_fmt.format(symbol=symbol or "stock")
        action_id = f"action_{today}_{trigger_type}_{symbol or 'unknown'}"

        if action_id in seen_keys:
            continue
        seen_keys.add(action_id)

        items.append({
            "trigger_type": trigger_type,
            "title": title,
            "description": reason,
            "symbol": symbol,
            "priority": priority,
            "urgency": urgency,
            "action_id": action_id,
        })

    # 2. Extract EXIT alerts directly from health_data (supplements suggestions)
    if health_data:
        for pos in health_data.get("positions", []):
            alert = pos.get("alert", {})
            if not isinstance(alert, dict):
                continue
            level = alert.get("level", "")
            if level != "exit":
                continue
            symbol = pos.get("symbol", "")
            if not symbol:
                continue
            action_id = f"action_{today}_exit_{symbol}"
            if action_id in seen_keys:
                continue
            seen_keys.add(action_id)
            items.append({
                "trigger_type": "exit",
                "title": f"[Action] {symbol} Consider selling",
                "description": alert.get("message", "EXIT judgment"),
                "symbol": symbol,
                "priority": 2,
                "urgency": "high",
                "action_id": action_id,
            })

    return items


def _extract_symbol_from_suggestion(suggestion: dict) -> str:
    """Try to extract a ticker symbol from a suggestion dict (KIK-489).

    Searches command_hint, title, and reason fields using regex patterns
    to handle Japanese text without spaces (e.g. "7203.Tの投資テーゼ").
    """
    # 1. Check command_hint for --symbol flag (e.g. "--symbol AAPL")
    hint = suggestion.get("command_hint", "")
    hint_parts = hint.split()
    for i, part in enumerate(hint_parts):
        if part == "--symbol" and i + 1 < len(hint_parts):
            return hint_parts[i + 1]

    # 2. Regex-based extraction across all text fields (KIK-489)
    # Priority: JP/dotted symbols > international > US uppercase
    _EXCLUDE = {"EXIT", "PER", "PBR", "ROE", "ETF", "IPO", "GDP", "BOJ", "FRB"}

    for field in ("command_hint", "title", "reason"):
        text = suggestion.get(field, "")
        if not text:
            continue
        # JP symbols first: 7203.T, 9856.T
        m = _RE_JP_SYMBOL.search(text)
        if m:
            return m.group(1)
        # International dotted: BBL.BK, D05.SI, AUTO.JK
        m = _RE_INTL_SYMBOL.search(text)
        if m:
            return m.group(1)

    # US symbols last (higher false-positive risk)
    for field in ("command_hint", "title", "reason"):
        text = suggestion.get(field, "")
        if not text:
            continue
        for m in _RE_US_SYMBOL.finditer(text):
            candidate = m.group(1)
            if candidate not in _EXCLUDE:
                return candidate

    return ""
