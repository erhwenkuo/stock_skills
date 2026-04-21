"""Scenario-based causal chain analysis for portfolio stress testing (KIK-341)."""

from typing import Optional

from src.core.common import safe_float as _safe_float
from src.core.risk.scenario_definitions import (
    SCENARIOS,
    SCENARIO_ALIASES,
    TARGET_TO_SECTORS,
    SUFFIX_TO_REGION,
    ETF_ASSET_CLASS,
)
from src.core.ticker_utils import infer_currency as _infer_currency


def _get_etf_asset_class(symbol: str, stock_info: dict) -> Optional[str]:
    """Return the ETF asset class if the symbol is a known ETF, else None."""
    # Strip suffix for lookup (e.g., "1326.T" -> not in mapping, just use symbol)
    base_symbol = symbol.split(".")[0] if "." in symbol else symbol
    asset_class = ETF_ASSET_CLASS.get(base_symbol)
    if asset_class:
        return asset_class
    # quoteType fallback
    if stock_info.get("quoteType") == "ETF":
        return "Equity income"  # Default ETF class (conservative equity)
    return None


def _infer_region(symbol: str, stock_info: dict) -> str:
    """Infer the region of a stock."""
    country = stock_info.get("country") or stock_info.get("region")
    if country:
        return country
    for suffix, region in SUFFIX_TO_REGION.items():
        if symbol.endswith(suffix):
            return region
    return "US"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve_scenario(name: str) -> Optional[dict]:
    """Resolve a scenario name (including natural language) to a scenario definition.

    Search order: exact match (SCENARIOS key) -> exact match (alias) -> partial match (alias)
    """
    key = name.lower().strip()

    # 1. Exact match on SCENARIOS key
    if key in SCENARIOS:
        return SCENARIOS[key]

    # 2. Exact match on alias
    alias_key = SCENARIO_ALIASES.get(key) or SCENARIO_ALIASES.get(name)
    if alias_key and alias_key in SCENARIOS:
        return SCENARIOS[alias_key]

    # 3. Partial match on alias (input contains alias or alias contains input)
    if len(key) >= 2:
        for alias, scenario_key in SCENARIO_ALIASES.items():
            if alias in key or key in alias:
                if scenario_key in SCENARIOS:
                    return SCENARIOS[scenario_key]

    return None


def _match_target(
    target: str,
    sector: Optional[str],
    currency: str,
    region: str,
    etf_asset_class: Optional[str] = None,
) -> bool:
    """Return True if the scenario target matches the stock's attributes."""
    # Currency-based matching (applies to all stocks including ETFs)
    if target in ("JPY-denominated", "JPY-denominated foreign assets") and currency == "JPY":
        return True
    if target == "All foreign assets" and currency != "JPY":
        return True

    # ETF asset class matching (KIK-358)
    # Non-equity ETFs (gold/bonds) match only their own asset class
    # Evaluated before region matching to prevent false matches like "US stocks"
    if etf_asset_class:
        if etf_asset_class in ("Gold/safe assets", "Long-term bonds"):
            return target == etf_asset_class
        if target == etf_asset_class:
            return True
        # Equity income ETFs also react as cyclical stocks
        if etf_asset_class == "Equity income" and target == "Cyclical stocks":
            return True
        # Equity income ETFs also fall through to region matching

    # Region-based matching
    if target == "Japan stocks" and region == "Japan":
        return True
    if target == "US stocks" and region == "US":
        return True
    if target == "US stocks (JPY)" and region == "US":
        return True
    if target == "ASEAN stocks" and region in ("Singapore", "Thailand", "Malaysia", "Indonesia", "Philippines"):
        return True
    if target == "China-related stocks" and region in ("China", "Hong Kong"):
        return True
    if target in ("Japan export stocks", "Export companies") and region == "Japan":
        sector_list = TARGET_TO_SECTORS.get(target)
        if sector_list is None:
            return True
        return sector in sector_list if sector else False
    if target in ("Japan domestic stocks", "Domestic companies") and region == "Japan":
        sector_list = TARGET_TO_SECTORS.get(target)
        if sector_list is None:
            return True
        return sector in sector_list if sector else False

    # Non-tech stocks: all sectors except Technology and Communication Services
    if target == "Non-tech stocks":
        return sector not in ("Technology", "Communication Services") if sector else True

    # Sector-based matching
    sector_list = TARGET_TO_SECTORS.get(target)
    if sector_list is not None and sector in (sector_list or []):
        return True

    # High dividend stocks: judged by dividend_yield, return False here
    # (caller should check dividend_yield separately if needed)
    return False


