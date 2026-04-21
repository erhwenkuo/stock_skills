"""Performance review formatter (KIK-441)."""

from typing import Optional

from src.output._format_helpers import fmt_currency_value as _fmt_currency_value


def format_performance_review(
    data: dict,
    year: Optional[int] = None,
    symbol: Optional[str] = None,
) -> str:
    """Format trade performance review as Markdown.

    Parameters
    ----------
    data : dict
        Output of ``get_performance_review()``.
        Expected keys: "trades" (list), "stats" (dict).
    year : int, optional
        Year used for filter (for display only).
    symbol : str, optional
        Symbol used for filter (for display only).

    Returns
    -------
    str
        Markdown-formatted performance review.
    """
    trades: list[dict] = data.get("trades", [])
    stats: dict = data.get("stats", {})

    # --- Header ---
    title_parts = ["Trade Performance Review"]
    if year:
        title_parts.append(f" ({year})")
    if symbol:
        title_parts.append(f" ({symbol})")
    title = "".join(title_parts)

    lines: list[str] = [f"## {title}", ""]

    if not trades:
        lines.append("No sell records with P&L found.")
        lines.append("")
        lines.append("Specify `--price` when selling to record realized P&L.")
        lines.append("")
        lines.append("Example: `sell --symbol NVDA --shares 5 --price 138`")
        return "\n".join(lines)

    # --- Trade history table ---
    lines.append("### Trade History")
    lines.append("")
    lines.append("| Symbol | Sell Date | Shares | Cost Price | Sell Price | Hold Days | Realized P&L | P&L% |")
    lines.append("|:-----|:------|-----:|-------:|-------:|-------:|-------:|------:|")

    for t in trades:
        sym = t.get("symbol", "-")
        date_str = t.get("date", "-")
        shares = t.get("shares", 0)
        cost_price = t.get("cost_price")
        sell_price = t.get("sell_price")
        hold_days = t.get("hold_days")
        realized_pnl = t.get("realized_pnl")
        pnl_rate = t.get("pnl_rate")
        currency = t.get("currency", "JPY")

        cost_str = _fmt_currency_value(cost_price, currency) if cost_price is not None else "-"
        sell_str = _fmt_currency_value(sell_price, currency) if sell_price is not None else "-"
        hold_str = f"{hold_days} days" if hold_days is not None else "-"
        pnl_str = _fmt_pnl(realized_pnl, currency) if realized_pnl is not None else "-"
        rate_str = _fmt_rate(pnl_rate) if pnl_rate is not None else "-"

        lines.append(
            f"| {sym} | {date_str} | {shares:,} | {cost_str} | {sell_str} "
            f"| {hold_str} | {pnl_str} | {rate_str} |"
        )

    lines.append("")

    # --- Statistics ---
    lines.append("### Statistics")
    lines.append("")
    total = stats.get("total", 0)
    wins = stats.get("wins", 0)
    win_rate = stats.get("win_rate")
    avg_return = stats.get("avg_return")
    avg_hold_days = stats.get("avg_hold_days")
    total_pnl = stats.get("total_pnl")

    # Infer currency from first trade
    currency = trades[0].get("currency", "JPY") if trades else "JPY"

    win_rate_str = f"{win_rate * 100:.1f}%" if win_rate is not None else "-"
    lines.append(f"- Trades: **{total}** / Win rate: **{win_rate_str}** ({wins}/{total})")

    avg_ret_str = _fmt_rate(avg_return) if avg_return is not None else "-"
    avg_hold_str = f"{avg_hold_days:.0f} days" if avg_hold_days is not None else "-"
    lines.append(f"- Avg return: **{avg_ret_str}** / Avg hold period: **{avg_hold_str}**")

    total_pnl_str = _fmt_pnl(total_pnl, currency) if total_pnl is not None else "-"
    lines.append(f"- Total realized P&L: **{total_pnl_str}**")

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _fmt_pnl(pnl: float, currency: str) -> str:
    sign = "+" if pnl >= 0 else ""
    if currency == "JPY":
        return f"{sign}\u00a5{pnl:,.0f}"
    return f"{sign}${pnl:,.2f}"


def _fmt_rate(rate: float) -> str:
    pct = rate * 100
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.2f}%"
