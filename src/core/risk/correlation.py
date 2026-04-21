"""Correlation analysis and VaR computation for portfolio stress testing (KIK-352).

Provides:
  - Pairwise correlation matrix from price histories
  - Factor regression against macro variables
  - Historical VaR calculation
"""

import math
from typing import Optional

import numpy as np

from src.core.common import safe_float as _safe_float


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_daily_returns(prices: list[float]) -> list[float]:
    """Compute daily returns from a list of closing prices."""
    if len(prices) < 2:
        return []
    returns = []
    for i in range(1, len(prices)):
        if prices[i - 1] != 0:
            returns.append((prices[i] - prices[i - 1]) / prices[i - 1])
    return returns


# ---------------------------------------------------------------------------
# Correlation Matrix
# ---------------------------------------------------------------------------

def compute_correlation_matrix(portfolio_data: list[dict]) -> dict:
    """Compute pairwise Pearson correlation matrix from price histories.

    Parameters
    ----------
    portfolio_data : list[dict]
        Each dict must have "symbol" and "price_history" (list of close prices).

    Returns
    -------
    dict
        {
            "symbols": list[str],
            "matrix": list[list[float]],  # NxN correlation matrix
        }
    """
    symbols = [s.get("symbol", "?") for s in portfolio_data]
    n = len(symbols)

    # Compute daily returns for each stock
    returns_map: dict[str, list[float]] = {}
    for stock in portfolio_data:
        sym = stock.get("symbol", "?")
        prices = stock.get("price_history", [])
        returns_map[sym] = _compute_daily_returns(prices)

    # Build correlation matrix
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        matrix[i][i] = 1.0
        for j in range(i + 1, n):
            r_i = returns_map.get(symbols[i], [])
            r_j = returns_map.get(symbols[j], [])

            min_len = min(len(r_i), len(r_j))
            if min_len >= 30:
                arr_i = np.array(r_i[-min_len:])
                arr_j = np.array(r_j[-min_len:])
                if np.std(arr_i) == 0 or np.std(arr_j) == 0:
                    corr = 0.0
                else:
                    corr_matrix = np.corrcoef(arr_i, arr_j)
                    corr = float(corr_matrix[0, 1])
                    if math.isnan(corr):
                        corr = 0.0
            else:
                corr = float("nan")

            matrix[i][j] = round(corr, 4)
            matrix[j][i] = round(corr, 4)

    return {
        "symbols": symbols,
        "matrix": matrix,
    }


def find_high_correlation_pairs(
    corr_result: dict,
    threshold: float = 0.7,
) -> list[dict]:
    """Extract symbol pairs with absolute correlation above threshold.

    Parameters
    ----------
    corr_result : dict
        Output of compute_correlation_matrix().
    threshold : float
        Minimum absolute correlation to include (default 0.7).

    Returns
    -------
    list[dict]
        Each dict: {"pair": [sym_a, sym_b], "correlation": float, "label": str}
        Sorted by descending absolute correlation.
    """
    symbols = corr_result.get("symbols", [])
    matrix = corr_result.get("matrix", [])
    n = len(symbols)
    pairs = []

    for i in range(n):
        for j in range(i + 1, n):
            r = matrix[i][j]
            if math.isnan(r):
                continue
            if abs(r) >= threshold:
                if r >= 0.85:
                    label = "Very strong positive correlation"
                elif r >= 0.7:
                    label = "Strong positive correlation"
                elif r <= -0.7:
                    label = "Strong inverse correlation"
                else:
                    label = "Inverse correlation"
                pairs.append({
                    "pair": [symbols[i], symbols[j]],
                    "correlation": round(r, 4),
                    "label": label,
                })

    pairs.sort(key=lambda x: -abs(x["correlation"]))
    return pairs


# ---------------------------------------------------------------------------
# Factor Regression
# ---------------------------------------------------------------------------

