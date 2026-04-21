"""Value trap detection (extracted from health_check.py, KIK-392).

Detects stocks that appear cheap on valuation metrics but have
deteriorating fundamentals — a classic 'value trap' pattern.
"""

from src.core.common import finite_or_none


def detect_value_trap(stock_detail: dict) -> dict:
    """Detect value trap: stock appears cheap but fundamentals are deteriorating.

    Returns {"is_trap": bool, "reasons": list[str]}.
    """
    if stock_detail is None:
        return {"is_trap": False, "reasons": []}

    per = finite_or_none(stock_detail.get("per"))
    pbr = finite_or_none(stock_detail.get("pbr"))
    roe = finite_or_none(stock_detail.get("roe"))
    eps_growth = finite_or_none(stock_detail.get("eps_growth"))
    rev_growth = finite_or_none(stock_detail.get("revenue_growth"))

    reasons = []

    # Condition A: Very low PER + negative earnings growth
    if per is not None and per < 8 and eps_growth is not None and eps_growth < 0:
        reasons.append("Low PER but earnings declining")

    # Condition B: Low PER + significant revenue decline (regardless of EPS)
    # Revenue decline with low PER signals value trap even when EPS is temporarily up
    if per is not None and rev_growth is not None:
        if per < 10 and rev_growth <= -0.05:
            reasons.append("Low PER + revenue declining trend")

    # Condition C: Low PBR + low ROE + negative earnings growth
    if pbr is not None and roe is not None and eps_growth is not None:
        if pbr < 0.8 and roe < 0.05 and eps_growth < 0:
            reasons.append("Low PBR but ROE declining and earnings decreasing")
    return {"is_trap": bool(reasons), "reasons": reasons}
