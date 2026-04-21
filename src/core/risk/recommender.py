"""Rule-based portfolio recommendation engine (KIK-352).

Generates actionable recommendations from:
  - HHI concentration analysis
  - Correlation analysis
  - VaR analysis
  - Scenario stress test results
  - Shock sensitivity analysis
"""

from typing import Optional

# ---------------------------------------------------------------------------
# Thresholds for recommendation rules
# ---------------------------------------------------------------------------

HHI_DANGER = 0.50  # HHI above this is "danger"
HHI_MODERATE = 0.25  # HHI above this is "moderate concern"
CORR_VERY_HIGH = 0.85  # Very strong correlation
CORR_HIGH = 0.70  # High correlation
VAR_SEVERE = -0.15  # Monthly VaR(95%) severe threshold
VAR_WARNING = -0.10  # Monthly VaR(95%) warning threshold
VOLATILITY_HIGH = 0.30  # Annualized portfolio volatility threshold
STRESS_SEVERE_IMPACT = -0.30  # Individual stock stress impact threshold


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_recommendations(
    concentration: dict,
    correlation_pairs: Optional[list[dict]] = None,
    var_result: Optional[dict] = None,
    scenario_result: Optional[dict] = None,
    sensitivities: Optional[list[dict]] = None,
) -> list[dict]:
    """Generate rule-based portfolio recommendations.

    Parameters
    ----------
    concentration : dict
        Output of ``analyze_concentration()``.
    correlation_pairs : list[dict] or None
        Output of ``find_high_correlation_pairs()``.
    var_result : dict or None
        Output of ``compute_var()``.
    scenario_result : dict or None
        Output of ``analyze_portfolio_scenario()``.
    sensitivities : list[dict] or None
        Per-stock sensitivity analysis results from ``analyze_stock_sensitivity()``.

    Returns
    -------
    list[dict]
        Each recommendation: {
            "priority": str ("high", "medium", "low"),
            "category": str,
            "title": str,
            "detail": str,
            "action": str,
        }
        Sorted by priority (high first).
    """
    recs: list[dict] = []

    recs.extend(_check_concentration(concentration))

    if correlation_pairs:
        recs.extend(_check_correlations(correlation_pairs))

    if var_result:
        recs.extend(_check_var(var_result))

    if scenario_result is not None:
        recs.extend(_check_stress(scenario_result))

    if sensitivities:
        recs.extend(_check_sensitivities(sensitivities))

    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    recs.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 3))

    return recs


# ---------------------------------------------------------------------------
# Concentration checks
# ---------------------------------------------------------------------------

_ALL_SECTORS = [
    "Technology", "Healthcare", "Financial Services",
    "Consumer Defensive", "Industrials", "Energy",
    "Basic Materials", "Utilities", "Real Estate",
    "Communication Services", "Consumer Cyclical",
]


def _suggest_diversification_sector(sector_breakdown: dict) -> str:
    """Suggest sectors not present in the portfolio."""
    missing = [s for s in _ALL_SECTORS if s not in sector_breakdown]
    if missing:
        return ", ".join(missing[:3])
    return "Other sector"


def _check_concentration(concentration: dict) -> list[dict]:
    """Generate recommendations from concentration analysis."""
    recs: list[dict] = []

    # Sector concentration
    sector_hhi = concentration.get("sector_hhi", 0)
    sector_breakdown = concentration.get("sector_breakdown", {})
    if sector_hhi > HHI_DANGER and sector_breakdown:
        top_sector = max(sector_breakdown, key=sector_breakdown.get)
        top_weight = sector_breakdown.get(top_sector, 0)
        suggestion = _suggest_diversification_sector(sector_breakdown)
        recs.append({
            "priority": "high",
            "category": "concentration",
            "title": f"Sector concentration risk: {top_sector} {top_weight*100:.0f}%",
            "detail": (
                f"Sector HHI={sector_hhi:.4f} (danger level). "
                f"Exposure to {top_sector} is too high."
            ),
            "action": f"Consider adding stocks from a different sector (e.g., {suggestion})",
        })
    elif sector_hhi > HHI_MODERATE and sector_breakdown:
        top_sector = max(sector_breakdown, key=sector_breakdown.get)
        recs.append({
            "priority": "medium",
            "category": "concentration",
            "title": f"Sector slightly concentrated: {top_sector}",
            "detail": f"Sector HHI={sector_hhi:.4f}. Diversification is insufficient.",
            "action": "Consider improving sector diversification",
        })

    # Region concentration
    region_hhi = concentration.get("region_hhi", 0)
    region_breakdown = concentration.get("region_breakdown", {})
    if region_hhi > HHI_DANGER and region_breakdown:
        top_region = max(region_breakdown, key=region_breakdown.get)
        top_weight = region_breakdown.get(top_region, 0)
        recs.append({
            "priority": "high",
            "category": "concentration",
            "title": f"Region concentration risk: {top_region} {top_weight*100:.0f}%",
            "detail": (
                f"Region HHI={region_hhi:.4f} (danger level). "
                f"Exposure to {top_region} is too high."
            ),
            "action": "Consider adding stocks from other regions (US/ASEAN/Europe)",
        })
    elif region_hhi > HHI_MODERATE:
        recs.append({
            "priority": "low",
            "category": "concentration",
            "title": "Region allocation slightly skewed",
            "detail": f"Region HHI={region_hhi:.4f}.",
            "action": "Consider improving regional diversification",
        })

    # Currency concentration
    currency_hhi = concentration.get("currency_hhi", 0)
    currency_breakdown = concentration.get("currency_breakdown", {})
    if currency_hhi > HHI_DANGER and currency_breakdown:
        top_currency = max(currency_breakdown, key=currency_breakdown.get)
        recs.append({
            "priority": "medium",
            "category": "concentration",
            "title": f"Currency concentration: {top_currency}",
            "detail": f"Currency HHI={currency_hhi:.4f}. FX risk is skewed.",
            "action": "Diversify FX risk by adding stocks in different currencies",
        })

    return recs


