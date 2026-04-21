"""Alert level computation for portfolio health checks (KIK-576).

Computes 3-level alert system: early_warning, caution, exit.
"""

from src.core.value_trap import detect_value_trap as _detect_value_trap

# Alert level constants
ALERT_NONE = "none"
ALERT_EARLY_WARNING = "early_warning"
ALERT_CAUTION = "caution"
ALERT_EXIT = "exit"


def compute_alert_level(
    trend_health: dict,
    change_quality: dict,
    stock_detail=None,
    return_stability: dict | None = None,
    is_small_cap: bool = False,
) -> dict:
    """Compute 3-level alert from trend and change quality.

    Level priority: exit > caution > early_warning > none.

    Parameters
    ----------
    is_small_cap : bool
        If True, escalate early_warning to caution (KIK-438).

    Returns
    -------
    dict
        Keys: level, emoji, label, reasons.
    """
    reasons: list[str] = []
    level = ALERT_NONE

    trend = trend_health.get("trend", "Unknown")
    quality_label = change_quality.get("quality_label", "Good")
    dead_cross = trend_health.get("dead_cross", False)
    rsi_drop = trend_health.get("rsi_drop", False)
    price_above_sma50 = trend_health.get("price_above_sma50", True)
    sma50_approaching = trend_health.get("sma50_approaching_sma200", False)
    cross_signal = trend_health.get("cross_signal", "none")
    days_since_cross = trend_health.get("days_since_cross")
    cross_date = trend_health.get("cross_date")

    if quality_label == "N/A":
        # ETF: evaluate technical conditions only (no quality data)
        if not price_above_sma50:
            level = ALERT_EARLY_WARNING
            sma50_val = trend_health.get("sma50", 0)
            price_val = trend_health.get("current_price", 0)
            reasons.append(f"Below SMA50 (current {price_val}, SMA50={sma50_val})")
        if dead_cross:
            level = ALERT_CAUTION
            reasons.append("Death cross")
        if rsi_drop:
            if level == ALERT_NONE:
                level = ALERT_EARLY_WARNING
            rsi_val = trend_health.get("rsi", 0)
            reasons.append(f"RSI sharp drop ({rsi_val})")
    else:
        # --- EXIT ---
        # KIK-357: EXIT requires technical collapse AND fundamental deterioration.
        # Dead cross + good fundamentals = CAUTION (not EXIT).
        if dead_cross and quality_label == "Multiple deteriorated":
            level = ALERT_EXIT
            reasons.append("Death cross + change score multiple deteriorated")
        elif dead_cross and trend == "Downtrend":
            if quality_label == "Good":
                level = ALERT_CAUTION
                reasons.append("Death cross (fundamentals good → CAUTION)")
            else:
                # quality_label is "1 metric↓" — technical + fundamental confirm
                level = ALERT_EXIT
                reasons.append("Trend breakdown (death cross + fundamental deterioration)")

        # --- CAUTION ---
        elif sma50_approaching and quality_label in ("1 metric↓", "Multiple deteriorated"):
            level = ALERT_CAUTION
            if quality_label == "Multiple deteriorated":
                reasons.append("Change score multiple deteriorated")
            else:
                reasons.append("Change score 1 metric deteriorated")
            reasons.append("SMA50 approaching SMA200")
        elif quality_label == "Multiple deteriorated":
            level = ALERT_CAUTION
            reasons.append("Change score multiple deteriorated")

        # --- EARLY WARNING ---
        elif not price_above_sma50:
            level = ALERT_EARLY_WARNING
            sma50_val = trend_health.get("sma50", 0)
            price_val = trend_health.get("current_price", 0)
            reasons.append(f"Below SMA50 (current {price_val}, SMA50={sma50_val})")
        elif rsi_drop:
            level = ALERT_EARLY_WARNING
            rsi_val = trend_health.get("rsi", 0)
            reasons.append(f"RSI sharp drop ({rsi_val})")
        elif quality_label == "1 metric↓":
            level = ALERT_EARLY_WARNING
            reasons.append("Change score 1 metric deteriorated")

    # Recent death cross event: add date context to reasons
    if cross_signal == "death_cross" and days_since_cross is not None and days_since_cross <= 10:
        reasons.append(f"Death cross occurred ({days_since_cross} days ago, {cross_date})")

    # Recent golden cross: positive signal -> early warning if no other alert
    if cross_signal == "golden_cross" and days_since_cross is not None and days_since_cross <= 20:
        if level == ALERT_NONE:
            level = ALERT_EARLY_WARNING
        reasons.append(
            f"Golden cross occurred ({days_since_cross} days ago, {cross_date})"
            " - possible uptrend reversal"
        )

    # Value trap detection (KIK-381)
    value_trap = _detect_value_trap(stock_detail)
    if value_trap["is_trap"]:
        for reason in value_trap["reasons"]:
            if reason not in reasons:
                reasons.append(reason)
        # Escalate to at least EARLY_WARNING
        if level == ALERT_NONE:
            level = ALERT_EARLY_WARNING

    # Shareholder return stability (KIK-403)
    if return_stability is not None:
        stability = return_stability.get("stability")
        if stability == "temporary":
            reason_text = return_stability.get("reason", "Temporary high return")
            reason_str = f"Possibly temporary high return ({reason_text})"
            if reason_str not in reasons:
                reasons.append(reason_str)
            if level == ALERT_NONE:
                level = ALERT_EARLY_WARNING
        elif stability == "decreasing":
            reason_text = return_stability.get("reason", "Return rate declining")
            reason_str = f"Shareholder return rate declining ({reason_text})"
            if reason_str not in reasons:
                reasons.append(reason_str)

    # Small-cap escalation (KIK-438): early_warning -> caution
    if is_small_cap and level == ALERT_EARLY_WARNING:
        level = ALERT_CAUTION
        reasons.append("[Small-cap] Escalated to caution due to small-cap")

    level_map = {
        ALERT_NONE: ("", "None"),
        ALERT_EARLY_WARNING: ("\u26a1", "Early Warning"),
        ALERT_CAUTION: ("\u26a0", "Caution"),
        ALERT_EXIT: ("\U0001f6a8", "Exit"),
    }
    emoji, label = level_map[level]

    return {
        "level": level,
        "emoji": emoji,
        "label": label,
        "reasons": reasons,
    }
