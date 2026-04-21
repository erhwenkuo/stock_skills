"""TEI vector search and result merging for hybrid context retrieval (KIK-420).

Embeds user input via TEI, runs vector similarity search on Neo4j,
and merges results with symbol-based context.
"""

from typing import Optional

from src.data.context.freshness import (
    _action_directive,
    _best_freshness,
    freshness_label,
)


def _vector_search(user_input: str, _graph_query=None) -> list[dict]:
    """Embed user input via TEI and run vector similarity search on Neo4j.

    Returns list of {label, summary, score, date, id, symbol?}.
    Empty list when TEI or Neo4j unavailable (graceful degradation).

    Args:
        user_input: User query text.
        _graph_query: graph_query module (dependency injection for testability).
            When None, imports from src.data at call time.
    """
    try:
        from src.data.embedding_client import get_embedding, is_available
        if not is_available():
            return []
        emb = get_embedding(user_input)
        if emb is None:
            return []
        if _graph_query is None:
            from src.data import graph_query as _graph_query
        return _graph_query.vector_search(emb, top_k=5)
    except Exception:
        return []


def _format_vector_results(results: list[dict]) -> str:
    """Format vector search results as markdown with freshness labels (KIK-427)."""
    lines = ["## Related Past Records"]
    for r in results[:5]:
        score_pct = f"{r['score'] * 100:.0f}%"
        summary = r.get("summary") or "(no summary)"
        fl = freshness_label(r.get("date", ""))
        lines.append(f"- [{r['label']}][{fl}] {summary} (similarity {score_pct})")
    return "\n".join(lines)


def _infer_skill_from_vectors(results: list[dict]) -> str:
    """Infer a recommended skill from vector search result labels."""
    if not results:
        return "report"
    label_counts: dict[str, int] = {}
    for r in results[:5]:
        label = r.get("label", "")
        label_counts[label] = label_counts.get(label, 0) + 1
    if not label_counts:
        return "report"
    top_label = max(label_counts, key=label_counts.get)  # type: ignore[arg-type]
    mapping = {
        "Screen": "screen-stocks",
        "Report": "report",
        "Trade": "health",
        "Research": "market-research",
        "HealthCheck": "health",
        "MarketContext": "market-research",
        "Note": "report",
    }
    return mapping.get(top_label, "report")


def _merge_context(
    symbol_context: Optional[dict],
    vector_results: list[dict],
) -> Optional[dict]:
    """Merge symbol-based context with vector search results."""
    if not symbol_context and not vector_results:
        return None

    if symbol_context and not vector_results:
        return symbol_context

    if not symbol_context and vector_results:
        # KIK-428: Prepend action directive based on best freshness
        labels = [freshness_label(r.get("date", "")) for r in vector_results[:5]]
        overall = _best_freshness(labels) if labels else "NONE"
        return {
            "symbol": "",
            "context_markdown": (_action_directive(overall) + "\n\n"
                                 + _format_vector_results(vector_results)),
            "recommended_skill": _infer_skill_from_vectors(vector_results),
            "recommendation_reason": "Vector similarity search",
            "relationship": "Related",
        }

    # Both available: append vector results to symbol context
    merged = dict(symbol_context)  # type: ignore[arg-type]
    merged["context_markdown"] += "\n\n" + _format_vector_results(vector_results)
    return merged