# ---------------------------------------------------------------------------
# Correlation checks
# ---------------------------------------------------------------------------

def _check_correlations(pairs: list[dict]) -> list[dict]:
    """Generate recommendations from high correlation pairs."""
    recs: list[dict] = []
    for pair_info in pairs:
        pair = pair_info.get("pair", ["?", "?"])
        corr = pair_info.get("correlation", 0)
        if abs(corr) >= CORR_VERY_HIGH:
            recs.append({
                "priority": "high",
                "category": "correlation",
                "title": f"Strong correlation: {pair[0]} x {pair[1]} (r={corr:.2f})",
                "detail": "Both stocks move very closely together, limiting diversification effect.",
                "action": "Consider reducing one position and diversifying into uncorrelated sectors",
            })
        elif abs(corr) >= CORR_HIGH:
            recs.append({
                "priority": "medium",
                "category": "correlation",
                "title": f"High-correlation pair: {pair[0]} x {pair[1]} (r={corr:.2f})",
                "detail": "High price co-movement, risk of simultaneous decline in a shock.",
                "action": "Investigate the cause of correlation and consider risk diversification",
            })
    return recs


# ---------------------------------------------------------------------------
# VaR checks
# ---------------------------------------------------------------------------

def _check_var(var_result: dict) -> list[dict]:
    """Generate recommendations from VaR analysis."""
    recs: list[dict] = []
    monthly_var = var_result.get("monthly_var", {})
    var_95 = monthly_var.get(0.95, 0)

    if var_95 < VAR_SEVERE:
        recs.append({
            "priority": "high",
            "category": "var",
            "title": f"Monthly VaR(95%) is high: {var_95*100:.1f}%",
            "detail": "There is a statistical 5% probability of a loss exceeding 15% in a month.",
            "action": "Consider reducing position size or introducing hedging instruments",
        })
    elif var_95 < VAR_WARNING:
        recs.append({
            "priority": "medium",
            "category": "var",
            "title": f"Monthly VaR(95%): {var_95*100:.1f}%",
            "detail": "There is a statistical 5% probability of a loss exceeding 10% in a month.",
            "action": "Review positions against your risk tolerance",
        })

    portfolio_vol = var_result.get("portfolio_volatility", 0)
    if portfolio_vol > VOLATILITY_HIGH:
        recs.append({
            "priority": "medium",
            "category": "var",
            "title": f"Portfolio volatility: {portfolio_vol*100:.1f}%",
            "detail": "Annual volatility exceeds 30%.",
            "action": "Consider adding low-volatility or defensive stocks",
        })

    return recs


# ---------------------------------------------------------------------------
# Stress test checks
# ---------------------------------------------------------------------------

def _check_stress(scenario_result: dict) -> list[dict]:
    """Generate recommendations from stress test results."""
    recs: list[dict] = []
    judgment = scenario_result.get("judgment", "")
    pf_impact = scenario_result.get("portfolio_impact", 0)

    if judgment == "Action required":
        recs.append({
            "priority": "high",
            "category": "stress",
            "title": f"Stress test action required: PF impact {pf_impact*100:+.1f}%",
            "detail": (
                f"Scenario '{scenario_result.get('scenario_name', 'Unknown')}': "
                f"Portfolio projected to lose more than 30%."
            ),
            "action": "Consider building hedge positions or reducing exposure",
        })

    # Check individual stock impacts
    stock_impacts = scenario_result.get("stock_impacts", [])
    for si in stock_impacts:
        total_impact = si.get("total_impact", 0)
        if total_impact < STRESS_SEVERE_IMPACT:
            sym = si.get("symbol", "?")
            recs.append({
                "priority": "high",
                "category": "stress",
                "title": f"{sym}: scenario impact {total_impact*100:+.1f}%",
                "detail": f"{sym}: stress loss exceeds -30%.",
                "action": (
                    f"Consider reducing {sym} position or "
                    f"hedging with put options"
                ),
            })

    return recs


# ---------------------------------------------------------------------------
# Sensitivity checks
# ---------------------------------------------------------------------------

def _check_sensitivities(sensitivities: list[dict]) -> list[dict]:
    """Generate recommendations from sensitivity analysis."""
    recs: list[dict] = []
    for sens in sensitivities:
        integrated = sens.get("integrated", {})
        quadrant = integrated.get("quadrant", {})
        quad_name = quadrant.get("quadrant", "")
        sym = sens.get("symbol", "?")

        if quad_name == "Highest risk":
            recs.append({
                "priority": "high",
                "category": "sensitivity",
                "title": f"{sym}: Weak fundamentals + technically overbought",
                "detail": quadrant.get("description", ""),
                "action": f"Consider taking profit or reducing {sym}",
            })
        elif quad_name == "Breakdown risk":
            recs.append({
                "priority": "medium",
                "category": "sensitivity",
                "title": f"{sym}: Breakdown risk",
                "detail": quadrant.get("description", ""),
                "action": f"Review {sym} position (set stop-loss level)",
            })
    return recs
