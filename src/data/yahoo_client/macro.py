"""Macro economic indicators (KIK-396, KIK-449)."""

import time

import yfinance as yf


MACRO_TICKERS = {
    "S&P500": "^GSPC",
    "Nikkei 225": "^N225",
    "VIX": "^VIX",
    "US 10Y Yield": "^TNX",
    "USD/JPY": "JPY=X",
    "EUR/USD": "EURUSD=X",
    "Crude Oil (WTI)": "CL=F",
    "Gold": "GC=F",
}

# Tickers where change is expressed as point difference, not percentage
_POINT_DIFF_TICKERS = {"^VIX", "^TNX"}


def get_macro_indicators() -> list[dict]:
    """Fetch macro economic indicators (8 tickers).

    Returns a list of dicts with keys:
        name, symbol, price, daily_change, weekly_change, is_point_diff.

    ``daily_change`` and ``weekly_change`` are percentage changes (0.01 = 1%)
    for normal tickers, or raw point differences for VIX / bond yields
    (``is_point_diff=True``).

    No caching is applied because freshness is important.
    A 1-second sleep is used per ticker for rate-limit compliance.
    """
    results: list[dict] = []

    for name, symbol in MACRO_TICKERS.items():
        try:
            time.sleep(1)
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            if hist is None or hist.empty or "Close" not in hist.columns:
                results.append({
                    "name": name,
                    "symbol": symbol,
                    "price": None,
                    "daily_change": None,
                    "weekly_change": None,
                    "is_point_diff": symbol in _POINT_DIFF_TICKERS,
                })
                continue

            closes = hist["Close"].dropna()
            if len(closes) == 0:
                results.append({
                    "name": name,
                    "symbol": symbol,
                    "price": None,
                    "daily_change": None,
                    "weekly_change": None,
                    "is_point_diff": symbol in _POINT_DIFF_TICKERS,
                })
                continue

            latest = float(closes.iloc[-1])
            is_point = symbol in _POINT_DIFF_TICKERS

            # Daily change
            daily_change = None
            if len(closes) >= 2:
                prev = float(closes.iloc[-2])
                if is_point:
                    daily_change = latest - prev
                elif prev != 0:
                    daily_change = (latest - prev) / prev

            # Weekly change (oldest available in 5d window)
            weekly_change = None
            oldest = float(closes.iloc[0])
            if is_point:
                weekly_change = latest - oldest
            elif oldest != 0:
                weekly_change = (latest - oldest) / oldest

            results.append({
                "name": name,
                "symbol": symbol,
                "price": latest,
                "daily_change": daily_change,
                "weekly_change": weekly_change,
                "is_point_diff": is_point,
            })
        except Exception as e:
            print(f"[yahoo_client] Error fetching macro indicator {name}: {e}")
            continue

    return results
