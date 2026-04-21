"""Simulation and what-if output formatters (KIK-447, split from portfolio_formatter.py)."""

from src.output._format_helpers import fmt_pct_sign as _fmt_pct_sign
from src.output._format_helpers import fmt_float as _fmt_float
from src.output._portfolio_utils import _fmt_jpy, _fmt_currency_value, _fmt_k


_JUDGMENT_EMOJI = {
    "recommend": "\u2705",       # ✅
    "caution": "\u26a0\ufe0f",   # ⚠️
    "not_recommended": "\U0001f6a8",  # 🚨
}

_JUDGMENT_LABEL = {
    "recommend": "This addition is recommended",
    "caution": "Review with caution",
    "not_recommended": "This addition is not recommended",
}

_JUDGMENT_LABEL_SWAP = {
    "recommend": "This swap is recommended",
    "caution": "Review with caution",
    "not_recommended": "This swap is not recommended",
}


def format_simulation(result) -> str:
    """Format compound interest simulation results as Markdown.

    Parameters
    ----------
    result : SimulationResult or dict
        Output from simulator.simulate_portfolio().

    Returns
    -------
    str
        Markdown-formatted simulation report.
    """
    # Support both SimulationResult and dict
    if hasattr(result, "to_dict"):
        d = result.to_dict()
    else:
        d = result

    scenarios = d.get("scenarios", {})
    years = d.get("years", 0)
    monthly_add = d.get("monthly_add", 0.0)
    reinvest_dividends = d.get("reinvest_dividends", True)
    target = d.get("target")

    lines: list[str] = []

    # Empty scenarios
    if not scenarios:
        lines.append("## Compound Interest Simulation")
        lines.append("")
        lines.append(
            "Could not retrieve estimated returns. "
            "Please run /stock-portfolio forecast first."
        )
        return "\n".join(lines)

    # Header
    if monthly_add > 0:
        add_str = f"Monthly \u00a5{monthly_add:,.0f} accumulation"
    else:
        add_str = "No accumulation"
    lines.append(f"## {years}-Year Simulation ({add_str})")
    lines.append("")

    # Base scenario table
    base_snapshots = scenarios.get("base", [])
    if base_snapshots:
        base_return = d.get("portfolio_return_base")
        if base_return is not None:
            ret_str = f"{base_return * 100:+.2f}%"
        else:
            ret_str = "-"
        lines.append(f"### Base Scenario (Annual Return {ret_str})")
        lines.append("")
        lines.append("| Year | Value | Cumulative Input | Capital Gain | Cumulative Dividends |")
        lines.append("|----|--------|----------|--------|----------|")

        for snap in base_snapshots:
            yr = snap.get("year", 0) if isinstance(snap, dict) else snap.year
            value = snap.get("value", 0) if isinstance(snap, dict) else snap.value
            cum_input = snap.get("cumulative_input", 0) if isinstance(snap, dict) else snap.cumulative_input
            cap_gain = snap.get("capital_gain", 0) if isinstance(snap, dict) else snap.capital_gain
            cum_div = snap.get("cumulative_dividends", 0) if isinstance(snap, dict) else snap.cumulative_dividends

            if yr == 0:
                lines.append(
                    f"| {yr} | {_fmt_k(value)} | {_fmt_k(cum_input)} | - | - |"
                )
            else:
                lines.append(
                    f"| {yr} | {_fmt_k(value)} | {_fmt_k(cum_input)} "
                    f"| {_fmt_k(cap_gain)} | {_fmt_k(cum_div)} |"
                )

        lines.append("")

    # Scenario comparison (final year)
    scenario_labels = {
        "optimistic": "Optimistic",
        "base": "Base",
        "pessimistic": "Pessimistic",
    }

    has_comparison = len(scenarios) > 1 or (len(scenarios) == 1 and "base" in scenarios)
    if has_comparison:
        lines.append("### Scenario Comparison (Final Year)")
        lines.append("")
        lines.append("| Scenario | Final Value | Capital Gain |")
        lines.append("|:---------|----------:|-------:|")

        for key in ["optimistic", "base", "pessimistic"]:
            snaps = scenarios.get(key)
            if not snaps:
                continue
            last = snaps[-1]
            value = last.get("value", 0) if isinstance(last, dict) else last.value
            cap_gain = last.get("capital_gain", 0) if isinstance(last, dict) else last.capital_gain
            label = scenario_labels.get(key, key)
            lines.append(
                f"| {label} | {_fmt_k(value)} | {_fmt_k(cap_gain)} |"
            )

        lines.append("")

    # Target analysis
    if target is not None:
        lines.append("### Target Achievement Analysis")
        lines.append("")
        lines.append(f"- Target: {_fmt_k(target)}")

        target_year_base = d.get("target_year_base")
        target_year_opt = d.get("target_year_optimistic")
        target_year_pess = d.get("target_year_pessimistic")

        if target_year_base is not None:
            lines.append(
                f"- Base scenario: "
                f"**projected to be reached in {target_year_base:.1f} years**"
            )
        else:
            lines.append("- Base scenario: not reached within period")

        if target_year_opt is not None:
            lines.append(
                f"- Optimistic scenario: "
                f"projected to be reached in {target_year_opt:.1f} years"
            )
        elif "optimistic" in scenarios:
            lines.append("- Optimistic scenario: not reached within period")

        if target_year_pess is not None:
            lines.append(
                f"- Pessimistic scenario: "
                f"projected to be reached in {target_year_pess:.1f} years"
            )
        elif "pessimistic" in scenarios:
            lines.append("- Pessimistic scenario: not reached within period")

        required_monthly = d.get("required_monthly")
        if required_monthly is not None and required_monthly > 0:
            lines.append("")
            lines.append(
                f"- Monthly savings required to reach target: "
                f"\u00a5{required_monthly:,.0f}"
            )

        lines.append("")

    # Dividend reinvestment effect
    dividend_effect = d.get("dividend_effect", 0)
    dividend_effect_pct = d.get("dividend_effect_pct", 0)

    lines.append("### Effect of Dividend Reinvestment")
    lines.append("")

    if not reinvest_dividends:
        lines.append("- Dividend reinvestment: OFF")
    else:
        lines.append(
            f"- Compounding effect from dividend reinvestment: "
            f"+{_fmt_k(dividend_effect)}"
        )
        lines.append(
            f"- vs. no dividend reinvestment: "
            f"+{dividend_effect_pct * 100:.1f}%"
        )

    lines.append("")

    return "\n".join(lines)


