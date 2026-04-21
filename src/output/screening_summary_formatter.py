"""Formatter for GraphRAG screening context output (KIK-452).

Converts the context dict from screening_context.get_screening_graph_context()
into a human-readable markdown string appended after screening tables.
"""


_NOTE_TYPE_LABELS = {
    "concern": "Concern",
    "thesis": "Thesis",
    "observation": "Observation",
    "lesson": "Lesson",
    "review": "Review",
}


def format_screening_summary(context: dict) -> str:
    """Format GraphRAG context as markdown for screening output (KIK-452, KIK-532).

    Outputs structured Neo4j data. Claude Code LLM interprets and synthesizes.

    Parameters
    ----------
    context : dict
        Output from get_screening_graph_context().

    Returns
    -------
    str
        Formatted markdown string. Empty string if nothing to show.
    """
    has_data = context.get("has_data", False)
    if not has_data:
        return ""

    lines = ["---", "### 📊 Graph Context (from Knowledge Graph)", ""]

    # --- Sector research ---
    for sector, data in context.get("sector_research", {}).items():
        lines.append(f"**{sector} Sector Trend**")
        cats_pos = data.get("catalysts_pos", [])
        cats_neg = data.get("catalysts_neg", [])
        if cats_pos:
            pos_str = ", ".join(cats_pos[:3])
            lines.append(f"- Positive: {pos_str}")
        if cats_neg:
            neg_str = ", ".join(cats_neg[:3])
            lines.append(f"- Negative: {neg_str}")
        lines.append("")

    # --- Symbol themes ---
    themes_map = context.get("symbol_themes", {})
    if themes_map:
        for symbol, themes in themes_map.items():
            if themes:
                themes_str = ", ".join(themes)
                lines.append(f"**Themes ({symbol})**: {themes_str}")
        lines.append("")

    # --- Symbol notes ---
    notes_map = context.get("symbol_notes", {})
    if notes_map:
        for symbol, notes in notes_map.items():
            for note in notes[:2]:
                note_type = _NOTE_TYPE_LABELS.get(
                    note.get("type", ""), note.get("type", "")
                )
                content = note.get("content", "")
                if len(content) > 80:
                    content = content[:77] + "..."
                date_str = note.get("date", "")
                date_part = f" ({date_str})" if date_str else ""
                lines.append(
                    f"**Investment Memo ({symbol})**: {note_type} — {content}{date_part}"
                )
        lines.append("")

    # --- Community grouping (KIK-549) ---
    communities_map = context.get("symbol_communities", {})
    if communities_map:
        # Group symbols by community name
        by_community: dict[str, list[str]] = {}
        for symbol, info in communities_map.items():
            cname = info.get("name", "?")
            by_community.setdefault(cname, []).append(symbol)

        lines.append("**Communities (similar stock clusters)**")
        for cname, members in sorted(by_community.items(), key=lambda x: -len(x[1])):
            members_str = ", ".join(members)
            lines.append(f"- {cname}: {members_str} ({len(members)} stocks)")
        lines.append("")

    return "\n".join(lines)
