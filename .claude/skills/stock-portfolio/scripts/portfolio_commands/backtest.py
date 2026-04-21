"""Portfolio command: backtest -- Run backtest on accumulated screening history."""

import sys
from typing import Optional

from portfolio_commands import (
    HAS_BACKTEST,
    run_backtest,
    yahoo_client,
)


def cmd_backtest(
    preset: Optional[str] = None,
    region: Optional[str] = None,
    days: int = 90,
) -> None:
    """Run backtest on accumulated screening history."""
    if not HAS_BACKTEST:
        print("Error: backtest module not found.")
        sys.exit(1)

    print("Running backtest (accumulated data + current price fetch)...\n")

    result = run_backtest(
        yahoo_client_module=yahoo_client,
        category="screen",
        preset=preset,
        region=region,
        days_back=days,
    )

    stocks = result.get("stocks", [])
    period = result.get("period", {})

    if not stocks:
        print("No screening history found for the target period.")
        print(f"Period: {period.get('start', '?')} -> {period.get('end', '?')}")
        if preset:
            print(f"Preset: {preset}")
        if region:
            print(f"Region: {region}")
        return

    # Header
    print(f"## Backtest Results (past {days} days)")
    print(f"Period: {period.get('start', '?')} -> {period.get('end', '?')}")
    if preset:
        print(f"Preset: {preset}")
    if region:
        print(f"Region: {region}")
    print(f"Number of screenings: {result.get('total_screens', 0)}")
    print()

    # Stock table
    print("| Symbol | Name | Screen Date | Score at Screen | Price at Screen | Current Price | Return |")
    print("|:-----|:-----|:--------------|--------:|-------:|-------:|------:|")
    for s in stocks:
        ret_str = f"{s['return_pct'] * 100:+.2f}%"
        print(
            f"| {s['symbol']} | {s.get('name', '')} "
            f"| {s['screen_date']} | {s['score_at_screen']:.1f} "
            f"| {s['price_at_screen']:.2f} | {s['price_now']:.2f} | {ret_str} |"
        )
    print()

    # Summary
    print("### Summary")
    print(f"- Number of stocks: {result.get('total_stocks', 0)}")
    print(f"- Average return: {result.get('avg_return', 0) * 100:+.2f}%")
    print(f"- Median return: {result.get('median_return', 0) * 100:+.2f}%")
    print(f"- Win rate: {result.get('win_rate', 0) * 100:.1f}%")

    benchmark = result.get("benchmark", {})
    nikkei = benchmark.get("nikkei")
    sp500 = benchmark.get("sp500")
    if nikkei is not None:
        print(f"- Benchmark (Nikkei 225): {nikkei * 100:+.2f}%")
    else:
        print("- Benchmark (Nikkei 225): unavailable")
    if sp500 is not None:
        print(f"- Benchmark (S&P 500): {sp500 * 100:+.2f}%")
    else:
        print("- Benchmark (S&P 500): unavailable")

    alpha_n = result.get("alpha_nikkei")
    alpha_s = result.get("alpha_sp500")
    if alpha_n is not None:
        print(f"- Alpha (vs Nikkei 225): {alpha_n * 100:+.2f}%")
    if alpha_s is not None:
        print(f"- Alpha (vs S&P 500): {alpha_s * 100:+.2f}%")
    print()
