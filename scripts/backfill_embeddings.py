#!/usr/bin/env python3
"""Backfill missing embeddings for Neo4j nodes (KIK-492).

Usage:
    python3 scripts/backfill_embeddings.py [--dry-run]

Finds nodes where embedding IS NULL, rebuilds semantic_summary if needed,
and generates embedding via TEI.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.graph_store import _get_driver, is_available
from src.data import embedding_client, summary_builder

# All node types that have vector indexes
NODE_TYPES = [
    "Screen", "Report", "Trade", "HealthCheck", "Research",
    "MarketContext", "Note", "Watchlist", "StressTest", "Forecast",
]


def _rebuild_summary(label: str, props: dict) -> str:
    """Rebuild semantic_summary from node properties."""
    try:
        if label == "Screen":
            return summary_builder.build_screen_summary(
                props.get("date", ""), props.get("preset", ""),
                props.get("region", ""), [],
            )
        elif label == "Report":
            return summary_builder.build_report_summary(
                props.get("symbol", ""), props.get("name", ""),
                props.get("score", 0), props.get("verdict", ""),
                props.get("sector", ""),
            )
        elif label == "Trade":
            return summary_builder.build_trade_summary(
                props.get("date", ""), props.get("type", ""),
                props.get("symbol", ""), props.get("shares", 0),
                props.get("memo", ""),
            )
        elif label == "HealthCheck":
            summary = {
                "total": props.get("total", 0),
                "healthy": props.get("healthy", 0),
                "exit": props.get("exit_count", 0),
            }
            return summary_builder.build_health_summary(
                props.get("date", ""), summary,
            )
        elif label == "Research":
            return summary_builder.build_research_summary(
                props.get("research_type", ""), props.get("target", ""),
                {"summary": props.get("summary", "")},
            )
        elif label == "MarketContext":
            return summary_builder.build_market_context_summary(
                props.get("date", ""), None, None,
            )
        elif label == "Note":
            return summary_builder.build_note_summary(
                props.get("symbol", ""), props.get("type", ""),
                props.get("content", ""),
            )
        elif label == "Watchlist":
            return summary_builder.build_watchlist_summary(
                props.get("name", ""), [],
            )
        elif label == "StressTest":
            return summary_builder.build_stress_test_summary(
                props.get("date", ""), props.get("scenario", ""),
                props.get("portfolio_impact", 0), props.get("symbol_count", 0),
            )
        elif label == "Forecast":
            return summary_builder.build_forecast_summary(
                props.get("date", ""),
                props.get("optimistic"), props.get("base"),
                props.get("pessimistic"), props.get("symbol_count", 0),
            )
    except Exception:
        pass
    return ""


def backfill(dry_run: bool = False) -> dict[str, int]:
    """Backfill missing embeddings.

    Returns dict of {label: count_updated}.
    """
    driver = _get_driver()
    if driver is None:
        print("ERROR: Neo4j driver not available.")
        return {}

    stats: dict[str, int] = {}

    for label in NODE_TYPES:
        # Find nodes missing embeddings
        id_field = "name" if label == "Watchlist" else "id"
        query = (
            f"MATCH (n:{label}) WHERE n.embedding IS NULL "
            f"RETURN n.{id_field} AS node_id, n AS props"
        )

        with driver.session() as session:
            result = session.run(query)
            nodes = [(r["node_id"], dict(r["props"])) for r in result]

        if not nodes:
            continue

        updated = 0
        for node_id, props in nodes:
            if node_id is None:
                continue

            # Use existing semantic_summary or rebuild
            summary = props.get("semantic_summary") or ""
            if not summary:
                summary = _rebuild_summary(label, props)

            if not summary:
                continue

            # Get embedding from TEI
            emb = embedding_client.get_embedding(summary)
            if emb is None:
                continue

            if dry_run:
                print(f"  [DRY-RUN] {label} {node_id}: would set embedding ({len(emb)}d)")
                updated += 1
                continue

            # Update node
            with driver.session() as session:
                set_clause = "n.embedding = $embedding"
                if not props.get("semantic_summary"):
                    set_clause += ", n.semantic_summary = $summary"
                session.run(
                    f"MATCH (n:{label} {{{id_field}: $node_id}}) SET {set_clause}",
                    node_id=node_id, embedding=emb, summary=summary,
                )
            updated += 1

        if updated > 0:
            stats[label] = updated
            action = "would update" if dry_run else "updated"
            print(f"  {label}: {action} {updated}/{len(nodes)} nodes")
        else:
            if nodes:
                print(f"  {label}: {len(nodes)} missing but could not generate embeddings")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Backfill missing embeddings (KIK-492)")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be updated without making changes",
    )
    args = parser.parse_args()

    print("Checking Neo4j connection...")
    if not is_available():
        print("ERROR: Neo4j is not reachable. Start with: docker compose up -d")
        sys.exit(1)

    print("Checking TEI availability...")
    if not embedding_client.is_available():
        print("ERROR: TEI is not reachable. Start TEI or set TEI_URL.")
        sys.exit(1)

    if args.dry_run:
        print("\n[DRY-RUN MODE] No changes will be made.\n")
    print("Scanning for nodes with missing embeddings...\n")

    stats = backfill(dry_run=args.dry_run)

    total = sum(stats.values())
    if total == 0:
        print("\nAll nodes already have embeddings. Nothing to do.")
    else:
        action = "Would update" if args.dry_run else "Updated"
        print(f"\n{action} {total} nodes across {len(stats)} types.")


if __name__ == "__main__":
    main()
