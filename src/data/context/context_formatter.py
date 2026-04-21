"""Markdown formatting for graph context output (KIK-411/427/428).

Converts raw graph history dicts into human-readable markdown with
freshness labels, community info, and action directives.
"""

from src.data.context.freshness import (
    _action_directive,
    _best_freshness,
    freshness_action,
    freshness_label,
)


def _format_context(symbol: str, history: dict, skill: str, reason: str,
                    relationship: str) -> str:
    """Format graph context as markdown with freshness labels (KIK-427/428)."""
    lines = [f"## History: {symbol} ({relationship})"]

    # Track freshness by data type for summary
    freshness_map: dict[str, str] = {}  # data_type -> label

    # Screens
    for s in history.get("screens", [])[:3]:
        d = s.get("date", "?")
        fl = freshness_label(d)
        lines.append(f"- [{fl}] {d} {s.get('preset', '')} "
                     f"Screening ({s.get('region', '')})")
        freshness_map.setdefault("Screening", fl)

    # Reports
    for r in history.get("reports", [])[:2]:
        d = r.get("date", "?")
        fl = freshness_label(d)
        verdict = r.get("verdict", "")
        score = r.get("score", "")
        lines.append(f"- [{fl}] {d} Report: Score {score}, {verdict}")
        freshness_map.setdefault("Report", fl)

    # Trades
    for t in history.get("trades", [])[:3]:
        d = t.get("date", "?")
        fl = freshness_label(d)
        action = "Buy" if t.get("type") == "buy" else "Sell"
        lines.append(f"- [{fl}] {d} {action}: "
                     f"{t.get('shares', '')} shares @ {t.get('price', '')}")
        freshness_map.setdefault("Trade", fl)

    # Health checks
    for h in history.get("health_checks", [])[:1]:
        d = h.get("date", "?")
        fl = freshness_label(d)
        lines.append(f"- [{fl}] {d} Health check performed")
        freshness_map.setdefault("Health Check", fl)

    # Notes
    for n in history.get("notes", [])[:3]:
        content = (n.get("content", "") or "")[:50]
        lines.append(f"- Note ({n.get('type', '')}): {content}")

    # Themes
    themes = history.get("themes", [])
    if themes:
        lines.append(f"- Themes: {', '.join(themes[:5])}")

    # Community (KIK-549)
    try:
        from src.data.graph_query.community import get_stock_community
        comm = get_stock_community(symbol)
        if comm:
            peers = comm.get("peers", [])[:5]
            lines.append(f"- Community: {comm['name']} ({comm['size']} stocks)")
            if peers:
                lines.append(f"  Same cluster: {', '.join(peers)}")
    except Exception:
        pass

    # Researches
    for r in history.get("researches", [])[:2]:
        d = r.get("date", "?")
        fl = freshness_label(d)
        summary = (r.get("summary", "") or "")[:50]
        lines.append(f"- [{fl}] {d} Research ({r.get('research_type', '')}): "
                     f"{summary}")
        freshness_map.setdefault("Research", fl)

    if len(lines) == 1:
        lines.append("- (no past data)")

    # Freshness summary (KIK-427)
    if freshness_map:
        lines.append("")
        lines.append("### Freshness Summary")
        for dtype, fl in freshness_map.items():
            lines.append(f"- {dtype}: [{fl}] → {freshness_action(fl)}")

    # KIK-428: Prepend action directive based on overall freshness
    overall = _best_freshness(list(freshness_map.values())) if freshness_map else "NONE"
    lines.insert(0, _action_directive(overall) + "\n")

    lines.append(f"\n**Recommended**: {skill} ({reason})")
    return "\n".join(lines)


def _format_market_context(mc: dict) -> str:
    """Format market context as markdown with freshness label (KIK-427/428)."""
    d = mc.get("date", "?")
    fl = freshness_label(d)
    lines = [_action_directive(fl) + "\n"]
    lines.append(f"## Recent Market Context [{fl}]")
    lines.append(f"- Fetched: {d} → {freshness_action(fl)}")
    for idx in mc.get("indices", [])[:5]:
        if isinstance(idx, dict):
            name = idx.get("name", idx.get("symbol", "?"))
            price = idx.get("price", idx.get("close", "?"))
            lines.append(f"- {name}: {price}")
    lines.append("\n**Recommended**: market-research (market check)")
    return "\n".join(lines)
