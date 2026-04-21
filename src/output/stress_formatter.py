"""Output formatters for stress test results (KIK-339/340/341/352)."""

import math
from typing import Optional

from src.output._format_helpers import fmt_pct as _fmt_pct
from src.output._format_helpers import fmt_pct_sign as _fmt_pct_sign
from src.output._format_helpers import fmt_float as _fmt_float
from src.output._format_helpers import fmt_float_sign as _fmt_float_sign
from src.output._format_helpers import hhi_bar as _hhi_bar
from src.output._format_helpers import fmt_currency_value as _fmt_currency_value


def _fmt_currency(value: Optional[float]) -> str:
    """Format a currency value using the canonical formatter.

    Delegates to ``_fmt_currency_value`` (JPY default).
    """
    return _fmt_currency_value(value)


# ---------------------------------------------------------------------------
# Concentration Analysis Report
# ---------------------------------------------------------------------------

def format_concentration_report(concentration: dict) -> str:
    """Format concentration analysis as a Markdown report."""
    lines: list[str] = []
    lines.append("## Step 2: Concentration Analysis")
    lines.append("")

    risk_level = concentration.get("risk_level", "-")
    max_hhi = concentration.get("max_hhi", 0.0)
    max_axis = concentration.get("max_hhi_axis", "-")
    multiplier = concentration.get("concentration_multiplier", 1.0)

    lines.append(f"**Overall Judgment: {risk_level}** (Max HHI: {_fmt_float(max_hhi, 4)} / Axis: {max_axis})")
    lines.append(f"Concentration multiplier: x{_fmt_float(multiplier, 2)}")
    lines.append("")

    # Sector breakdown
    lines.append("### Sector Allocation")
    sector_hhi = concentration.get("sector_hhi", 0.0)
    lines.append(f"HHI: {_fmt_float(sector_hhi, 4)} {_hhi_bar(sector_hhi)}")
    lines.append("")
    lines.append("| Sector | Weight |")
    lines.append("|:---------|-----:|")
    sector_breakdown = concentration.get("sector_breakdown", {})
    for sector, weight in sorted(sector_breakdown.items(), key=lambda x: -x[1]):
        lines.append(f"| {sector} | {_fmt_pct(weight)} |")
    lines.append("")

    # Region breakdown
    lines.append("### Region Allocation")
    region_hhi = concentration.get("region_hhi", 0.0)
    lines.append(f"HHI: {_fmt_float(region_hhi, 4)} {_hhi_bar(region_hhi)}")
    lines.append("")
    lines.append("| Region | Weight |")
    lines.append("|:-----|-----:|")
    region_breakdown = concentration.get("region_breakdown", {})
    for region, weight in sorted(region_breakdown.items(), key=lambda x: -x[1]):
        lines.append(f"| {region} | {_fmt_pct(weight)} |")
    lines.append("")

    # Currency breakdown
    lines.append("### Currency Allocation")
    currency_hhi = concentration.get("currency_hhi", 0.0)
    lines.append(f"HHI: {_fmt_float(currency_hhi, 4)} {_hhi_bar(currency_hhi)}")
    lines.append("")
    lines.append("| Currency | Weight |")
    lines.append("|:-----|-----:|")
    currency_breakdown = concentration.get("currency_breakdown", {})
    for currency, weight in sorted(currency_breakdown.items(), key=lambda x: -x[1]):
        lines.append(f"| {currency} | {_fmt_pct(weight)} |")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Shock Sensitivity Report
# ---------------------------------------------------------------------------