MACRO_FACTORS = [
    {"symbol": "USDJPY=X", "name": "USD/JPY"},
    {"symbol": "^N225", "name": "Nikkei 225"},
    {"symbol": "^GSPC", "name": "S&P500"},
    {"symbol": "CL=F", "name": "Crude Oil"},
    {"symbol": "^TNX", "name": "US 10Y Yield"},
]


def decompose_factors(
    portfolio_data: list[dict],
    factor_histories: dict[str, list[float]],
) -> list[dict]:
    """Run factor regression for each portfolio stock.

    For each stock, regresses daily returns on macro factor returns using OLS.

    Parameters
    ----------
    portfolio_data : list[dict]
        Each dict must have "symbol" and "price_history".
    factor_histories : dict[str, list[float]]
        {factor_symbol: [close_prices]} for macro factors.

    Returns
    -------
    list[dict]
        Per-stock results:
        {
            "symbol": str,
            "factors": [{"name": str, "symbol": str, "beta": float, "contribution": float}],
            "r_squared": float,
            "residual_std": float,
        }
    """
    # Compute factor returns
    factor_returns: dict[str, list[float]] = {}
    for fsym, prices in factor_histories.items():
        factor_returns[fsym] = _compute_daily_returns(prices)

    results = []
    for stock in portfolio_data:
        sym = stock.get("symbol", "?")
        prices = stock.get("price_history", [])
        stock_returns = _compute_daily_returns(prices)

        if len(stock_returns) < 30:
            results.append(_empty_factor_result(sym))
            continue

        # Collect available factor series
        available_factors = []
        available_factor_returns = []
        for factor in MACRO_FACTORS:
            fsym_key = factor["symbol"]
            if fsym_key in factor_returns and len(factor_returns[fsym_key]) >= 30:
                available_factors.append(factor)
                available_factor_returns.append(factor_returns[fsym_key])

        if not available_factors:
            results.append(_empty_factor_result(sym))
            continue

        # Align to shortest series
        all_series = [stock_returns] + available_factor_returns
        min_len = min(len(s) for s in all_series)
        if min_len < 30:
            results.append(_empty_factor_result(sym))
            continue

        y = np.array(stock_returns[-min_len:])
        X = np.column_stack(
            [np.array(fr[-min_len:]) for fr in available_factor_returns]
        )

        # Skip columns with zero variance (constant series)
        valid_cols = []
        valid_factors = []
        for k in range(X.shape[1]):
            if np.std(X[:, k]) > 0:
                valid_cols.append(k)
                valid_factors.append(available_factors[k])

        if not valid_cols or np.std(y) == 0:
            results.append(_empty_factor_result(sym))
            continue

        X_filtered = X[:, valid_cols]

        # Add intercept
        X_with_intercept = np.column_stack([np.ones(min_len), X_filtered])

        try:
            with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
                betas = np.linalg.lstsq(X_with_intercept, y, rcond=None)[0]
                if not np.all(np.isfinite(betas)):
                    results.append(_empty_factor_result(sym))
                    continue
                y_pred = X_with_intercept @ betas

            ss_res = float(np.sum((y - y_pred) ** 2))
            ss_tot = float(np.sum((y - np.mean(y)) ** 2))
            r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
            r_squared = max(0.0, r_squared)
            residual_std = float(np.std(y - y_pred))

            factor_results = []
            stock_std = float(np.std(y))
            for k, factor in enumerate(valid_factors):
                beta_val = float(betas[k + 1])  # skip intercept
                factor_std = float(np.std(X_filtered[:, k]))
                contribution = (
                    abs(beta_val) * factor_std / stock_std
                    if stock_std > 0
                    else 0.0
                )
                if not math.isfinite(contribution):
                    contribution = 0.0
                factor_results.append({
                    "name": factor["name"],
                    "symbol": factor["symbol"],
                    "beta": round(beta_val, 4),
                    "contribution": round(contribution, 4),
                })

            factor_results.sort(key=lambda x: -abs(x["contribution"]))

            results.append({
                "symbol": sym,
                "factors": factor_results,
                "r_squared": round(r_squared, 4),
                "residual_std": round(residual_std, 6),
            })
        except (np.linalg.LinAlgError, ValueError):
            results.append(_empty_factor_result(sym))

    return results


