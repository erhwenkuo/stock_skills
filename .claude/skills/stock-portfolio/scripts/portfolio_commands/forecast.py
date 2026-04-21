"""Portfolio command: forecast -- Generate 3-scenario return estimation."""

import sys

from portfolio_commands import (
    HAS_HISTORY,
    HAS_PORTFOLIO_FORMATTER,
    HAS_RETURN_ESTIMATE,
    estimate_portfolio_return,
    format_return_estimate,
    save_forecast,
    yahoo_client,
)


def cmd_forecast(csv_path: str) -> None:
    """Generate 3-scenario return estimation for portfolio."""
    if not HAS_RETURN_ESTIMATE:
        print("Error: return_estimate module not found.")
        sys.exit(1)

    print("Calculating estimated return (fetching analyst targets, news, and sentiment)...\n")

    result = estimate_portfolio_return(csv_path, yahoo_client)

    positions = result.get("positions", [])
    if not positions:
        print("No data available in portfolio.")
        return

    if HAS_PORTFOLIO_FORMATTER:
        print(format_return_estimate(result))
    else:
        # Fallback text output
        portfolio = result.get("portfolio", {})
        print("## Estimated Return (12 months)\n")
        for label, key in [("Optimistic", "optimistic"), ("Base", "base"), ("Pessimistic", "pessimistic")]:
            ret = portfolio.get(key)
            if ret is not None:
                print(f"- {label}: {ret * 100:+.2f}%")
            else:
                print(f"- {label}: -")
        print()
        for pos in positions:
            base_r = pos.get("base")
            base_str = f"{base_r * 100:+.2f}%" if base_r is not None else "-"
            print(f"  {pos.get('symbol', '-')}: {base_str} ({pos.get('method', '')})")
        print()

    # KIK-428: Auto-save forecast results
    if HAS_HISTORY:
        try:
            total_jpy = result.get("total_value_jpy", 0)
            save_forecast(positions=positions, total_value_jpy=total_jpy)
        except Exception as e:
            print(f"Warning: Failed to save forecast history: {e}", file=sys.stderr)
