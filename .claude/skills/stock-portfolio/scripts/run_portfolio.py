#!/usr/bin/env python3
"""Entry point for the stock-portfolio skill.

Manages portfolio holdings stored in a CSV file.
Commands:
  snapshot  -- Generate a portfolio snapshot with current prices and P&L
  buy       -- Record a stock purchase
  sell      -- Record a stock sale (reduce shares)
  analyze   -- Structural analysis (sector/region/currency HHI)
  list      -- Display raw CSV contents
"""

import argparse
import os
import sys
from typing import Optional

# ---------------------------------------------------------------------------
# sys.path setup (same pattern as run_screen.py / run_stress_test.py)
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
sys.path.insert(0, PROJECT_ROOT)

# Add scripts directory so portfolio_commands package is importable
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from scripts.common import print_context, print_removal_contexts, print_suggestions

# ---------------------------------------------------------------------------
# Import subcommand functions from portfolio_commands
# ---------------------------------------------------------------------------
import portfolio_commands as _pc
from portfolio_commands import (
    _fallback_load_csv,
    _fallback_save_csv,
    _print_no_portfolio_message,
    _fmt_conf_price,
    _save_trade_market_context,
)
from portfolio_commands.snapshot import cmd_snapshot
from portfolio_commands.buy_sell import cmd_buy, cmd_sell
from portfolio_commands.list_cmd import cmd_list
from portfolio_commands.health import cmd_health as _cmd_health_inner
from portfolio_commands.analyze import cmd_analyze
from portfolio_commands.forecast import cmd_forecast
from portfolio_commands.rebalance import cmd_rebalance
from portfolio_commands.simulate import cmd_simulate as _cmd_simulate_inner
from portfolio_commands.what_if import cmd_what_if as _cmd_what_if_inner
from portfolio_commands.backtest import cmd_backtest
from portfolio_commands.review import cmd_review
from portfolio_commands.adjust import cmd_adjust

# ---------------------------------------------------------------------------
# Re-export HAS_* flags for backward compatibility (tests may override these)
# ---------------------------------------------------------------------------
HAS_PORTFOLIO_MANAGER = _pc.HAS_PORTFOLIO_MANAGER
HAS_PORTFOLIO_FORMATTER = _pc.HAS_PORTFOLIO_FORMATTER
HAS_RETURN_ESTIMATE = _pc.HAS_RETURN_ESTIMATE
HAS_HEALTH_CHECK = _pc.HAS_HEALTH_CHECK
HAS_CONCENTRATION = _pc.HAS_CONCENTRATION
HAS_REBALANCER = _pc.HAS_REBALANCER
HAS_REBALANCE_FORMATTER = _pc.HAS_REBALANCE_FORMATTER
HAS_SIMULATOR = _pc.HAS_SIMULATOR
HAS_SIMULATION_FORMATTER = _pc.HAS_SIMULATION_FORMATTER
HAS_HISTORY = _pc.HAS_HISTORY
HAS_BACKTEST = _pc.HAS_BACKTEST
HAS_CORRELATION = _pc.HAS_CORRELATION
HAS_SHAREHOLDER_RETURN = _pc.HAS_SHAREHOLDER_RETURN
HAS_WHAT_IF = _pc.HAS_WHAT_IF
HAS_WHAT_IF_FORMATTER = _pc.HAS_WHAT_IF_FORMATTER
HAS_SHAREHOLDER_ANALYSIS = _pc.HAS_SHAREHOLDER_ANALYSIS
HAS_SHAREHOLDER_ANALYSIS_FMT = _pc.HAS_SHAREHOLDER_ANALYSIS_FMT
HAS_GRAPH_QUERY = _pc.HAS_GRAPH_QUERY
HAS_GRAPH_STORE = _pc.HAS_GRAPH_STORE
HAS_PERFORMANCE_REVIEW = _pc.HAS_PERFORMANCE_REVIEW
HAS_REVIEW_FORMATTER = _pc.HAS_REVIEW_FORMATTER
HAS_MARKET_REGIME = _pc.HAS_MARKET_REGIME
HAS_ADJUSTMENT_ADVISOR = _pc.HAS_ADJUSTMENT_ADVISOR
HAS_ADJUST_FORMATTER = _pc.HAS_ADJUST_FORMATTER

# KIK-472: Module-level state to pass health_data to print_suggestions
_last_health_data: dict | None = None


def cmd_health(csv_path: str) -> None:
    """Run health check -- wrapper that stores health_data for action items."""
    global _last_health_data
    _last_health_data = _cmd_health_inner(csv_path)


