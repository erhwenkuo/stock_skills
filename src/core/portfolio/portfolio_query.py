"""Portfolio query: snapshot, structure analysis, and merge (KIK-578 split).

Extracted from portfolio_manager.py. Provides real-time pricing,
P&L calculation, structural analysis, and what-if merge operations.
"""

import copy
from datetime import datetime

from src.core.common import is_cash as _is_cash
from src.core.portfolio.fx_utils import (  # KIK-511
    get_fx_rates,
    get_rate as _get_fx_rate_for_currency,
)
from src.core.portfolio.portfolio_io import load_portfolio
from src.core.ticker_utils import (
    SUFFIX_TO_REGION as _SUFFIX_TO_COUNTRY,
    cash_currency as _cash_currency,
    infer_country as _infer_country,
    infer_currency as _infer_currency,
)


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


def get_snapshot(csv_path: str, client) -> dict:
    """Generate portfolio snapshot.

    For each symbol:
    - Fetches current price, sector, etc. via yahoo_client.get_stock_info()
    - Calculates P&L: (current_price - cost_price) * shares
    - Calculates P&L rate: (current_price - cost_price) / cost_price
    - Calculates market value: current_price * shares

    FX rate retrieval:
    - Fetches USDJPY=X, SGDJPY=X, etc. via yfinance
    - Converts all positions to JPY

    Parameters
    ----------
    csv_path : str
        Path to portfolio CSV
    client
        yahoo_client module (must have get_stock_info)

    Returns
    -------
    dict
        {
            "positions": list[dict],
            "total_value_jpy": float,
            "total_cost_jpy": float,
            "total_pnl_jpy": float,
            "total_pnl_pct": float,
            "fx_rates": dict,
            "as_of": str,
        }
    """
    portfolio = load_portfolio(csv_path)

    if not portfolio:
        return {
            "positions": [],
            "total_value_jpy": 0.0,
            "total_cost_jpy": 0.0,
            "total_pnl_jpy": 0.0,
            "total_pnl_pct": 0.0,
            "fx_rates": {"JPY": 1.0},
            "as_of": datetime.now().isoformat(),
        }

    # Collect unique currencies for FX rate fetching
    currencies_needed: set[str] = set()
    for pos in portfolio:
        currencies_needed.add(pos.get("cost_currency", "JPY"))
        # Also need the market currency (inferred from symbol)
        currencies_needed.add(_infer_currency(pos["symbol"]))

    # Fetch FX rates (only if non-JPY currencies exist)
    if currencies_needed - {"JPY"}:
        fx_rates = get_fx_rates(client)
    else:
        fx_rates = {"JPY": 1.0}

    # Fetch current prices and build position details
    positions: list[dict] = []
    total_value_jpy = 0.0
    total_cost_jpy = 0.0

    for pos in portfolio:
        symbol = pos["symbol"]
        shares = pos["shares"]
        cost_price = pos["cost_price"]
        cost_currency = pos.get("cost_currency", "JPY")

        # Cash positions: skip API call, use cost_price as current price
        if _is_cash(symbol):
            cash_currency = _cash_currency(symbol)
            fx_rate = _get_fx_rate_for_currency(cash_currency, fx_rates)
            value_jpy = cost_price * shares * fx_rate
            cost_jpy = value_jpy  # cash has no P&L
            total_value_jpy += value_jpy
            total_cost_jpy += cost_jpy
            positions.append({
                "symbol": symbol,
                "name": f"Cash ({cash_currency})",
                "sector": "Cash",
                "shares": shares,
                "cost_price": cost_price,
                "cost_currency": cost_currency,
                "current_price": cost_price,
                "market_currency": cash_currency,
                "evaluation": cost_price * shares,
                "evaluation_jpy": round(value_jpy, 0),
                "cost_jpy": round(cost_jpy, 0),
                "pnl": 0.0,
                "pnl_pct": 0.0,
                "pnl_jpy": 0.0,
                "purchase_date": pos.get("purchase_date", ""),
                "memo": pos.get("memo", ""),
            })
            continue

        # Get current market data
        info = client.get_stock_info(symbol)
        current_price = None
        name = None
        sector = None
        market_currency = _infer_currency(symbol)

        market_cap = None
        if info is not None:
            current_price = info.get("price")
            name = info.get("name")
            sector = info.get("sector")
            market_cap = info.get("market_cap")
            # Use the currency from yfinance if available
            if info.get("currency"):
                market_currency = info["currency"]

        # P&L calculation (in market currency)
        if current_price is not None:
            pnl = (current_price - cost_price) * shares
            pnl_pct = (current_price - cost_price) / cost_price if cost_price != 0 else 0.0
            evaluation = current_price * shares
        else:
            pnl = 0.0
            pnl_pct = 0.0
            evaluation = 0.0

        # JPY conversion
        fx_rate = _get_fx_rate_for_currency(market_currency, fx_rates)
        evaluation_jpy = evaluation * fx_rate
        cost_jpy = cost_price * shares * _get_fx_rate_for_currency(
            cost_currency, fx_rates
        )
        pnl_jpy = evaluation_jpy - cost_jpy

        total_value_jpy += evaluation_jpy
        total_cost_jpy += cost_jpy

        position_detail = {
            "symbol": symbol,
            "name": name,
            "sector": sector,
            "shares": shares,
            "cost_price": cost_price,
            "cost_currency": cost_currency,
            "current_price": current_price,
            "market_currency": market_currency,
            "market_cap": market_cap,
            "evaluation": evaluation,
            "evaluation_jpy": round(evaluation_jpy, 0),
            "cost_jpy": round(cost_jpy, 0),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 4),
            "pnl_jpy": round(pnl_jpy, 0),
            "purchase_date": pos.get("purchase_date", ""),
            "memo": pos.get("memo", ""),
            "quoteType": info.get("quoteType") if info else None,  # KIK-469 P2
        }
        positions.append(position_detail)

    total_pnl_jpy = total_value_jpy - total_cost_jpy
    total_pnl_pct = (
        total_pnl_jpy / total_cost_jpy if total_cost_jpy != 0 else 0.0
    )

    return {
        "positions": positions,
        "total_value_jpy": round(total_value_jpy, 0),
        "total_cost_jpy": round(total_cost_jpy, 0),
        "total_pnl_jpy": round(total_pnl_jpy, 0),
        "total_pnl_pct": round(total_pnl_pct, 4),
        "fx_rates": fx_rates,
        "as_of": datetime.now().isoformat(),
    }