def compute_stock_scenario_impact(
    stock_info: dict,
    sensitivity: dict,
    scenario: dict,
) -> dict:
    """Compute scenario impact for a single stock.

    Parameters
    ----------
    stock_info : dict
        Stock fundamental data (sector, country, currency, etc.)
    sensitivity : dict
        Result of shock_sensitivity.analyze_stock_sensitivity().
        An empty dict is also acceptable. Available keys:
        - "composite_shock": float (composite shock impact rate)
        - "fundamental_score": float
        - "technical_score": float
    scenario : dict
        One entry from SCENARIOS

    Returns
    -------
    dict
        {
            "symbol": str,
            "direct_impact": float,      # direct impact rate
            "currency_impact": float,    # currency effect rate
            "total_impact": float,       # total impact rate
            "price_impact": float,       # price change amount
            "causal_chain": list[str],   # causal chain descriptions
        }
    """
    symbol = stock_info.get("symbol", "")
    sector = stock_info.get("sector")
    currency = _infer_currency(symbol, stock_info)
    region = _infer_region(symbol, stock_info)
    price = _safe_float(stock_info.get("price"))
    beta = _safe_float(stock_info.get("beta"), default=1.0)
    etf_asset_class = _get_etf_asset_class(symbol, stock_info)

    effects = scenario.get("effects", {})
    base_shock = _safe_float(scenario.get("base_shock"))
    causal_chain: list[str] = []

    # 1. Adjust base_shock by beta (fallback)
    beta_impact = base_shock * beta
    causal_chain.append(
        f"Base shock {base_shock:+.1%} x beta({beta:.2f}) = {beta_impact:+.1%}"
    )

    # 2. Match primary/secondary effects
    matched_impacts: list[float] = []
    for effect_group in ("primary", "secondary"):
        for effect in effects.get(effect_group, []):
            target = effect.get("target", "")
            impact = _safe_float(effect.get("impact"))
            reason = effect.get("reason", "")
            if _match_target(target, sector, currency, region, etf_asset_class):
                matched_impacts.append(impact)
                sign = "+" if impact >= 0 else ""
                causal_chain.append(
                    f"[{effect_group}] {target}: {sign}{impact:.1%} ({reason})"
                )

    # When matched impacts exist, use their average adjusted by beta.
    # Sector impact already incorporates base_shock, so replace rather than add.
    # Beta adjustment is dampened: multiplier = 0.7 + 0.3 * beta
    #   beta=1.0 -> 1.0 (neutral), beta=0.5 -> 0.85, beta=2.0 -> 1.30
    if matched_impacts:
        avg_matched = sum(matched_impacts) / len(matched_impacts)
        beta_multiplier = 0.7 + 0.3 * beta
        direct_impact = avg_matched * beta_multiplier
        causal_chain.append(
            f"Sector impact avg: {avg_matched:+.1%} x beta adj({beta_multiplier:.2f})"
            f" = {direct_impact:+.1%}"
        )
    else:
        direct_impact = beta_impact
        causal_chain.append("No matching sector impact -> using base shock x beta")

    # 3. Adjust by sensitivity (if available)
    composite_shock = _safe_float(sensitivity.get("composite_shock"))
    if composite_shock != 0.0:
        # Fine-tune impact using sensitivity score (max +/- 20%)
        adjustment = composite_shock * 0.2
        direct_impact *= (1.0 + adjustment)
        causal_chain.append(
            f"Sensitivity adj: composite_shock={composite_shock:+.2f} -> impact x{1.0 + adjustment:.2f}"
        )

    # 4. Currency effect
    currency_data = effects.get("currency", {})
    currency_impact = 0.0
    if currency != "JPY":
        # FX impact on foreign-currency assets
        impact_on_foreign = _safe_float(currency_data.get("impact_on_foreign"))
        currency_impact = impact_on_foreign
        usd_jpy_change = _safe_float(currency_data.get("usd_jpy_change"))
        if currency_impact != 0.0:
            causal_chain.append(
                f"Currency effect: USD/JPY {usd_jpy_change:+.0f} yen -> foreign assets {currency_impact:+.1%}"
            )
    elif currency == "JPY":
        # JPY assets: yen weakness negative impact already reflected in primary/secondary
        pass

    # 5. Total
    total_impact = direct_impact + currency_impact
    price_impact = price * total_impact

    causal_chain.append(
        f"Total impact: direct {direct_impact:+.1%} + currency {currency_impact:+.1%} = {total_impact:+.1%}"
    )

    return {
        "symbol": symbol,
        "name": stock_info.get("name", ""),
        "direct_impact": round(direct_impact, 4),
        "currency_impact": round(currency_impact, 4),
        "total_impact": round(total_impact, 4),
        "price_impact": round(price_impact, 2),
        "causal_chain": causal_chain,
    }


