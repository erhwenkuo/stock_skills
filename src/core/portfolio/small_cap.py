"""Small-cap classification and allocation rules (KIK-438/574).

Provides region-aware market-cap classification and portfolio-level
small-cap allocation checks.
KIK-574: Thresholds loaded from config/thresholds.yaml with hardcoded fallback.
"""

from src.core._thresholds import th, get_thresholds

# Hardcoded fallback (used when YAML is missing or region not in YAML)
_FALLBACK_THRESHOLDS: dict[str, float] = {
    "jp": 100_000_000_000,       # 100 billion JPY
    "us": 1_000_000_000,         # $1B
    "sg": 2_000_000_000,         # SGD 2B
    "th": 30_000_000_000,        # THB 30B
    "my": 5_000_000_000,         # MYR 5B
    "id": 15_000_000_000_000,    # IDR 15T
    "ph": 50_000_000_000,        # PHP 50B
    "hk": 10_000_000_000,        # HKD 10B
    "kr": 1_000_000_000_000,     # KRW 1T
    "tw": 30_000_000_000,        # TWD 30B
    "cn": 10_000_000_000,        # CNY 10B
    "gb": 500_000_000,           # GBP 500M
    "de": 1_000_000_000,         # EUR 1B
    "fr": 1_000_000_000,         # EUR 1B
    "ca": 1_000_000_000,         # CAD 1B
    "au": 1_500_000_000,         # AUD 1.5B
    "br": 5_000_000_000,         # BRL 5B
    "in": 100_000_000_000,       # INR 100B
}


def _get_small_cap_thresholds() -> dict[str, float]:
    """Load small-cap thresholds from YAML, fall back to hardcoded."""
    yaml_section = get_thresholds().get("small_cap", {})
    if yaml_section:
        result = dict(_FALLBACK_THRESHOLDS)
        for region, val in yaml_section.items():
            if region != "large_cap_multiplier" and isinstance(val, (int, float)):
                result[region] = float(val)
        return result
    return dict(_FALLBACK_THRESHOLDS)


def _get_large_cap_multiplier() -> float:
    """Load large-cap multiplier from YAML, default 5."""
    return float(th("small_cap", "large_cap_multiplier", 5))


# Backward-compatible aliases (used by tests)
_SMALL_CAP_THRESHOLDS = _FALLBACK_THRESHOLDS
_LARGE_CAP_MULTIPLIER = 5


def classify_market_cap(market_cap: float | None, region_code: str) -> str:
    """Classify stock size from market cap and region code.

    Returns
    -------
    str
        "Small-cap", "Mid-cap", "Large-cap", or "Unknown"
    """
    if market_cap is None or market_cap <= 0:
        return "Unknown"
    thresholds = _get_small_cap_thresholds()
    small_threshold = thresholds.get(region_code)
    if small_threshold is None:
        return "Unknown"
    if market_cap <= small_threshold:
        return "Small-cap"
    if market_cap <= small_threshold * _get_large_cap_multiplier():
        return "Mid-cap"
    return "Large-cap"


def check_small_cap_allocation(small_cap_weight: float) -> dict:
    """Check portfolio-level small-cap allocation.

    Returns
    -------
    dict
        {"level": "ok"|"warning"|"critical", "weight": float, "message": str}
    """
    warn_pct = th("health", "small_cap_warn_pct", 0.25)
    crit_pct = th("health", "small_cap_crit_pct", 0.35)

    if small_cap_weight > crit_pct:
        return {
            "level": "critical",
            "weight": small_cap_weight,
            "message": f"Small-cap ratio {small_cap_weight * 100:.0f}% — Over-concentrated (>{crit_pct * 100:.0f}%)",
        }
    if small_cap_weight > warn_pct:
        return {
            "level": "warning",
            "weight": small_cap_weight,
            "message": f"Small-cap ratio {small_cap_weight * 100:.0f}% — Caution (>{warn_pct * 100:.0f}%)",
        }
    return {
        "level": "ok",
        "weight": small_cap_weight,
        "message": f"Small-cap ratio {small_cap_weight * 100:.0f}% — Normal",
    }