# ---------------------------------------------------------------------------
# Structure analysis
# ---------------------------------------------------------------------------


def get_structure_analysis(csv_path: str, client) -> dict:
    """Structure analysis. Automatically aggregates portfolio bias.

    Fetches sector, region, and currency for each symbol via yfinance,
    then computes HHI based on evaluation_jpy weights.

    Uses analyze_concentration() from concentration.py.

    Parameters
    ----------
    csv_path : str
        Path to portfolio CSV
    client
        yahoo_client module (must have get_stock_info)

    Returns
    -------
    dict
        {
            "region_breakdown": dict,
            "sector_breakdown": dict,
            "currency_breakdown": dict,
            "region_hhi": float,
            "sector_hhi": float,
            "currency_hhi": float,
            "concentration_multiplier": float,
            "risk_level": str,
        }
    """
    from src.core.portfolio.concentration import analyze_concentration
    from src.core.portfolio.small_cap import classify_market_cap
    from src.core.ticker_utils import infer_region_code

    # Get snapshot first (this also fetches current prices and FX rates)
    snapshot = get_snapshot(csv_path, client)
    positions = snapshot["positions"]

    if not positions:
        return {
            "region_breakdown": {},
            "sector_breakdown": {},
            "currency_breakdown": {},
            "size_breakdown": {},
            "region_hhi": 0.0,
            "sector_hhi": 0.0,
            "currency_hhi": 0.0,
            "size_hhi": 0.0,
            "concentration_multiplier": 1.0,
            "risk_level": "Diversified",
        }

    # Calculate weights based on evaluation_jpy
    total_value = snapshot["total_value_jpy"]
    if total_value <= 0:
        # Fallback: equal weights
        n = len(positions)
        weights = [1.0 / n] * n
    else:
        weights = [
            pos["evaluation_jpy"] / total_value for pos in positions
        ]

    # Build portfolio_data for analyze_concentration
    portfolio_data: list[dict] = []
    for pos in positions:
        region_code = infer_region_code(pos["symbol"])
        # KIK-469 Phase 2: ETF sector classification
        is_etf_pos = pos.get("quoteType") == "ETF"
        sector = pos.get("sector") or ("ETF" if is_etf_pos else "Unknown")
        stock_data = {
            "symbol": pos["symbol"],
            "sector": sector,
            "country": _infer_country(pos["symbol"]),
            "currency": pos.get("market_currency") or _infer_currency(pos["symbol"]),
            "size_class": "ETF" if is_etf_pos else classify_market_cap(pos.get("market_cap"), region_code),
            "is_etf": is_etf_pos,
        }
        portfolio_data.append(stock_data)

    # Run concentration analysis
    conc = analyze_concentration(portfolio_data, weights)

    return {
        "region_breakdown": conc.get("region_breakdown", {}),
        "sector_breakdown": conc.get("sector_breakdown", {}),
        "currency_breakdown": conc.get("currency_breakdown", {}),
        "size_breakdown": conc.get("size_breakdown", {}),
        "region_hhi": conc.get("region_hhi", 0.0),
        "sector_hhi": conc.get("sector_hhi", 0.0),
        "currency_hhi": conc.get("currency_hhi", 0.0),
        "size_hhi": conc.get("size_hhi", 0.0),
        "concentration_multiplier": conc.get("concentration_multiplier", 1.0),
        "risk_level": conc.get("risk_level", "Diversified"),
    }


