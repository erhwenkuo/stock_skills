"""Portfolio I/O: CSV load/save and position operations (KIK-578 split).

Extracted from portfolio_manager.py. Provides CSV-based portfolio
persistence with position tracking and P&L calculation.
"""

import csv
import os
from datetime import datetime
from typing import Optional

from src.core.ticker_utils import (
    SUFFIX_TO_CURRENCY as _SUFFIX_TO_CURRENCY,
    infer_currency as _infer_currency,
)

# CSV path (default)
DEFAULT_CSV_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "..",
    ".claude",
    "skills",
    "stock-portfolio",
    "data",
    "portfolio.csv",
)

# CSV column definitions
CSV_COLUMNS = [
    "symbol",
    "shares",
    "cost_price",
    "cost_currency",
    "purchase_date",
    "memo",
]


# ---------------------------------------------------------------------------
# CSV I/O
# ---------------------------------------------------------------------------


def load_portfolio(csv_path: str = DEFAULT_CSV_PATH) -> list[dict]:
    """Load portfolio from CSV.

    Returns
    -------
    list[dict]
        Each row as dict: {symbol, shares, cost_price, cost_currency, purchase_date, memo}
        shares is int, cost_price is float.
        Returns empty list if file does not exist.
    """
    csv_path = os.path.normpath(csv_path)
    if not os.path.exists(csv_path):
        return []

    portfolio: list[dict] = []
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            position = {
                "symbol": row.get("symbol", "").strip(),
                "shares": int(float(row.get("shares", 0))),
                "cost_price": float(row.get("cost_price", 0.0)),
                "cost_currency": row.get("cost_currency", "JPY").strip(),
                "purchase_date": row.get("purchase_date", "").strip(),
                "memo": row.get("memo", "").strip(),
            }
            if position["symbol"] and position["shares"] > 0:
                portfolio.append(position)

    return portfolio


def save_portfolio(
    portfolio: list[dict], csv_path: str = DEFAULT_CSV_PATH
) -> None:
    """Save portfolio to CSV.

    Automatically creates the directory if it does not exist.
    """
    csv_path = os.path.normpath(csv_path)
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)

    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for pos in portfolio:
            writer.writerow(
                {
                    "symbol": pos.get("symbol", ""),
                    "shares": pos.get("shares", 0),
                    "cost_price": pos.get("cost_price", 0.0),
                    "cost_currency": pos.get("cost_currency", "JPY"),
                    "purchase_date": pos.get("purchase_date", ""),
                    "memo": pos.get("memo", ""),
                }
            )


# ---------------------------------------------------------------------------
# Position operations
# ---------------------------------------------------------------------------


def add_position(
    csv_path: str,
    symbol: str,
    shares: int,
    cost_price: float,
    cost_currency: str = "JPY",
    purchase_date: Optional[str] = None,
    memo: str = "",
) -> dict:
    """Add a new position or additional purchase to an existing position.

    For existing holdings:
    - Adds share count
    - Recalculates average cost: new_avg = (old_shares * old_price + new_shares * new_price) / total_shares
    - Updates purchase_date to the latest date

    Returns
    -------
    dict
        Updated position dict
    """
    if purchase_date is None:
        purchase_date = datetime.now().strftime("%Y-%m-%d")

    portfolio = load_portfolio(csv_path)

    # Search for existing position with same symbol
    existing = None
    for pos in portfolio:
        if pos["symbol"].upper() == symbol.upper():
            existing = pos
            break

    if existing is not None:
        # Additional purchase → recalculate average cost
        old_shares = existing["shares"]
        old_price = existing["cost_price"]
        total_shares = old_shares + shares
        if total_shares > 0:
            new_avg = (old_shares * old_price + shares * cost_price) / total_shares
        else:
            new_avg = cost_price

        existing["shares"] = total_shares
        existing["cost_price"] = round(new_avg, 4)
        existing["purchase_date"] = purchase_date
        if memo:
            existing["memo"] = memo
        result = dict(existing)
    else:
        # New position
        new_pos = {
            "symbol": symbol.upper() if "." not in symbol else symbol,
            "shares": shares,
            "cost_price": cost_price,
            "cost_currency": cost_currency,
            "purchase_date": purchase_date,
            "memo": memo,
        }
        portfolio.append(new_pos)
        result = dict(new_pos)

    save_portfolio(portfolio, csv_path)
    return result


