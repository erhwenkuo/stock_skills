"""Portfolio command: health -- Run health check on portfolio holdings."""

import sys

from portfolio_commands import (
    HAS_GRAPH_QUERY,
    HAS_HEALTH_CHECK,
    HAS_HISTORY,
    HAS_PORTFOLIO_FORMATTER,
    format_health_check,
    get_recent_market_context,
    hc_run_health_check,
    save_health,
    yahoo_client,
)


def cmd_health(csv_path: str) -> dict | None:
    """Run health check on portfolio holdings.

    Returns the health_data dict (for action item processing in main).
    """
    if not HAS_HEALTH_CHECK:
        print("Error: health_check module not found.")
        sys.exit(1)

    print("Running health check (fetching price and financial data)...\n")

    health_data = hc_run_health_check(csv_path, yahoo_client)
    positions = health_data.get("positions", [])

    if not positions:
        print("No data available in portfolio.")
        return health_data

    if HAS_PORTFOLIO_FORMATTER:
        print(format_health_check(health_data))
    else:
        # Fallback text output
        print("## Portfolio Holdings Health Check\n")
        print("| Symbol | P&L | Trend | Change Quality | Alert |")
        print("|:-----|-----:|:-------|:--------|:------------|")
        for pos in positions:
            symbol = pos.get("symbol", "-")
            pnl_pct = pos.get("pnl_pct", 0)
            pnl_str = f"{pnl_pct * 100:+.1f}%" if pnl_pct else "-"
            trend = pos.get("trend_health", {}).get("trend", "Unknown")
            quality = pos.get("change_quality", {}).get("quality_label", "-")
            alert = pos.get("alert", {})
            alert_label = alert.get("label", "None")
            emoji = alert.get("emoji", "")
            alert_str = f"{emoji} {alert_label}".strip() if emoji else "None"
            print(f"| {symbol} | {pnl_str} | {trend} | {quality} | {alert_str} |")
        print()

    # KIK-406: Market context display
    if HAS_GRAPH_QUERY:
        try:
            ctx = get_recent_market_context()
            if ctx and ctx.get("indices"):
                print(f"\n### Market Context ({ctx['date']})")
                for idx in ctx["indices"]:
                    name = idx.get("name", "?")
                    price = idx.get("price")
                    change = idx.get("change_pct")
                    if price is not None:
                        change_str = f" ({change:+.2f}%)" if change is not None else ""
                        print(f"  - {name}: {price:,.2f}{change_str}")
                print()
        except Exception:
            pass

    if HAS_HISTORY:
        try:
            save_health(health_data)
        except Exception as e:
            print(f"Warning: Failed to save history: {e}", file=sys.stderr)

    return health_data