# ---------------------------------------------------------------------------
# Portfolio shareholder return (KIK-375)
# ---------------------------------------------------------------------------


def get_portfolio_shareholder_return(csv_path: str, client) -> dict:
    """Calculate weighted-average shareholder return for the portfolio.

    Parameters
    ----------
    csv_path : str
        Path to portfolio CSV.
    client
        yahoo_client module (must expose ``get_stock_detail``).

    Returns
    -------
    dict
        Keys: positions (list of {symbol, rate, market_value}),
        weighted_avg_rate (float or None).
    """
    from src.core.screening.indicators import calculate_shareholder_return

    holdings = load_portfolio(csv_path)
    if not holdings:
        return {"positions": [], "weighted_avg_rate": None}

    total_mv = 0.0
    weighted_rate = 0.0
    position_returns: list[dict] = []

    for h in holdings:
        symbol = h["symbol"]
        if _is_cash(symbol):
            continue
        detail = client.get_stock_detail(symbol)
        if detail is None:
            continue
        sr = calculate_shareholder_return(detail)
        rate = sr.get("total_return_rate")
        price = detail.get("price") or 0
        mv = price * h["shares"]
        if rate is not None and mv > 0:
            position_returns.append({
                "symbol": symbol,
                "rate": rate,
                "market_value": mv,
            })
            weighted_rate += rate * mv
            total_mv += mv

    avg_rate = weighted_rate / total_mv if total_mv > 0 else None
    return {
        "positions": sorted(position_returns, key=lambda x: -x["rate"]),
        "weighted_avg_rate": avg_rate,
    }


# ---------------------------------------------------------------------------
# Merge positions (KIK-376: What-If simulation)
# ---------------------------------------------------------------------------


def merge_positions(
    current: list[dict], proposed: list[dict]
) -> list[dict]:
    """Merge proposed stocks into current portfolio (weighted average cost).

    Does not modify input lists (deep copy).

    Parameters
    ----------
    current : list[dict]
        Current portfolio (return value of load_portfolio).
    proposed : list[dict]
        Proposed additions. Each dict must have symbol, shares, cost_price,
        cost_currency.

    Returns
    -------
    list[dict]
        Merged portfolio.
    """
    merged = copy.deepcopy(current)
    symbol_map: dict[str, int] = {
        p["symbol"].upper(): i for i, p in enumerate(merged)
    }

    for prop in proposed:
        key = prop["symbol"].upper()
        if key in symbol_map:
            old = merged[symbol_map[key]]
            total = old["shares"] + prop["shares"]
            if total > 0:
                old["cost_price"] = (
                    old["shares"] * old["cost_price"]
                    + prop["shares"] * prop["cost_price"]
                ) / total
            old["shares"] = total
        else:
            merged.append({
                "symbol": prop["symbol"],
                "shares": prop["shares"],
                "cost_price": prop["cost_price"],
                "cost_currency": prop.get("cost_currency", "JPY"),
                "purchase_date": "",
                "memo": "(what-if)",
            })
            symbol_map[key] = len(merged) - 1

    return merged
