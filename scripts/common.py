"""Common utilities for skill scripts -- graceful imports and context."""

import signal
from typing import Optional

_CONTEXT_TIMEOUT = 10  # seconds — max wait for context/suggestions


def try_import(module_path: str, *names: str):
    """Import names from a module with graceful degradation.

    Args:
        module_path: Dotted module path (e.g. "src.data.history")
        *names: Names to import from the module

    Returns:
        tuple: (success: bool, imports: dict)
               imports maps each name to the imported object or None.

    Example:
        ok, imports = try_import("src.data.history", "save_screening")
        save_screening = imports["save_screening"]
        if ok:
            save_screening(...)
    """
    result = {n: None for n in names}
    try:
        mod = __import__(module_path, fromlist=list(names))
        for name in names:
            result[name] = getattr(mod, name)
        return True, result
    except (ImportError, AttributeError):
        return False, result


# ---------------------------------------------------------------------------
# Module availability flags (KIK-448)
#
# Centralised checks for optional modules used by 2+ skill scripts.
# Each flag answers "can this module be imported?" — nothing more.
# Individual scripts still import the specific functions they need,
# guarded by these flags.
# ---------------------------------------------------------------------------

try:
    import src.data.history as _history_store_mod  # noqa: F401
    HAS_HISTORY_STORE = True
except ImportError:
    HAS_HISTORY_STORE = False

try:
    import src.data.graph_query as _graph_query_mod  # noqa: F401
    HAS_GRAPH_QUERY = True
except ImportError:
    HAS_GRAPH_QUERY = False

try:
    import src.data.graph_store as _graph_store_mod  # noqa: F401
    HAS_GRAPH_STORE = True
except ImportError:
    HAS_GRAPH_STORE = False


# ---------------------------------------------------------------------------
# Context retrieval & proactive suggestions (KIK-465)
#
# Embedded into each skill script's start/end for reliable execution.
# Graceful degradation: returns None / no output on any failure.
# ---------------------------------------------------------------------------

def _timeout_handler(signum, frame):
    raise TimeoutError("Context/suggestion timeout")


def print_context(user_input: str) -> Optional[str]:
    """Get and print graph context at script start.

    Returns the action label (FRESH/RECENT/STALE/NONE) or None on failure.
    Timeout: 10 seconds max. Graceful degradation on any error.
    """
    if not user_input:
        return None
    try:
        from src.data.context.auto_context import get_context

        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(_CONTEXT_TIMEOUT)
        try:
            result = get_context(user_input)
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

        if result and result.get("context_markdown"):
            print(result["context_markdown"])
            print()
            return result.get("action_label")
        return None
    except Exception:
        return None


def print_removal_contexts(symbols: list[str]) -> None:
    """Print graph context for removal candidate symbols (KIK-470).

    Called before what-if simulation to show screening history,
    investment notes, and research for stocks about to be sold.
    Timeout: 10 seconds total. Graceful degradation on any error.
    """
    if not symbols:
        return
    try:
        from src.data.context.auto_context import get_context

        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(_CONTEXT_TIMEOUT)
        try:
            contexts = []
            for sym in symbols:
                result = get_context(sym)
                if result and result.get("context_markdown"):
                    contexts.append(result["context_markdown"])
            if contexts:
                print("---")
                print("## Sell Candidate Context (KIK-470)\n")
                print("\n\n".join(contexts))
                print()
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    except Exception:
        pass  # graceful degradation


def print_suggestions(
    symbol: str = "",
    sector: str = "",
    context_summary: str = "",
    health_data: dict | None = None,
) -> None:
    """Print proactive suggestions at script end.

    Args:
        symbol: Current symbol in focus.
        sector: Current sector in focus.
        context_summary: Execution result summary for context-aware suggestions.
        health_data: Health check result dict (optional, for action item extraction).
    """
    suggestions: list[dict] = []
    try:
        from src.core.proactive_engine import format_suggestions, get_suggestions

        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(_CONTEXT_TIMEOUT)
        try:
            suggestions = get_suggestions(
                context=context_summary,
                symbol=symbol,
                sector=sector,
            )
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

        output = format_suggestions(suggestions)
        if output:
            print(output)
    except Exception:
        pass

    # Action item processing (KIK-472)
    _process_action_items(suggestions, health_data, context_summary)

    # Community incremental update (KIK-549)
    _maybe_refresh_communities()


def _process_action_items(
    suggestions: list[dict],
    health_data: dict | None = None,
    context_summary: str = "",
) -> None:
    """Process action items from suggestions and health data (KIK-472).

    Calls action_item_bridge.process_action_items() and displays results.
    Graceful degradation: no output on any failure.
    """
    try:
        from src.core.action_item_bridge import process_action_items

        results = process_action_items(
            suggestions=suggestions,
            health_data=health_data,
        )
        if not results:
            return

        lines = ["\n---", "📌 **Action Items** (auto-detected)\n"]
        for r in results:
            title = r.get("title", "")
            symbol = r.get("symbol", "")
            linear = r.get("linear_issue")
            neo4j = r.get("neo4j_saved", False)

            status_parts = []
            if neo4j:
                status_parts.append("Saved to Neo4j")
            if linear:
                ident = linear.get("identifier", "")
                url = linear.get("url", "")
                if ident and url:
                    status_parts.append(f"Linear: [{ident}]({url})")
                elif ident:
                    status_parts.append(f"Linear: {ident}")

            status = " / ".join(status_parts) if status_parts else "detected"
            lines.append(f"- {title} ({status})")

        print("\n".join(lines))
    except Exception:
        pass  # graceful degradation


def _maybe_refresh_communities() -> None:
    """Check for unclustered stocks and trigger incremental update (KIK-549).

    If new Stock nodes exist that are not in any Community, assign them
    to their best-matching community. If unclustered count exceeds threshold,
    trigger a full re-detection.
    Graceful degradation: no output on any failure.
    """
    try:
        if not HAS_GRAPH_QUERY:
            return
        from src.data.graph_query.community import (
            get_communities,
            update_stock_community,
        )
        from src.data.graph_query._common import _get_driver

        driver = _get_driver()
        if driver is None:
            return

        # Find stocks not in any community
        with driver.session() as session:
            result = session.run(
                "MATCH (s:Stock) "
                "WHERE NOT (s)-[:BELONGS_TO]->(:Community) "
                "RETURN s.symbol AS symbol LIMIT 20"
            )
            unclustered = [r["symbol"] for r in result]

        if not unclustered:
            return

        # If too many unclustered, trigger full re-detection
        if len(unclustered) >= 10:
            from src.data.graph_query.community import detect_communities
            detect_communities()
            return

        # Incremental: assign each to best community
        for sym in unclustered:
            update_stock_community(sym)
    except Exception:
        pass  # graceful degradation