def sell_position(
    csv_path: str,
    symbol: str,
    shares: int,
    sell_price: Optional[float] = None,
    sell_date: Optional[str] = None,
) -> dict:
    """Sell shares. Subtracts from holdings; removes row when shares reach 0.

    Parameters
    ----------
    sell_price : float, optional
        Sell price per share. When specified, computes realized_pnl / pnl_rate.
    sell_date : str, optional
        Sale date (YYYY-MM-DD). When specified, computes hold_days.

    Returns
    -------
    dict
        Updated position dict (shares=0 if fully sold).
        KIK-441: adds sold_shares / sell_price / realized_pnl / pnl_rate / hold_days.

    Raises
    ------
    ValueError
        If the symbol is not found, or if shares exceed holdings.
    """
    portfolio = load_portfolio(csv_path)

    target_idx = None
    for i, pos in enumerate(portfolio):
        if pos["symbol"].upper() == symbol.upper():
            target_idx = i
            break

    if target_idx is None:
        raise ValueError(f"Symbol {symbol} not found in portfolio.")

    target = portfolio[target_idx]

    if shares > target["shares"]:
        raise ValueError(
            f"Sell quantity ({shares}) exceeds holdings "
            f"({target['shares']}) for {symbol}."
        )

    remaining = target["shares"] - shares

    if remaining <= 0:
        # Full position sell → remove row
        result = dict(target)
        result["shares"] = 0
        portfolio.pop(target_idx)
    else:
        target["shares"] = remaining
        result = dict(target)

    save_portfolio(portfolio, csv_path)

    # KIK-441: Add P&L fields
    result["sold_shares"] = shares
    result["sell_price"] = sell_price

    cost_price = target.get("cost_price")
    if sell_price is not None and cost_price is not None and cost_price != 0:
        result["realized_pnl"] = (sell_price - cost_price) * shares
        result["pnl_rate"] = (sell_price - cost_price) / cost_price
    else:
        result["realized_pnl"] = None
        result["pnl_rate"] = None

    purchase_date = target.get("purchase_date", "")
    if sell_date and purchase_date:
        try:
            from datetime import date as _date
            d1 = _date.fromisoformat(purchase_date)
            d2 = _date.fromisoformat(sell_date)
            result["hold_days"] = (d2 - d1).days
        except (ValueError, TypeError):
            result["hold_days"] = None
    else:
        result["hold_days"] = None

    return result


def get_performance_review(
    year: Optional[int] = None,
    symbol: Optional[str] = None,
    base_dir: str = "data/history",
) -> dict:
    """Trade performance review aggregation (KIK-441).

    Aggregates sell records with realized_pnl from data/history/trade/*.json.

    Parameters
    ----------
    year : int, optional
        Filter by year (e.g. 2026). None = all periods.
    symbol : str, optional
        Filter by symbol. None = all symbols.
    base_dir : str
        History root directory.

    Returns
    -------
    dict
        {
            "trades": [...],  # Filtered sell records
            "stats": {
                "total": int,
                "wins": int,
                "win_rate": float | None,
                "avg_return": float | None,   # Average pnl_rate
                "avg_hold_days": float | None,
                "total_pnl": float | None,
            }
        }
    """
    from src.data.history import load_history

    all_trades = load_history("trade", base_dir=base_dir)

    # Filter to sell records with realized_pnl
    sells = [
        t for t in all_trades
        if t.get("trade_type") == "sell" and t.get("realized_pnl") is not None
    ]

    # Year filter
    if year is not None:
        sells = [t for t in sells if str(t.get("date", "")).startswith(str(year))]

    # Symbol filter
    if symbol is not None:
        sym_upper = symbol.upper()
        sells = [t for t in sells if t.get("symbol", "").upper() == sym_upper]

    # Statistics calculation
    total = len(sells)
    if total == 0:
        return {
            "trades": [],
            "stats": {
                "total": 0,
                "wins": 0,
                "win_rate": None,
                "avg_return": None,
                "avg_hold_days": None,
                "total_pnl": None,
            },
        }

    wins = sum(1 for t in sells if (t.get("realized_pnl") or 0) > 0)
    win_rate = wins / total

    pnl_rates_stored = [t["pnl_rate"] for t in sells if t.get("pnl_rate") is not None]
    avg_return = sum(pnl_rates_stored) / len(pnl_rates_stored) if pnl_rates_stored else None

    hold_days_list = [t["hold_days"] for t in sells if t.get("hold_days") is not None]
    avg_hold_days = sum(hold_days_list) / len(hold_days_list) if hold_days_list else None

    total_pnl = sum(t.get("realized_pnl", 0) or 0 for t in sells)

    return {
        "trades": sells,
        "stats": {
            "total": total,
            "wins": wins,
            "win_rate": win_rate,
            "avg_return": avg_return,
            "avg_hold_days": avg_hold_days,
            "total_pnl": total_pnl,
        },
    }
