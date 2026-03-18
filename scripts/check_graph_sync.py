#!/usr/bin/env python3
"""Check and fix portfolio-to-Neo4j sync integrity (KIK-555).

Usage:
    python3 scripts/check_graph_sync.py          # Check only
    python3 scripts/check_graph_sync.py --fix    # Auto-fix missing data
"""

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.graph_store import _get_driver, is_available


_DEFAULT_CSV = ".claude/skills/stock-portfolio/data/portfolio.csv"


def _load_portfolio_symbols(csv_path: str) -> list[str]:
    """Load unique symbols from portfolio CSV."""
    p = Path(csv_path)
    if not p.exists():
        return []
    symbols = []
    with open(p, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sym = row.get("symbol", "").strip()
            if sym and not sym.endswith(".CASH"):
                symbols.append(sym)
    return list(dict.fromkeys(symbols))  # deduplicate preserving order


def check_sync(csv_path: str = _DEFAULT_CSV) -> list[dict]:
    """Check Neo4j sync status for all portfolio symbols.

    Returns list of {symbol, issues: [str]} for each symbol with issues.
    """
    driver = _get_driver()
    if driver is None:
        print("ERROR: Neo4j driver not available.")
        return []

    symbols = _load_portfolio_symbols(csv_path)
    if not symbols:
        print("No portfolio symbols found.")
        return []

    results = []
    with driver.session() as session:
        for sym in symbols:
            issues = []

            # 1. Stock node + metadata
            rec = session.run(
                "OPTIONAL MATCH (s:Stock {symbol: $sym}) "
                "RETURN s.name AS name, s.sector AS sector, s.country AS country",
                sym=sym,
            ).single()
            if rec is None or (not rec["name"] and not rec["sector"]):
                issues.append("Stock metadata empty")

            # 2. Trade node (BOUGHT)
            trade_cnt = session.run(
                "MATCH (t:Trade)-[:BOUGHT|SOLD]->(s:Stock {symbol: $sym}) "
                "RETURN count(t) AS cnt",
                sym=sym,
            ).single()["cnt"]
            if trade_cnt == 0:
                issues.append("No Trade nodes")

            # 3. HOLDS relationship
            holds = session.run(
                "MATCH (p:Portfolio)-[:HOLDS]->(s:Stock {symbol: $sym}) "
                "RETURN count(p) AS cnt",
                sym=sym,
            ).single()["cnt"]
            if holds == 0:
                issues.append("No HOLDS relationship")

            # 4. IN_SECTOR relationship
            if rec and rec["sector"]:
                in_sector = session.run(
                    "MATCH (s:Stock {symbol: $sym})-[:IN_SECTOR]->(:Sector) "
                    "RETURN count(*) AS cnt",
                    sym=sym,
                ).single()["cnt"]
                if in_sector == 0:
                    issues.append("No IN_SECTOR relationship")

            # 5. Trade embedding
            if trade_cnt > 0:
                emb_cnt = session.run(
                    "MATCH (t:Trade)-[:BOUGHT|SOLD]->(s:Stock {symbol: $sym}) "
                    "WHERE t.embedding IS NOT NULL "
                    "RETURN count(t) AS cnt",
                    sym=sym,
                ).single()["cnt"]
                if emb_cnt < trade_cnt:
                    issues.append(f"Trade embedding missing ({emb_cnt}/{trade_cnt})")

            # 6. Community
            comm = session.run(
                "MATCH (s:Stock {symbol: $sym})-[:BELONGS_TO]->(:Community) "
                "RETURN count(*) AS cnt",
                sym=sym,
            ).single()["cnt"]
            if comm == 0:
                issues.append("No Community assignment")

            if issues:
                results.append({"symbol": sym, "issues": issues})

    return results


def fix_sync(csv_path: str = _DEFAULT_CSV) -> dict:
    """Fix all sync issues by running sync_stock_full for each problem symbol.

    Returns {fixed: int, failed: int, details: [{symbol, result}]}
    """
    from src.data.graph_store.portfolio import sync_stock_full, sync_portfolio

    issues = check_sync(csv_path)
    if not issues:
        return {"fixed": 0, "failed": 0, "details": []}

    # Also re-sync portfolio HOLDS
    try:
        symbols_csv = _load_portfolio_symbols(csv_path)
        holdings = []
        p = Path(csv_path)
        if p.exists():
            with open(p, encoding="utf-8") as f:
                holdings = list(csv.DictReader(f))
        if holdings:
            sync_portfolio(holdings)
    except Exception as e:
        print(f"Warning: Portfolio HOLDS sync failed: {e}", file=sys.stderr)

    fixed = 0
    failed = 0
    details = []
    for item in issues:
        sym = item["symbol"]
        try:
            result = sync_stock_full(sym)
            details.append({"symbol": sym, "result": result})
            if result.get("stock") or result.get("trades", 0) > 0:
                fixed += 1
            else:
                failed += 1
        except Exception as e:
            details.append({"symbol": sym, "result": {"error": str(e)}})
            failed += 1

    return {"fixed": fixed, "failed": failed, "details": details}


def main():
    parser = argparse.ArgumentParser(
        description="Check portfolio-to-Neo4j sync integrity (KIK-555)"
    )
    parser.add_argument(
        "--fix", action="store_true",
        help="Auto-fix missing data using sync_stock_full()",
    )
    parser.add_argument(
        "--csv", default=_DEFAULT_CSV,
        help=f"Path to portfolio CSV (default: {_DEFAULT_CSV})",
    )
    args = parser.parse_args()

    print("Checking Neo4j connection...")
    if not is_available():
        print("ERROR: Neo4j is not reachable. Start with: docker compose up -d")
        sys.exit(1)

    print("Checking sync integrity...\n")
    issues = check_sync(args.csv)

    if not issues:
        print("All portfolio symbols are fully synced.")
        return

    print(f"Found {len(issues)} symbols with sync issues:\n")
    for item in issues:
        issue_str = ", ".join(item["issues"])
        print(f"  {item['symbol']}: {issue_str}")

    if not args.fix:
        print(f"\nRun with --fix to auto-repair these issues.")
        return

    print(f"\nFixing {len(issues)} symbols...")
    result = fix_sync(args.csv)
    print(f"\nFixed: {result['fixed']}, Failed: {result['failed']}")

    for d in result["details"]:
        sym = d["symbol"]
        r = d["result"]
        if "error" in r:
            print(f"  {sym}: ERROR - {r['error']}")
        else:
            parts = []
            if r.get("stock"):
                parts.append("Stock OK")
            if r.get("trades", 0) > 0:
                parts.append(f"Trades: {r['trades']}")
            if r.get("community"):
                parts.append("Community OK")
            print(f"  {sym}: {', '.join(parts) if parts else 'no changes'}")


if __name__ == "__main__":
    main()
