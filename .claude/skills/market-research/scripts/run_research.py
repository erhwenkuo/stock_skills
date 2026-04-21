#!/usr/bin/env python3
"""Entry point for the market-research skill."""

import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

from scripts.common import try_import, HAS_HISTORY_STORE, HAS_GRAPH_QUERY as _HAS_GQ, print_context, print_suggestions
from src.data import yahoo_client

HAS_RESEARCHER, _res = try_import(
    "src.core.research.researcher", "research_stock", "research_industry", "research_market")
if HAS_RESEARCHER:
    research_stock = _res["research_stock"]
    research_industry = _res["research_industry"]
    research_market = _res["research_market"]

HAS_BUSINESS, _biz = try_import("src.core.research.researcher", "research_business")
if HAS_BUSINESS: research_business = _biz["research_business"]

HAS_FORMATTER, _fmt = try_import(
    "src.output.research_formatter", "format_stock_research", "format_industry_research", "format_market_research")
if HAS_FORMATTER:
    format_stock_research = _fmt["format_stock_research"]
    format_industry_research = _fmt["format_industry_research"]
    format_market_research = _fmt["format_market_research"]

HAS_BUSINESS_FORMATTER, _bf = try_import("src.output.research_formatter", "format_business_research")
if HAS_BUSINESS_FORMATTER: format_business_research = _bf["format_business_research"]

# Module availability from common.py (KIK-448)
HAS_HISTORY = HAS_HISTORY_STORE
if HAS_HISTORY:
    from src.data.history import save_research, save_market_context

HAS_GRAPH_QUERY = _HAS_GQ
if HAS_GRAPH_QUERY:
    from src.data.graph_query import get_research_chain


def _print_research_history(research_type: str, target: str):
    """Print prior research history if graph data available (KIK-406)."""
    if not HAS_GRAPH_QUERY:
        return
    try:
        chain = get_research_chain(research_type, target, limit=3)
        if chain:
            print(f"\n### Research History ({len(chain)} entries)")
            for entry in chain:
                d = entry.get("date", "?")
                s = entry.get("summary", "")
                summary_short = s[:60] + "..." if len(s) > 60 else s
                print(f"  - {d}: {summary_short}")
            print()
    except Exception:
        pass


def cmd_stock(args):
    """Stock research"""
    if not HAS_RESEARCHER:
        print("Error: researcher module not found.")
        sys.exit(1)

    _print_research_history("stock", args.symbol)
    print(f"Researching: {args.symbol} ...")
    result = research_stock(args.symbol, yahoo_client)

    if HAS_FORMATTER:
        print(format_stock_research(result))
    else:
        import json
        print(json.dumps(result, ensure_ascii=False, indent=2))

    if HAS_HISTORY:
        try:
            save_research("stock", args.symbol, result)
        except Exception as e:
            print(f"Warning: Failed to save research history: {e}", file=sys.stderr)


def cmd_industry(args):
    """Industry research"""
    if not HAS_RESEARCHER:
        print("Error: researcher module not found.")
        sys.exit(1)

    _print_research_history("industry", args.theme)
    print(f"Industry research: {args.theme} ...")
    result = research_industry(args.theme)

    if HAS_FORMATTER:
        print(format_industry_research(result))
    else:
        import json
        print(json.dumps(result, ensure_ascii=False, indent=2))

    if HAS_HISTORY:
        try:
            save_research("industry", args.theme, result)
        except Exception as e:
            print(f"Warning: Failed to save research history: {e}", file=sys.stderr)


def cmd_market(args):
    """Market research"""
    if not HAS_RESEARCHER:
        print("Error: researcher module not found.")
        sys.exit(1)

    _print_research_history("market", args.market)
    print(f"Market research: {args.market} ...")
    result = research_market(args.market, yahoo_client)

    if HAS_FORMATTER:
        print(format_market_research(result))
    else:
        import json
        print(json.dumps(result, ensure_ascii=False, indent=2))

    if HAS_HISTORY:
        try:
            save_research("market", args.market, result)
            # Also save market context snapshot
            macro = result.get("macro_indicators")
            if macro:
                save_market_context({"indices": macro})
        except Exception as e:
            print(f"Warning: Failed to save research history: {e}", file=sys.stderr)


def cmd_business(args):
    """Business model analysis"""
    if not HAS_BUSINESS:
        print("Error: researcher module (research_business) not found.")
        sys.exit(1)

    _print_research_history("business", args.symbol)
    print(f"Business model analysis: {args.symbol} ...")
    result = research_business(args.symbol, yahoo_client)

    if HAS_BUSINESS_FORMATTER:
        print(format_business_research(result))
    else:
        import json
        print(json.dumps(result, ensure_ascii=False, indent=2))

    if HAS_HISTORY:
        try:
            save_research("business", args.symbol, result)
        except Exception as e:
            print(f"Warning: Failed to save research history: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Deep research tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # stock
    p_stock = subparsers.add_parser("stock", help="Stock research")
    p_stock.add_argument("symbol", help="Ticker symbol (e.g., 7203.T, AAPL)")
    p_stock.set_defaults(func=cmd_stock)

    # industry
    p_industry = subparsers.add_parser("industry", help="Industry/theme research")
    p_industry.add_argument("theme", help="Industry name or theme (e.g., semiconductors, AI)")
    p_industry.set_defaults(func=cmd_industry)

    # market
    p_market = subparsers.add_parser("market", help="Market overview research")
    p_market.add_argument("market", help="Market name or index (e.g., Nikkei, S&P500)")
    p_market.set_defaults(func=cmd_market)

    # business
    p_business = subparsers.add_parser("business", help="Business model analysis")
    p_business.add_argument("symbol", help="Ticker symbol (e.g., 7751.T, AAPL)")
    p_business.set_defaults(func=cmd_business)

    args = parser.parse_args()

    # Context retrieval (KIK-465)
    _target = getattr(args, "symbol", None) or getattr(args, "theme", None) or getattr(args, "market", None) or ""
    print_context(f"research {args.command} {_target}")

    args.func(args)

    # Proactive suggestions (KIK-465)
    _sym = getattr(args, "symbol", "") or ""
    print_suggestions(symbol=_sym, context_summary=f"Research complete: {args.command} {_target}")


if __name__ == "__main__":
    main()
