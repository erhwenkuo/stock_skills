#!/usr/bin/env python3
"""Clean up expired UpcomingEvent/SectorRotation nodes and orphan nodes (KIK-573).

Usage:
    python3 scripts/cleanup_expired_nodes.py [--dry-run] [--ttl-days 30]
"""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.graph_store import _get_driver, is_available


def cleanup_expired(ttl_days: int = 30, dry_run: bool = False) -> dict:
    """Delete expired UpcomingEvent and SectorRotation nodes."""
    driver = _get_driver()
    if driver is None:
        return {"upcoming_events": 0, "sector_rotations": 0}

    cutoff = (date.today() - timedelta(days=ttl_days)).isoformat()
    stats = {"upcoming_events": 0, "sector_rotations": 0}

    with driver.session() as session:
        for label, key in [("UpcomingEvent", "upcoming_events"),
                           ("SectorRotation", "sector_rotations")]:
            cnt = session.run(
                f"MATCH (n:{label}) WHERE n.date < $cutoff "
                "RETURN count(n) AS cnt",
                cutoff=cutoff,
            ).single()["cnt"]
            stats[key] = cnt
            if not dry_run and cnt > 0:
                session.run(
                    f"MATCH (n:{label}) WHERE n.date < $cutoff DETACH DELETE n",
                    cutoff=cutoff,
                )

    return stats


def cleanup_orphans(dry_run: bool = False) -> dict:
    """Delete orphan nodes (no relationships)."""
    driver = _get_driver()
    if driver is None:
        return {"orphan_notes": 0, "orphan_stocks": 0}

    stats = {"orphan_notes": 0, "orphan_stocks": 0}

    with driver.session() as session:
        # Orphan Notes
        cnt = session.run(
            "MATCH (n:Note) WHERE NOT (n)--() RETURN count(n) AS cnt",
        ).single()["cnt"]
        stats["orphan_notes"] = cnt
        if not dry_run and cnt > 0:
            session.run("MATCH (n:Note) WHERE NOT (n)--() DETACH DELETE n")

        # Orphan Stocks
        cnt = session.run(
            "MATCH (s:Stock) WHERE NOT (s)--() RETURN count(s) AS cnt",
        ).single()["cnt"]
        stats["orphan_stocks"] = cnt
        if not dry_run and cnt > 0:
            session.run("MATCH (s:Stock) WHERE NOT (s)--() DETACH DELETE s")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Clean up expired/orphan Neo4j nodes (KIK-573)"
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--ttl-days", type=int, default=30)
    args = parser.parse_args()

    if not is_available():
        print("ERROR: Neo4j not reachable.")
        sys.exit(1)

    prefix = "[DRY-RUN] " if args.dry_run else ""

    expired = cleanup_expired(ttl_days=args.ttl_days, dry_run=args.dry_run)
    print(f"{prefix}Expired UpcomingEvent: {expired['upcoming_events']}")
    print(f"{prefix}Expired SectorRotation: {expired['sector_rotations']}")

    orphans = cleanup_orphans(dry_run=args.dry_run)
    print(f"{prefix}Orphan Notes: {orphans['orphan_notes']}")
    print(f"{prefix}Orphan Stocks: {orphans['orphan_stocks']}")

    total = sum(expired.values()) + sum(orphans.values())
    action = "Would delete" if args.dry_run else "Deleted"
    print(f"\n{action} {total} nodes total.")


if __name__ == "__main__":
    main()
