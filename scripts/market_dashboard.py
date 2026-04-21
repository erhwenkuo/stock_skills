#!/usr/bin/env python3
"""Market quantitative dashboard — VIX, Fear & Greed, Yield Curve (KIK-567).

Usage:
    python3 scripts/market_dashboard.py

Uses yfinance only. No Grok API required.
For qualitative analysis, use: /market-research market
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.yahoo_client.macro import get_macro_indicators
from src.core.market_dashboard import (
    compute_fear_greed,
    get_vix_history,
    get_yield_curve,
)


def _fmt_change(val, is_point: bool = False) -> str:
    if val is None:
        return "-"
    if is_point:
        return f"{val:+.2f}pt"
    return f"{val * 100:+.1f}%"


def _fmt_price(val) -> str:
    if val is None:
        return "-"
    if val >= 1000:
        return f"{val:,.0f}"
    if val >= 100:
        return f"{val:.1f}"
    return f"{val:.2f}"


def main():
    today = date.today().isoformat()
    print(f"## Market Dashboard ({today})")
    print()

    # --- Macro indicators ---
    print("### Key Indicators")
    print()
    print("| Indicator | Value | Daily Change | Weekly Change |")
    print("|:---|---:|---:|---:|")

    indicators = get_macro_indicators()
    for ind in indicators:
        name = ind["name"]
        price = _fmt_price(ind["price"])
        daily = _fmt_change(ind["daily_change"], ind.get("is_point_diff", False))
        weekly = _fmt_change(ind["weekly_change"], ind.get("is_point_diff", False))
        print(f"| {name} | {price} | {daily} | {weekly} |")
    print()

    # --- Fear & Greed ---
    print("### Fear & Greed Score")
    print()
    fg = compute_fear_greed()
    fg_emoji = {
        "Extreme Fear": "😱",
        "Fear": "😰",
        "Neutral": "😐",
        "Greed": "😊",
        "Extreme Greed": "🤑",
    }
    emoji = fg_emoji.get(fg["label"], "")
    print(f"**{fg['score']:.0f} / 100** — {emoji} {fg['label']}")
    print()
    if fg["indicators"]:
        print("| Indicator | Value | Score | Signal |")
        print("|:---|---:|---:|:---|")
        for ind in fg["indicators"]:
            print(f"| {ind['name']} | {ind['value']} | {ind['score']:.0f} | {ind['signal']} |")
        print()

    # --- VIX History ---
    print("### VIX Trend (1 Month)")
    print()
    vix = get_vix_history()
    if vix["current"] is not None:
        print(f"Current: **{vix['current']}** — {vix['phase']} (Trend: {vix['trend']})")
        print()
        if vix["history"]:
            print("| Date | VIX |")
            print("|:---|---:|")
            for h in vix["history"]:
                print(f"| {h['date']} | {h['close']} |")
            print()
    else:
        print("VIX data unavailable")
        print()

    # --- Yield Curve ---
    print("### Interest Rates & Yield Curve")
    print()
    yc = get_yield_curve()
    if yc["yields"]:
        print("| Tenor | Yield |")
        print("|:---|---:|")
        for tenor in ["3M", "5Y", "10Y", "30Y"]:
            rate = yc["yields"].get(tenor, "-")
            print(f"| US {tenor} | {rate}% |" if isinstance(rate, float) else f"| US {tenor} | - |")
        print()
        if yc["spread_10y_3m"] is not None:
            print(f"10Y-3M Spread: **{yc['spread_10y_3m']:+.3f}%** — {yc['curve_status']}")
        if yc["history_10y"]:
            print()
            print("US 10Y Yield Trend:")
            print("| Date | Yield |")
            print("|:---|---:|")
            for h in yc["history_10y"]:
                print(f"| {h['date']} | {h['rate']}% |")
        print()
    else:
        print("Interest rate data unavailable")
        print()


if __name__ == "__main__":
    main()
