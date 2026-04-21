"""ETF-specific health check logic (KIK-469, KIK-576).

Extracted from health_etf.py as part of KIK-576 health subpackage split.
"""


def check_etf_health(stock_detail: dict) -> dict:
    """ETF-specific health check (KIK-469).

    Returns dict with:
        expense_ratio, expense_label, aum, aum_label, score (0-100), alerts,
        fund_category, fund_family.
    """
    info = stock_detail.get("info", stock_detail)
    er = info.get("expense_ratio")
    aum = info.get("total_assets_fund")
    alerts: list[str] = []

    # Expense ratio evaluation
    if er is not None:
        if er <= 0.001:
            expense_label = "Ultra low-cost"
        elif er <= 0.005:
            expense_label = "Low-cost"
        elif er <= 0.01:
            expense_label = "Slightly high"
            alerts.append(f"Expense ratio {er*100:.2f}% is slightly high")
        else:
            expense_label = "High-cost"
            alerts.append(f"High expense ratio ({er*100:.2f}% — unfavorable for long-term holding)")
    else:
        expense_label = "-"

    # AUM evaluation
    if aum is not None:
        if aum >= 1_000_000_000:
            aum_label = "Sufficient"
        elif aum >= 100_000_000:
            aum_label = "Small AUM"
            alerts.append("Small AUM (note liquidity/redemption risk)")
        else:
            aum_label = "Tiny AUM"
            alerts.append("Tiny AUM (redemption risk present)")
    else:
        aum_label = "-"

    # ETF score (0-100, based on expense ratio and AUM)
    score = 50  # baseline
    if er is not None:
        if er <= 0.001:
            score += 25
        elif er <= 0.005:
            score += 15
        elif er <= 0.01:
            score += 0
        else:
            score -= 15
    if aum is not None:
        if aum >= 10_000_000_000:
            score += 25
        elif aum >= 1_000_000_000:
            score += 15
        elif aum >= 100_000_000:
            score += 0
        else:
            score -= 15

    return {
        "expense_ratio": er,
        "expense_label": expense_label,
        "aum": aum,
        "aum_label": aum_label,
        "score": max(0, min(100, score)),
        "alerts": alerts,
        "fund_category": info.get("fund_category"),
        "fund_family": info.get("fund_family"),
    }
