"""Shared private helpers for portfolio formatter modules (KIK-447)."""

from typing import Optional

# Re-import canonical currency formatters from _format_helpers (KIK-572).
# Private aliases kept for backward compatibility with existing callers.
from src.output._format_helpers import fmt_jpy as _fmt_jpy  # noqa: F401
from src.output._format_helpers import fmt_usd as _fmt_usd  # noqa: F401
from src.output._format_helpers import fmt_currency_value as _fmt_currency_value  # noqa: F401


def _pnl_indicator(value: Optional[float]) -> str:
    """Return gain/loss indicator: triangle-up for positive, triangle-down for negative."""
    if value is None:
        return ""
    if value > 0:
        return "\u25b2"  # ▲
    elif value < 0:
        return "\u25bc"  # ▼
    return ""


def _classify_hhi(hhi: float) -> str:
    """Classify HHI into a risk label."""
    if hhi < 0.25:
        return "Diversified"
    if hhi < 0.50:
        return "Moderately concentrated"
    return "Dangerously concentrated"


def _fmt_k(value: Optional[float]) -> str:
    """Format a value in K (thousands) notation, e.g. 10000000 -> '¥10,000K'."""
    if value is None:
        return "-"
    k = value / 1000
    if k < 0:
        return f"-\u00a5{abs(k):,.0f}K"
    return f"\u00a5{k:,.0f}K"
