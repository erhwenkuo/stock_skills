"""Rebalance proposal output formatter (KIK-447, split from portfolio_formatter.py)."""

from src.core.ticker_utils import get_lot_size, round_to_lot_size
from src.output._format_helpers import fmt_pct_sign as _fmt_pct_sign
from src.output._format_helpers import fmt_float as _fmt_float


_ACTION_LABELS = {
    "sell": "Sell",
    "reduce": "Reduce",
    "increase": "Increase",
}

def _estimate_shares_annotation(
    symbol: str, value_jpy: float, current_price: float | None,
) -> str:
    """Generate a lot-size-aware share estimate annotation.

    Returns empty string for lot_size=1 stocks or when price is unavailable.
    """
    lot = get_lot_size(symbol)
    if lot <= 1 or not current_price or current_price <= 0:
        return ""
    estimated_shares = int(value_jpy / current_price)
    rounded = round_to_lot_size(estimated_shares, symbol)
    if rounded <= 0:
        rounded = lot
    return f"\u2248 {rounded} shares ({lot}-share lots)"


_ACTION_EMOJI = {
    "sell": "\U0001f534",      # red circle
    "reduce": "\U0001f7e1",    # yellow circle
    "increase": "\U0001f7e2",  # green circle
}


def format_rebalance_report(proposal: dict) -> str:
    """Format a rebalance proposal as markdown.

    Parameters
    ----------
    proposal : dict
        Output of rebalancer.generate_rebalance_proposal().

    Returns
    -------
    str
        Markdown-formatted report.
    """
    lines: list[str] = []

    strategy = proposal.get("strategy", "balanced")
    strategy_label = {
        "defensive": "Defensive",
        "balanced": "Balanced",
        "aggressive": "Aggressive",
    }.get(strategy, strategy)
    lines.append(f"## Rebalance Proposal ({strategy_label})")
    lines.append("")

    # --- Before / After ---
    before = proposal.get("before", {})
    after = proposal.get("after", {})

    lines.append("### Current \u2192 Proposed")
    lines.append("")
    lines.append("| Metric | Current | Proposed |")
    lines.append("|:-----|-----:|------:|")
    lines.append(
        f"| Base Expected Return | {_fmt_pct_sign(before.get('base_return'))} "
        f"| {_fmt_pct_sign(after.get('base_return'))} |"
    )
    lines.append(
        f"| Sector HHI | {_fmt_float(before.get('sector_hhi'), 4)} "
        f"| {_fmt_float(after.get('sector_hhi'), 4)} |"
    )
    lines.append(
        f"| Region HHI | {_fmt_float(before.get('region_hhi'), 4)} "
        f"| {_fmt_float(after.get('region_hhi'), 4)} |"
    )
    lines.append("")

    # --- Cash summary ---
    freed = proposal.get("freed_cash_jpy", 0)
    additional = proposal.get("additional_cash_jpy", 0)
    if freed > 0 or additional > 0:
        lines.append("### Funds")
        lines.append("")
        if freed > 0:
            lines.append(f"- **Funds freed by selling/reducing:** \u00a5{freed:,.0f}")
        if additional > 0:
            lines.append(f"- **Additional capital:** \u00a5{additional:,.0f}")
        lines.append(f"- **Total available funds:** \u00a5{freed + additional:,.0f}")
        lines.append("")

    # --- Actions ---
    actions = proposal.get("actions", [])
    if not actions:
        lines.append("### Actions")
        lines.append("")
        lines.append("Current portfolio is within constraints. No rebalancing needed.")
        lines.append("")
        return "\n".join(lines)

    lines.append("### Actions")
    lines.append("")

    for i, action in enumerate(actions, 1):
        act_type = action.get("action", "")
        emoji = _ACTION_EMOJI.get(act_type, "")
        label = _ACTION_LABELS.get(act_type, act_type)
        symbol = action.get("symbol", "")
        name = action.get("name", "")
        name_str = f" {name}" if name else ""
        reason = action.get("reason", "")

        if act_type == "sell":
            value = action.get("value_jpy", 0)
            lines.append(
                f"{i}. {emoji} **{label}**: {symbol}{name_str} all shares"
                f" \u2192 {reason}"
            )
            if value > 0:
                lines.append(f"   Freed funds: \u00a5{value:,.0f}")
        elif act_type == "reduce":
            ratio = action.get("ratio", 0)
            value = action.get("value_jpy", 0)
            lines.append(
                f"{i}. {emoji} **{label}**: {symbol}{name_str}"
                f" {ratio*100:.0f}% reduction \u2192 {reason}"
            )
            if value > 0:
                lines.append(f"   Freed funds: \u00a5{value:,.0f}")
            lot_note = _estimate_shares_annotation(
                symbol, value, action.get("current_price"),
            )
            if lot_note:
                lines.append(f"   {lot_note}")
        elif act_type == "increase":
            amount = action.get("amount_jpy", 0)
            lines.append(
                f"{i}. {emoji} **{label}**: {symbol}{name_str}"
                f" +\u00a5{amount:,.0f} \u2192 {reason}"
            )
            lot_note = _estimate_shares_annotation(
                symbol, amount, action.get("current_price"),
            )
            if lot_note:
                lines.append(f"   {lot_note}")

        lines.append("")

    # --- Constraints ---
    constraints = proposal.get("constraints", {})
    if constraints:
        lines.append("### Applied Constraints")
        lines.append("")
        lines.append(
            f"- Single stock limit: {constraints.get('max_single_ratio', 0)*100:.0f}%"
        )
        lines.append(
            f"- Sector HHI limit: {constraints.get('max_sector_hhi', 0):.2f}"
        )
        lines.append(
            f"- Region HHI limit: {constraints.get('max_region_hhi', 0):.2f}"
        )
        lines.append(
            f"- Correlated pair limit:"
            f" {constraints.get('max_corr_pair_ratio', 0)*100:.0f}%"
        )
        lines.append("")

    return "\n".join(lines)
