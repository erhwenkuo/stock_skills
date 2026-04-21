"""Portfolio command: review -- Display trade performance review."""

import sys

from portfolio_commands import (
    HAS_PERFORMANCE_REVIEW,
    HAS_REVIEW_FORMATTER,
    format_performance_review,
    get_performance_review,
)


def cmd_review(
    year: int | None = None,
    symbol: str | None = None,
) -> None:
    """Display trade performance review (KIK-441)."""
    if not HAS_PERFORMANCE_REVIEW:
        print("Error: get_performance_review is not available.")
        sys.exit(1)

    data = get_performance_review(year=year, symbol=symbol)

    if HAS_REVIEW_FORMATTER:
        print(format_performance_review(data, year=year, symbol=symbol))
    else:
        # Fallback: print statistics only
        stats = data.get("stats", {})
        trades = data.get("trades", [])
        print(f"## Trade Performance Review")
        print(f"- Number of trades: {stats.get('total', 0)}")
        if stats.get("win_rate") is not None:
            print(f"- Win rate: {stats['win_rate'] * 100:.1f}%")
        if stats.get("total_pnl") is not None:
            print(f"- Total realized P&L: {stats['total_pnl']:+,.0f}")