def _empty_factor_result(symbol: str) -> dict:
    """Return empty factor result for a stock with insufficient data."""
    return {
        "symbol": symbol,
        "factors": [],
        "r_squared": 0.0,
        "residual_std": 0.0,
    }


# ---------------------------------------------------------------------------
# VaR Computation
# ---------------------------------------------------------------------------

def compute_var(
    portfolio_data: list[dict],
    weights: list[float],
    confidence_levels: tuple[float, ...] = (0.95, 0.99),
    total_value: Optional[float] = None,
) -> dict:
    """Compute historical Value-at-Risk for a portfolio.

    Parameters
    ----------
    portfolio_data : list[dict]
        Each dict must have "price_history" (list of close prices).
    weights : list[float]
        Portfolio weights (should sum to ~1.0).
    confidence_levels : tuple
        Confidence levels for VaR (default: 95%, 99%).
    total_value : float or None
        Total portfolio value for computing absolute VaR amounts.

    Returns
    -------
    dict
        {
            "daily_var": {0.95: float, 0.99: float},
            "monthly_var": {0.95: float, 0.99: float},
            "daily_var_amount": {0.95: float, 0.99: float},  (if total_value)
            "monthly_var_amount": {0.95: float, 0.99: float},  (if total_value)
            "portfolio_volatility": float,
            "observation_days": int,
        }
    """
    # Compute daily returns for each stock
    all_returns = []
    for stock in portfolio_data:
        prices = stock.get("price_history", [])
        returns = _compute_daily_returns(prices)
        all_returns.append(returns)

    if not all_returns:
        return _empty_var()

    min_len = min(len(r) for r in all_returns)
    if min_len < 30:
        return _empty_var()

    # Trim to same length (use most recent data)
    aligned = [r[-min_len:] for r in all_returns]

    # Compute portfolio weighted daily returns
    n_days = min_len
    portfolio_returns = []
    for day in range(n_days):
        day_return = sum(
            aligned[i][day] * weights[i]
            for i in range(len(weights))
            if i < len(aligned)
        )
        portfolio_returns.append(day_return)

    pf_arr = np.array(portfolio_returns)
    portfolio_vol = float(np.std(pf_arr)) * math.sqrt(252)

    # Historical VaR
    daily_var: dict[float, float] = {}
    monthly_var: dict[float, float] = {}
    daily_var_amount: dict[float, float] = {}
    monthly_var_amount: dict[float, float] = {}

    for cl in confidence_levels:
        percentile = (1.0 - cl) * 100  # e.g. 95% -> 5th percentile
        d_var = float(np.percentile(pf_arr, percentile))
        daily_var[cl] = round(d_var, 6)
        # Scale to monthly (sqrt(21) approximation)
        m_var = d_var * math.sqrt(21)
        monthly_var[cl] = round(m_var, 6)

        if total_value is not None:
            daily_var_amount[cl] = round(d_var * total_value, 0)
            monthly_var_amount[cl] = round(m_var * total_value, 0)

    result: dict = {
        "daily_var": daily_var,
        "monthly_var": monthly_var,
        "portfolio_volatility": round(portfolio_vol, 4),
        "observation_days": n_days,
    }
    if total_value is not None:
        result["daily_var_amount"] = daily_var_amount
        result["monthly_var_amount"] = monthly_var_amount
        result["total_value"] = total_value

    return result


def _empty_var() -> dict:
    """Return empty VaR result when data is insufficient."""
    return {
        "daily_var": {},
        "monthly_var": {},
        "portfolio_volatility": 0.0,
        "observation_days": 0,
    }