def _fmt_health_section(health_list: list[dict], title: str) -> list[str]:
    """Format a health check section (shared by proposed and removed stocks)."""
    lines: list[str] = [f"### {title}", ""]
    for ph in health_list:
        symbol = ph.get("symbol", "-")
        alert = ph.get("alert", {})
        level = alert.get("level", "none")
        label = alert.get("label", "None")
        if level == "none":
            lines.append(f"✅ {symbol}: OK")
        elif level == "early_warning":
            lines.append(f"⚡ {symbol}: {label}")
        elif level == "caution":
            lines.append(f"⚠️ {symbol}: {label}")
        elif level == "exit":
            lines.append(f"🚨 {symbol}: {label}")
        # KIK-469 Phase 2: ETF info
        etf_h = ph.get("change_quality", {}).get("etf_health")
        if etf_h:
            exp = etf_h.get("expense_label", "-")
            aum = etf_h.get("aum_label", "-")
            score = etf_h.get("score", "-")
            lines.append(f"  ETF: Expense ratio {exp} / AUM {aum} / Score {score}/100")
            for etf_alert in etf_h.get("alerts", []):
                lines.append(f"  \u26a0\ufe0f {etf_alert}")
    lines.append("")
    return lines


def format_what_if(result: dict) -> str:
    """Format What-If simulation result as Markdown.

    Parameters
    ----------
    result : dict
        Output from portfolio_simulation.run_what_if_simulation().
        KIK-451: Supports optional swap fields: removals, removed_health,
        proceeds_jpy, net_cash_jpy.

    Returns
    -------
    str
        Markdown-formatted What-If report.
    """
    lines: list[str] = []

    proposed = result.get("proposed", [])
    removals = result.get("removals", [])    # KIK-451
    before = result.get("before", {})
    after = result.get("after", {})
    proposed_health = result.get("proposed_health", [])
    removed_health = result.get("removed_health", [])    # KIK-451
    required_cash = result.get("required_cash_jpy", 0)
    proceeds = result.get("proceeds_jpy")    # KIK-451 (None when not a swap)
    net_cash = result.get("net_cash_jpy")    # KIK-451
    judgment = result.get("judgment", {})

    is_swap = bool(removals)

    lines.append("## What-If Simulation")
    lines.append("")

    # --- (KIK-451) Removed stocks table ---
    if removals:
        lines.append("### Stocks Being Sold")
        lines.append("")
        lines.append("| Symbol | Shares | Sale Proceeds (Estimate) |")
        lines.append("|:-----|-----:|----------------:|")
        for rem in removals:
            symbol = rem.get("symbol", "-")
            shares = rem.get("shares", 0)
            rem_proceeds = rem.get("proceeds_jpy", 0.0)
            lines.append(
                f"| {symbol} | {shares:,} | {_fmt_jpy(rem_proceeds)} |"
            )
        lines.append("")
        lines.append(f"Total sale proceeds: {_fmt_jpy(proceeds or 0.0)}")
        lines.append("")

    # --- Proposed stocks ---
    if proposed:
        lines.append("### Stocks Being Added")
        lines.append("")
        lines.append("| Symbol | Shares | Unit Price | Currency | Amount |")
        lines.append("|:-----|-----:|------:|:-----|------:|")

        for prop in proposed:
            symbol = prop.get("symbol", "-")
            shares = prop.get("shares", 0)
            price = prop.get("cost_price", 0)
            currency = prop.get("cost_currency", "JPY")
            amount = shares * price
            price_str = _fmt_currency_value(price, currency)
            amount_str = _fmt_currency_value(amount, currency)
            lines.append(
                f"| {symbol} | {shares:,} | {price_str} "
                f"| {currency} | {amount_str} |"
            )

        lines.append("")
        lines.append(f"Total required funds: {_fmt_jpy(required_cash)}")
        lines.append("")

    # --- (KIK-451) Cash balance for swap mode ---
    if is_swap:
        lines.append("### Cash Balance")
        lines.append("")
        lines.append("| Item | Amount |")
        lines.append("|:-----|-----:|")
        if proposed:
            lines.append(f"| Purchase funds required | {_fmt_jpy(required_cash)} |")
        lines.append(f"| Sale proceeds (estimate) | {_fmt_jpy(proceeds or 0.0)} |")
        if net_cash is not None and proposed:
            suffix = " (surplus)" if net_cash >= 0 else " (additional funds needed)"
            lines.append(f"| Balance | {_fmt_jpy(net_cash)}{suffix} |")
        lines.append("")

    # --- Portfolio change comparison ---
    after_label = "After Swap" if is_swap else "After Addition"
    lines.append("### Portfolio Change")
    lines.append("")
    lines.append(f"| Metric | Current | {after_label} | Change |")
    lines.append("|:-----|------:|------:|:------|")

    # Total value
    bv = before.get("total_value_jpy", 0)
    av = after.get("total_value_jpy", 0)
    if bv > 0:
        change_pct = (av - bv) / bv
        change_str = _fmt_pct_sign(change_pct)
    else:
        change_str = "-"
    lines.append(
        f"| Total Value | {_fmt_jpy(bv)} | {_fmt_jpy(av)} | {change_str} |"
    )

    # Sector HHI
    b_shhi = before.get("sector_hhi", 0)
    a_shhi = after.get("sector_hhi", 0)
    hhi_indicator = (
        "✅ Improved" if a_shhi < b_shhi
        else "⚠️ Worsened" if a_shhi > b_shhi
        else "↔️ Unchanged"
    )
    lines.append(
        f"| Sector HHI | {_fmt_float(b_shhi, 2)} "
        f"| {_fmt_float(a_shhi, 2)} | {hhi_indicator} |"
    )

    # Region HHI
    b_rhhi = before.get("region_hhi", 0)
    a_rhhi = after.get("region_hhi", 0)
    rhhi_indicator = (
        "✅ Improved" if a_rhhi < b_rhhi
        else "⚠️ Worsened" if a_rhhi > b_rhhi
        else "↔️ Unchanged"
    )
    lines.append(
        f"| Region HHI | {_fmt_float(b_rhhi, 2)} "
        f"| {_fmt_float(a_rhhi, 2)} | {rhhi_indicator} |"
    )

    # Forecast base return
    b_ret = before.get("forecast_base")
    a_ret = after.get("forecast_base")
    if b_ret is not None and a_ret is not None:
        diff_pp = (a_ret - b_ret) * 100
        ret_indicator = (
            f"✅ +{diff_pp:.1f}pp" if diff_pp > 0
            else f"⚠️ {diff_pp:.1f}pp" if diff_pp < 0
            else "↔️ 0pp"
        )
        lines.append(
            f"| Expected Return (Base) "
            f"| {_fmt_pct_sign(b_ret)} "
            f"| {_fmt_pct_sign(a_ret)} | {ret_indicator} |"
        )
    lines.append("")

    # --- Proposed stock health ---
    if proposed_health:
        lines += _fmt_health_section(proposed_health, "Proposed Stock Health Check")

    # --- (KIK-451) Removed stock health ---
    if removed_health:
        lines += _fmt_health_section(removed_health, "Sell Stock Health Check")

    # --- Judgment ---
    lines.append("### Overall Judgment")
    lines.append("")
    rec = judgment.get("recommendation", "caution")
    emoji = _JUDGMENT_EMOJI.get(rec, "")
    if is_swap and proposed:
        label = _JUDGMENT_LABEL_SWAP.get(rec, rec)
    else:
        label = _JUDGMENT_LABEL.get(rec, rec)
    lines.append(f"{emoji} **{label}**")
    for reason in judgment.get("reasons", []):
        lines.append(f"- {reason}")
    lines.append("")

    return "\n".join(lines)