def cmd_simulate(csv_path: str, years: int = 10, monthly_add: float = 0.0,
                 target=None, reinvest_dividends: bool = True) -> None:
    """Simulate wrapper -- checks module-level HAS_* flags for test overrides."""
    # Propagate any flag overrides to the portfolio_commands package,
    # but save/restore to avoid state pollution across test runs.
    orig_sim = _pc.HAS_SIMULATOR
    orig_re = _pc.HAS_RETURN_ESTIMATE
    try:
        _pc.HAS_SIMULATOR = HAS_SIMULATOR
        _pc.HAS_RETURN_ESTIMATE = HAS_RETURN_ESTIMATE
        _cmd_simulate_inner(csv_path, years=years, monthly_add=monthly_add,
                            target=target, reinvest_dividends=reinvest_dividends)
    finally:
        _pc.HAS_SIMULATOR = orig_sim
        _pc.HAS_RETURN_ESTIMATE = orig_re


def cmd_what_if(csv_path: str, add_str=None, remove_str=None) -> None:
    """What-If wrapper (KIK-470: print_removal_contexts integration)."""
    # KIK-470: removal_symbols context is handled inside _cmd_what_if_inner
    _cmd_what_if_inner(csv_path, add_str=add_str, remove_str=remove_str)


# ---------------------------------------------------------------------------
# Default CSV path
# ---------------------------------------------------------------------------
DEFAULT_CSV = os.path.join(
    os.path.dirname(__file__), "..", "data", "portfolio.csv"
)