def format_sensitivity_report(sensitivities: list[dict]) -> str:
    """Format shock sensitivity as a Markdown table.

    Parameters
    ----------
    sensitivities : list[dict]
        Per-stock sensitivity analysis results. Expected keys:
        - "symbol", "name"
        - "fundamental_score", "technical_score"
        - "quadrant"
        - "composite_shock"
    """
    lines: list[str] = []
    lines.append("## Step 3: Shock Sensitivity")
    lines.append("")

    if not sensitivities:
        lines.append("No sensitivity data available.")
        return "\n".join(lines)

    lines.append("| Symbol | Fundamental | Technical | Quadrant | Composite Shock |")
    lines.append("|:-----|-------:|----------:|:-----|----------:|")

    for s in sensitivities:
        symbol = s.get("symbol", "-")
        name = s.get("name", "")
        label = f"{symbol} {name}".strip() if name else symbol
        fund_score = _fmt_float(s.get("fundamental_score"))
        tech_score = _fmt_float(s.get("technical_score"))
        quadrant = s.get("quadrant", "-")
        composite = _fmt_pct_sign(s.get("composite_shock"))
        lines.append(f"| {label} | {fund_score} | {tech_score} | {quadrant} | {composite} |")

    lines.append("")

    # 4-quadrant matrix (text-based)
    lines.append("### 4-Quadrant Matrix")
    lines.append("```")
    lines.append("         Weak Fundamental      Strong Fundamental")
    lines.append("        +------------------+------------------+")
    lines.append("Strong  |    Caution       |    Solid         |")
    lines.append("Tech    |    (High Risk)   |    (Low Risk)    |")
    lines.append("        +------------------+------------------+")
    lines.append("Weak    |    Danger        |    Recovery      |")
    lines.append("Tech    |  (Highest Risk)  |    (Med Risk)    |")
    lines.append("        +------------------+------------------+")
    lines.append("```")
    lines.append("")

    # Stocks by quadrant
    quadrant_map: dict[str, list[str]] = {}
    for s in sensitivities:
        q = s.get("quadrant", "Unknown")
        sym = s.get("symbol", "?")
        quadrant_map.setdefault(q, []).append(sym)

    if quadrant_map:
        for q, symbols in quadrant_map.items():
            lines.append(f"- **{q}**: {', '.join(symbols)}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Scenario Causal Chain Report
# ---------------------------------------------------------------------------

def format_scenario_report(scenario_result: dict) -> str:
    """Format scenario analysis as a Markdown report."""
    lines: list[str] = []

    scenario_name = scenario_result.get("scenario_name", "Unknown")
    trigger = scenario_result.get("trigger", "Unknown")
    pf_impact = scenario_result.get("portfolio_impact", 0.0)
    pf_value_change = scenario_result.get("portfolio_value_change", 0.0)
    judgment = scenario_result.get("judgment", "-")

    lines.append(f"## Step 4-5: Scenario Causal Chain Analysis - {scenario_name}")
    lines.append("")
    lines.append(f"**Trigger:** {trigger}")
    lines.append("")

    # Causal chain diagram
    lines.append("### Causal Chain")
    lines.append("```")
    chain_summary = scenario_result.get("causal_chain_summary", "")
    if chain_summary:
        lines.append(chain_summary)
    lines.append("```")
    lines.append("")

    # Per-stock impact table
    stock_impacts = scenario_result.get("stock_impacts", [])
    if stock_impacts:
        lines.append("### Per-Stock Impact")
        lines.append("")
        lines.append("| Symbol | Weight | Direct Impact | Currency Effect | Total | PF Contribution |")
        lines.append("|:-----|-----:|-------:|-------:|-----:|------:|")

        for si in stock_impacts:
            symbol = si.get("symbol", "-")
            name = si.get("name", "")
            label = f"{symbol} {name}".strip() if name else symbol
            weight = _fmt_pct(si.get("weight"))
            direct = _fmt_pct_sign(si.get("direct_impact"))
            currency = _fmt_pct_sign(si.get("currency_impact"))
            total = _fmt_pct_sign(si.get("total_impact"))
            pf_contrib = _fmt_pct_sign(si.get("pf_contribution"))
            lines.append(f"| {label} | {weight} | {direct} | {currency} | {total} | {pf_contrib} |")

        lines.append("")

    # Offset factors
    offset_factors = scenario_result.get("offset_factors", [])
    if offset_factors:
        lines.append("### Offset Factors")
        for factor in offset_factors:
            lines.append(f"- {factor}")
        lines.append("")

    # Time horizon
    time_axis = scenario_result.get("time_axis", "")
    if time_axis:
        lines.append(f"**Time Horizon:** {time_axis}")
        lines.append("")

    # Judgment mapping
    _JUDGMENT_MAP = {
        "要対応": "Action Required",
        "認識": "Monitor",
        "継続": "Continue",
    }
    judgment_display = _JUDGMENT_MAP.get(judgment, judgment)

    lines.append(f"## Step 6: Quantitative Results")
    lines.append("")
    lines.append(f"- **PF Impact:** {_fmt_pct_sign(pf_impact)}")
    lines.append(f"- **Value Change:** {_fmt_currency(pf_value_change)}")
    lines.append(f"- **Judgment:** {judgment_display}")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Correlation Analysis Report (KIK-352)
# ---------------------------------------------------------------------------

def format_correlation_report(
    corr_result: dict,
    high_pairs: list[dict],
    factor_results: Optional[list[dict]] = None,
) -> str:
    """Format correlation analysis as a Markdown report."""
    lines: list[str] = []
    lines.append("## Correlation Analysis")
    lines.append("")

    symbols = corr_result.get("symbols", [])
    matrix = corr_result.get("matrix", [])
    n = len(symbols)

    if n < 2:
        lines.append("Fewer than 2 stocks — correlation analysis skipped.")
        lines.append("")
        return "\n".join(lines)

    # Correlation matrix table
    lines.append("### Correlation Matrix")
    lines.append("")
    header = "| |" + "|".join(f" {s} " for s in symbols) + "|"
    lines.append(header)
    sep = "|:-----|" + "|".join("-----:" for _ in symbols) + "|"
    lines.append(sep)
    for i in range(n):
        row_vals = []
        for j in range(n):
            v = matrix[i][j]
            if i == j:
                row_vals.append(" 1.00 ")
            elif isinstance(v, (int, float)) and not math.isnan(v):
                row_vals.append(f" {v:+.2f} ")
            else:
                row_vals.append(" - ")
        lines.append(f"| {symbols[i]} |" + "|".join(row_vals) + "|")
    lines.append("")

    # High correlation pairs
    if high_pairs:
        lines.append("### High Correlation Pairs")
        lines.append("")
        lines.append("| Pair | Correlation | Label |")
        lines.append("|:-----|-------:|:-----|")
        for p in high_pairs:
            pair = p.get("pair", ["?", "?"])
            corr = p.get("correlation", 0)
            label = p.get("label", "-")
            lines.append(f"| {pair[0]} x {pair[1]} | {corr:+.4f} | {label} |")
        lines.append("")
    else:
        lines.append("No high correlation pairs detected (|r| >= 0.7).")
        lines.append("")

    # Factor decomposition
    if factor_results:
        lines.append("### Factor Decomposition")
        lines.append("")
        for fr in factor_results:
            sym = fr.get("symbol", "?")
            r2 = fr.get("r_squared", 0)
            factors = fr.get("factors", [])
            if not factors:
                continue
            lines.append(f"**{sym}** (R²={_fmt_float(r2, 4)})")
            lines.append("")
            lines.append("| Factor | Beta | Contribution |")
            lines.append("|:---------|-----:|------:|")
            for f in factors[:5]:  # top 5
                lines.append(
                    f"| {f['name']} | {_fmt_float_sign(f.get('beta'), 4)} "
                    f"| {_fmt_float(f.get('contribution'), 4)} |"
                )
            lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# VaR Report (KIK-352)
# ---------------------------------------------------------------------------

def format_var_report(var_result: dict) -> str:
    """Format VaR analysis as a Markdown report."""
    lines: list[str] = []
    lines.append("## Risk Metrics (Historical)")
    lines.append("")

    obs = var_result.get("observation_days", 0)
    if obs < 30:
        lines.append("Insufficient data — VaR calculation skipped.")
        lines.append("")
        return "\n".join(lines)

    daily_var = var_result.get("daily_var", {})
    monthly_var = var_result.get("monthly_var", {})
    daily_var_amount = var_result.get("daily_var_amount", {})
    monthly_var_amount = var_result.get("monthly_var_amount", {})
    portfolio_vol = var_result.get("portfolio_volatility", 0)

    lines.append(f"Observation period: {obs} trading days")
    lines.append(f"PF Volatility (annualized): {_fmt_pct(portfolio_vol)}")
    lines.append("")

    lines.append("| Metric | Loss Rate | Loss Amount |")
    lines.append("|:-----|------:|------:|")

    for cl in [0.95, 0.99]:
        cl_label = f"{int(cl*100)}%"

        d_var = daily_var.get(cl)
        d_amt = daily_var_amount.get(cl)
        d_var_str = _fmt_pct_sign(d_var) if d_var is not None else "-"
        d_amt_str = _fmt_currency(d_amt) if d_amt is not None else "-"
        lines.append(f"| Daily VaR ({cl_label}) | {d_var_str} | {d_amt_str} |")

        m_var = monthly_var.get(cl)
        m_amt = monthly_var_amount.get(cl)
        m_var_str = _fmt_pct_sign(m_var) if m_var is not None else "-"
        m_amt_str = _fmt_currency(m_amt) if m_amt is not None else "-"
        lines.append(f"| Monthly VaR ({cl_label}) | {m_var_str} | {m_amt_str} |")

    lines.append("")
    lines.append(
        "*VaR represents the upper bound of normal fluctuation. "
        "Tail risks (triple meltdown, etc.) are covered by scenario analysis.*"
    )
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Recommendations Report (KIK-352)
# ---------------------------------------------------------------------------

def format_recommendations_report(recommendations: list[dict]) -> str:
    """Format recommended actions as a Markdown report."""
    lines: list[str] = []
    lines.append("## Recommended Actions (Auto-Generated)")
    lines.append("")

    if not recommendations:
        lines.append("No notable recommended actions.")
        lines.append("")
        return "\n".join(lines)

    _PRIORITY_EMOJI = {"high": "!!!", "medium": "!!", "low": "!"}
    _CATEGORY_LABELS = {
        "concentration": "Concentration",
        "correlation": "Correlation",
        "var": "VaR",
        "stress": "Stress",
        "sensitivity": "Sensitivity",
    }

    for i, rec in enumerate(recommendations, 1):
        priority = rec.get("priority", "low")
        category = _CATEGORY_LABELS.get(rec.get("category", ""), rec.get("category", ""))
        title = rec.get("title", "")
        detail = rec.get("detail", "")
        action = rec.get("action", "")
        priority_mark = _PRIORITY_EMOJI.get(priority, "!")

        lines.append(f"**{i}. [{priority_mark}] [{category}] {title}**")
        if detail:
            lines.append(f"   {detail}")
        if action:
            lines.append(f"   -> {action}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Full Stress Test Report
# ---------------------------------------------------------------------------

def format_full_stress_report(
    portfolio_summary: dict,
    concentration: dict,
    sensitivities: list[dict],
    scenario_result: dict,
    *,
    correlation: Optional[dict] = None,
    high_correlation_pairs: Optional[list[dict]] = None,
    factor_decomposition: Optional[list[dict]] = None,
    var_result: Optional[dict] = None,
    recommendations: Optional[list[dict]] = None,
) -> str:
    """Format the full stress test Markdown report.

    Step 1: PF Overview
    Step 2: Concentration Analysis
    Step 3: Shock Sensitivity
    Step 4-5: Scenario Causal Chain
    Step 6: Quantitative Results
    Step 6b: Correlation Analysis (KIK-352)
    Step 6c: VaR (KIK-352)
    Step 7: Historical Cases (added by Claude)
    Step 8: Overall Judgment
    Step 8b: Recommended Actions (KIK-352)
    """
    lines: list[str] = []

    # ===== Header =====
    scenario_name = scenario_result.get("scenario_name", "Unknown")
    lines.append(f"# Stress Test Report: {scenario_name}")
    lines.append("")

    # ===== Step 1: PF Overview =====
    lines.append("## Step 1: Portfolio Overview")
    lines.append("")

    total_value = portfolio_summary.get("total_value")
    stock_count = portfolio_summary.get("stock_count", 0)
    if total_value is not None:
        lines.append(f"- **PF Total Value:** {total_value:,.0f}")
    lines.append(f"- **Number of Stocks:** {stock_count}")
    lines.append("")

    stocks = portfolio_summary.get("stocks", [])
    if stocks:
        lines.append("| Symbol | Weight | Price | Sector |")
        lines.append("|:-----|-----:|-----:|:---------|")
        for s in stocks:
            symbol = s.get("symbol", "-")
            name = s.get("name", "")
            label = f"{symbol} {name}".strip() if name else symbol
            weight = _fmt_pct(s.get("weight"))
            price = _fmt_float(s.get("price"), decimals=0) if s.get("price") is not None else "-"
            sector = s.get("sector") or "-"
            lines.append(f"| {label} | {weight} | {price} | {sector} |")
        lines.append("")

    # ===== Step 2: Concentration Analysis =====
    lines.append(format_concentration_report(concentration))

    # ===== Step 3: Shock Sensitivity =====
    lines.append(format_sensitivity_report(sensitivities))

    # ===== Step 4-5-6: Scenario Analysis =====
    lines.append(format_scenario_report(scenario_result))

    # ===== Step 6b: Correlation Analysis (KIK-352) =====
    if correlation is not None:
        lines.append(format_correlation_report(
            correlation,
            high_correlation_pairs or [],
            factor_decomposition,
        ))

    # ===== Step 6c: VaR (KIK-352) =====
    if var_result is not None:
        lines.append(format_var_report(var_result))

    # ===== Step 7: Historical Cases =====
    lines.append("## Step 7: Historical Cases")
    lines.append("")
    lines.append("(Historical cases for similar scenarios will be supplemented by Claude)")
    lines.append("")

    # ===== Step 8: Overall Judgment =====
    lines.append("## Step 8: Overall Judgment")
    lines.append("")

    risk_level = concentration.get("risk_level", "-")
    pf_impact = scenario_result.get("portfolio_impact", 0.0)
    judgment = scenario_result.get("judgment", "-")

    _JUDGMENT_MAP = {
        "要対応": "Action Required",
        "認識": "Monitor",
        "継続": "Continue",
    }

    lines.append("| Item | Result |")
    lines.append("|:-----|:-----|")
    lines.append(f"| Concentration Risk | {risk_level} |")
    lines.append(f"| Scenario Impact | {_fmt_pct_sign(pf_impact)} |")
    lines.append(f"| Judgment | {_JUDGMENT_MAP.get(judgment, judgment)} |")

    # VaR summary in judgment table
    if var_result and var_result.get("daily_var"):
        daily_95 = var_result.get("daily_var", {}).get(0.95)
        if daily_95 is not None:
            lines.append(f"| Daily VaR (95%) | {_fmt_pct_sign(daily_95)} |")

    lines.append("")

    # ===== Step 8b: Recommended Actions (KIK-352) =====
    if recommendations:
        lines.append(format_recommendations_report(recommendations))
    else:
        # Fallback recommendations
        lines.append("### Recommended Actions")
        if judgment in ("要対応", "Action Required"):
            lines.append("- PF impact exceeds -30%. Risk mitigation is required.")
            lines.append("- Consider building a hedge position.")
            lines.append("- Review the ratio of overconcentrated sectors/regions.")
        elif judgment in ("認識", "Monitor"):
            lines.append("- PF impact exceeds -15%. Acknowledge the risk and continue monitoring.")
            lines.append("- Watch for signs of trigger events.")
            if risk_level not in ("-", "Low risk", "Continue"):
                lines.append(f"- Concentration level is \"{risk_level}\". Consider diversifying.")
        else:
            lines.append("- No major risks detected at this time.")
            lines.append("- Continue regular monitoring.")
        lines.append("")

    return "\n".join(lines)