def analyze_portfolio_scenario(
    portfolio: list[dict],
    sensitivities: list[dict],
    weights: list[float],
    scenario: dict,
) -> dict:
    """Run scenario analysis for the entire portfolio.

    Parameters
    ----------
    portfolio : list[dict]
        List of stock_info dicts for each holding
    sensitivities : list[dict]
        List of sensitivity dicts for each holding (empty dicts are acceptable)
    weights : list[float]
        Portfolio weight for each holding (should sum to ~1.0)
    scenario : dict
        One entry from SCENARIOS

    Returns
    -------
    dict
        {
            "scenario_name": str,
            "trigger": str,
            "portfolio_impact": float,      # portfolio-wide impact rate
            "portfolio_value_change": float, # portfolio-wide value change
            "stock_impacts": list[dict],     # per-stock impacts
            "causal_chain_summary": str,     # full causal chain summary
            "offset_factors": list[str],     # offsetting factors
            "time_axis": str,                # time horizon
            "judgment": str,                 # "Monitor" / "Caution" / "Action required"
        }
    """
    # Validate input consistency
    n = len(portfolio)
    if len(sensitivities) < n:
        sensitivities = sensitivities + [{}] * (n - len(sensitivities))
    if len(weights) < n:
        # Fill missing weights with equal distribution
        remaining = max(0.0, 1.0 - sum(weights))
        missing_count = n - len(weights)
        if missing_count > 0:
            weights = list(weights) + [remaining / missing_count] * missing_count

    # Compute scenario impact for each stock
    stock_impacts: list[dict] = []
    portfolio_impact = 0.0
    portfolio_value_change = 0.0

    for i, (stock, sens, weight) in enumerate(zip(portfolio, sensitivities, weights)):
        impact = compute_stock_scenario_impact(stock, sens, scenario)
        impact["weight"] = round(weight, 4)
        impact["pf_contribution"] = round(impact["total_impact"] * weight, 4)
        stock_impacts.append(impact)

        portfolio_impact += impact["total_impact"] * weight
        portfolio_value_change += impact["price_impact"] * weight

    # Build causal chain summary
    effects = scenario.get("effects", {})
    chain_lines: list[str] = []
    chain_lines.append(f"Trigger: {scenario.get('trigger', 'Unknown')}")
    chain_lines.append(f"  ↓")
    chain_lines.append(f"Base shock: {_safe_float(scenario.get('base_shock')):+.1%}")
    chain_lines.append(f"  ↓")

    # Primary effects
    for effect in effects.get("primary", []):
        target = effect.get("target", "")
        impact = _safe_float(effect.get("impact"))
        reason = effect.get("reason", "")
        chain_lines.append(f"[Primary] {target} {impact:+.1%} ({reason})")

    if effects.get("secondary"):
        chain_lines.append(f"  ↓")
        for effect in effects.get("secondary", []):
            target = effect.get("target", "")
            impact = _safe_float(effect.get("impact"))
            reason = effect.get("reason", "")
            chain_lines.append(f"[Secondary] {target} {impact:+.1%} ({reason})")

    currency_data = effects.get("currency", {})
    if currency_data:
        usd_jpy = _safe_float(currency_data.get("usd_jpy_change"))
        fx_impact = _safe_float(currency_data.get("impact_on_foreign"))
        chain_lines.append(f"  ↓")
        chain_lines.append(f"[FX] USD/JPY {usd_jpy:+.0f} yen -> foreign assets {fx_impact:+.1%}")

    chain_lines.append(f"  ↓")
    chain_lines.append(f"Portfolio total impact: {portfolio_impact:+.1%}")

    causal_chain_summary = "\n".join(chain_lines)

    # Offsetting factors
    offset_factors = effects.get("offset", [])

    # Time horizon
    time_axis = effects.get("time_axis", "Unknown")

    # Judgment
    if portfolio_impact <= -0.30:
        judgment = "Action required"
    elif portfolio_impact <= -0.15:
        judgment = "Caution"
    else:
        judgment = "Monitor"

    return {
        "scenario_name": scenario.get("name", "Unknown"),
        "trigger": scenario.get("trigger", "Unknown"),
        "portfolio_impact": round(portfolio_impact, 4),
        "portfolio_value_change": round(portfolio_value_change, 2),
        "stock_impacts": stock_impacts,
        "causal_chain_summary": causal_chain_summary,
        "offset_factors": offset_factors,
        "time_axis": time_axis,
        "judgment": judgment,
    }