# ---------------------------------------------------------------------------
# Main: argparse with subcommands
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Portfolio management -- list holdings, record trades, and analyze portfolio structure"
    )
    parser.add_argument(
        "--csv",
        default=DEFAULT_CSV,
        help=f"Path to the portfolio CSV file (default: {DEFAULT_CSV})",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # snapshot
    subparsers.add_parser("snapshot", help="Generate portfolio snapshot")

    # buy
    buy_parser = subparsers.add_parser("buy", help="Add a purchase record")
    buy_parser.add_argument("--symbol", required=True, help="Stock symbol (e.g. 7203.T)")
    buy_parser.add_argument("--shares", required=True, type=int, help="Number of shares")
    buy_parser.add_argument("--price", required=True, type=float, help="Purchase price per share")
    buy_parser.add_argument("--currency", default="JPY", help="Currency code (default: JPY)")
    buy_parser.add_argument("--date", default=None, help="Purchase date (YYYY-MM-DD)")
    buy_parser.add_argument("--memo", default="", help="Memo note")
    buy_parser.add_argument("-y", "--yes", action="store_true", default=False,
                            help="Skip confirmation and record directly (KIK-444)")

    # sell
    sell_parser = subparsers.add_parser("sell", help="Record a sale")
    sell_parser.add_argument("--symbol", required=True, help="Stock symbol (e.g. 7203.T)")
    sell_parser.add_argument("--shares", required=True, type=int, help="Number of shares to sell")
    sell_parser.add_argument("--price", type=float, default=None,
                             help="Sale price per share (KIK-441, e.g. 138.5)")
    sell_parser.add_argument("--date", default=None,
                             help="Sale date (KIK-441, YYYY-MM-DD, default: today)")
    sell_parser.add_argument("-y", "--yes", action="store_true", default=False,
                             help="Skip confirmation and record directly (KIK-444)")

    # review (KIK-441)
    review_parser = subparsers.add_parser("review", help="Trade performance review (KIK-441)")
    review_parser.add_argument("--year", type=int, default=None,
                               help="Year to aggregate (e.g. 2026, default: all periods)")
    review_parser.add_argument("--symbol", default=None,
                               help="Symbol filter (e.g. NVDA)")

    # analyze
    subparsers.add_parser("analyze", help="Structural analysis (sector/region/currency HHI)")

    # list
    subparsers.add_parser("list", help="Display holdings list")

    # health (KIK-356)
    subparsers.add_parser("health", help="Holdings health check")

    # forecast (KIK-359)
    subparsers.add_parser("forecast", help="Estimated return (3 scenarios)")

    # rebalance (KIK-363)
    rebalance_parser = subparsers.add_parser("rebalance", help="Rebalance proposal")
    rebalance_parser.add_argument(
        "--strategy",
        choices=["defensive", "balanced", "aggressive"],
        default="balanced",
        help="Investment strategy (default: balanced)",
    )
    rebalance_parser.add_argument(
        "--reduce-sector", default=None,
        help="Sector to reduce (e.g. Technology)",
    )
    rebalance_parser.add_argument(
        "--reduce-currency", default=None,
        help="Currency to reduce (e.g. USD)",
    )
    rebalance_parser.add_argument(
        "--max-single-ratio", type=float, default=None,
        help="Maximum single-stock ratio (e.g. 0.15)",
    )
    rebalance_parser.add_argument(
        "--max-sector-hhi", type=float, default=None,
        help="Maximum sector HHI (e.g. 0.25)",
    )
    rebalance_parser.add_argument(
        "--max-region-hhi", type=float, default=None,
        help="Maximum region HHI (e.g. 0.30)",
    )
    rebalance_parser.add_argument(
        "--additional-cash", type=float, default=0.0,
        help="Additional cash to invest (JPY, e.g. 1000000)",
    )
    rebalance_parser.add_argument(
        "--min-dividend-yield", type=float, default=None,
        help="Minimum dividend yield for increase candidates (e.g. 0.03)",
    )

    # simulate (KIK-366)
    simulate_parser = subparsers.add_parser("simulate", help="Compound interest simulation")
    simulate_parser.add_argument(
        "--years", type=int, default=10,
        help="Simulation period in years (default: 10)",
    )
    simulate_parser.add_argument(
        "--monthly-add", type=float, default=0.0,
        help="Monthly contribution amount (JPY, default: 0)",
    )
    simulate_parser.add_argument(
        "--target", type=float, default=None,
        help="Target amount (JPY, e.g. 15000000)",
    )
    simulate_parser.add_argument(
        "--reinvest-dividends", action="store_true", default=True,
        dest="reinvest_dividends",
        help="Reinvest dividends (default: ON)",
    )
    simulate_parser.add_argument(
        "--no-reinvest-dividends", action="store_false",
        dest="reinvest_dividends",
        help="Do not reinvest dividends",
    )

    # what-if (KIK-376 / KIK-451)
    whatif_parser = subparsers.add_parser("what-if", help="What-If simulation (add/swap)")
    whatif_parser.add_argument(
        "--add", required=False, default=None,
        help="Stocks to add (format: SYMBOL:SHARES:PRICE,... e.g. 7203.T:100:2850,AAPL:10:250)",
    )
    whatif_parser.add_argument(
        "--remove", required=False, default=None,
        help="Stocks to sell (format: SYMBOL:SHARES,... price not needed, calculated at market value e.g. 7203.T:100)",
    )

    # adjust (KIK-496)
    adjust_parser = subparsers.add_parser("adjust", help="Portfolio adjustment advisor")
    adjust_parser.add_argument(
        "--full", action="store_true", default=False,
        help="Full analysis (including concentration, correlation, VaR)",
    )

    # backtest (KIK-368)
    backtest_parser = subparsers.add_parser("backtest", help="Backtest of screening history")
    backtest_parser.add_argument(
        "--preset", default=None,
        help="Target preset (e.g. value, alpha)",
    )
    backtest_parser.add_argument(
        "--region", default=None,
        help="Target region (e.g. jp, us)",
    )
    backtest_parser.add_argument(
        "--days", type=int, default=90,
        help="Number of days of history to include (default: 90)",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # Context retrieval (KIK-465)
    print_context(f"portfolio {args.command}")

    csv_path = os.path.normpath(args.csv)

    if args.command == "snapshot":
        cmd_snapshot(csv_path)
    elif args.command == "buy":
        cmd_buy(
            csv_path=csv_path,
            symbol=args.symbol,
            shares=args.shares,
            price=args.price,
            currency=args.currency,
            purchase_date=args.date,
            memo=args.memo,
            yes=args.yes,
        )
    elif args.command == "sell":
        cmd_sell(
            csv_path=csv_path,
            symbol=args.symbol,
            shares=args.shares,
            sell_price=getattr(args, "price", None),
            sell_date=getattr(args, "date", None),
            yes=args.yes,
        )
    elif args.command == "analyze":
        cmd_analyze(csv_path)
    elif args.command == "list":
        cmd_list(csv_path)
    elif args.command == "health":
        cmd_health(csv_path)
    elif args.command == "forecast":
        cmd_forecast(csv_path)
    elif args.command == "rebalance":
        cmd_rebalance(
            csv_path=csv_path,
            strategy=args.strategy,
            reduce_sector=args.reduce_sector,
            reduce_currency=args.reduce_currency,
            max_single_ratio=args.max_single_ratio,
            max_sector_hhi=args.max_sector_hhi,
            max_region_hhi=args.max_region_hhi,
            additional_cash=args.additional_cash,
            min_dividend_yield=args.min_dividend_yield,
        )
    elif args.command == "simulate":
        cmd_simulate(
            csv_path=csv_path,
            years=args.years,
            monthly_add=args.monthly_add,
            target=args.target,
            reinvest_dividends=args.reinvest_dividends,
        )
    elif args.command == "what-if":
        cmd_what_if(
            csv_path=csv_path,
            add_str=getattr(args, "add", None),
            remove_str=getattr(args, "remove", None),
        )
    elif args.command == "backtest":
        cmd_backtest(
            preset=args.preset,
            region=args.region,
            days=args.days,
        )
    elif args.command == "review":
        cmd_review(
            year=getattr(args, "year", None),
            symbol=getattr(args, "symbol", None),
        )
    elif args.command == "adjust":
        cmd_adjust(
            csv_path=csv_path,
            full=getattr(args, "full", False),
        )
    else:
        parser.print_help()
        sys.exit(1)

    # Proactive suggestions (KIK-465) + action items (KIK-472)
    _sym = getattr(args, "symbol", "") or ""
    print_suggestions(
        symbol=_sym,
        context_summary=f"Portfolio: {args.command}",
        health_data=_last_health_data,
    )


if __name__ == "__main__":
    main()
