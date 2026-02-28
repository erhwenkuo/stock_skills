"""Tests for src/core/screening/trending_screener.py."""

import pytest

from src.core.screening.trending_screener import TrendingScreener


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_stock_info(symbol="7203.T", per=8.0, pbr=0.7, roe=0.12,
                     dividend_yield=0.035):
    """Create a stock info dict."""
    return {
        "symbol": symbol,
        "name": f"Company {symbol}",
        "price": 2500.0,
        "per": per,
        "pbr": pbr,
        "roe": roe,
        "dividend_yield": dividend_yield,
        "dividend_yield_trailing": dividend_yield * 0.95 if dividend_yield else None,
        "revenue_growth": 0.08,
        "sector": "Technology",
    }


class _MockGrokClient:
    """Mock grok_client module for TrendingScreener tests."""

    def __init__(self, trending_stocks=None, market_context=""):
        self._trending_stocks = trending_stocks or []
        self._market_context = market_context

    def search_trending_stocks(self, region="japan", theme=None, timeout=60):
        return {
            "stocks": self._trending_stocks,
            "market_context": self._market_context,
        }


class _MockYahooClient:
    """Mock yahoo_client for TrendingScreener tests."""

    def __init__(self, stock_info=None):
        self._stock_info = stock_info

    def get_stock_info(self, symbol):
        if callable(self._stock_info):
            return self._stock_info(symbol)
        return self._stock_info


# ---------------------------------------------------------------------------
# Tests: classify()
# ---------------------------------------------------------------------------

class TestTrendingScreenerClassify:
    def test_undervalued(self):
        """score >= 60 -> undervalued."""
        assert TrendingScreener.classify(60) == "話題×割安"
        assert TrendingScreener.classify(80) == "話題×割安"
        assert TrendingScreener.classify(100) == "話題×割安"

    def test_fair_value(self):
        """30 <= score < 60 -> fair value."""
        assert TrendingScreener.classify(30) == "話題×適正"
        assert TrendingScreener.classify(45) == "話題×適正"
        assert TrendingScreener.classify(59.9) == "話題×適正"

    def test_overvalued(self):
        """score < 30 -> overvalued."""
        assert TrendingScreener.classify(0) == "話題×割高"
        assert TrendingScreener.classify(15) == "話題×割高"
        assert TrendingScreener.classify(29.9) == "話題×割高"

    def test_boundary_60(self):
        """Exactly 60 is undervalued."""
        assert TrendingScreener.classify(60) == "話題×割安"

    def test_boundary_30(self):
        """Exactly 30 is fair value."""
        assert TrendingScreener.classify(30) == "話題×適正"


# ---------------------------------------------------------------------------
# Tests: class constants
# ---------------------------------------------------------------------------

class TestTrendingScreenerConstants:
    def test_undervalued_threshold(self):
        assert TrendingScreener.UNDERVALUED_THRESHOLD == 60

    def test_fair_value_threshold(self):
        assert TrendingScreener.FAIR_VALUE_THRESHOLD == 30

    def test_no_data_classification(self):
        assert TrendingScreener.CLASSIFICATION_NO_DATA == "話題×データ不足"


# ---------------------------------------------------------------------------
# Tests: screen() method
# ---------------------------------------------------------------------------

class TestTrendingScreenerScreen:
    def test_empty_trending_returns_empty(self):
        """No trending stocks -> empty results."""
        grok = _MockGrokClient(trending_stocks=[])
        ts = TrendingScreener(_MockYahooClient(), grok)
        results, ctx = ts.screen(region="japan")
        assert results == []
        assert ctx == ""

    def test_market_context_returned(self):
        """market_context is returned as second element."""
        grok = _MockGrokClient(
            trending_stocks=[],
            market_context="Market is bullish",
        )
        ts = TrendingScreener(_MockYahooClient(), grok)
        results, ctx = ts.screen()
        assert ctx == "Market is bullish"

    def test_normal_screening_with_stock_info(self):
        """Normal case: trending stocks enriched with fundamentals."""
        trending = [
            {"ticker": "7203.T", "name": "Toyota", "reason": "EV news"},
            {"ticker": "6758.T", "name": "Sony", "reason": "PS6"},
        ]
        info = _make_stock_info(per=8.0, pbr=0.7, roe=0.12)

        grok = _MockGrokClient(trending_stocks=trending)
        ts = TrendingScreener(
            _MockYahooClient(stock_info=info),
            grok,
        )
        results, _ = ts.screen()
        assert len(results) == 2
        for r in results:
            assert "classification" in r
            assert "value_score" in r
            assert "trending_reason" in r

    def test_no_stock_info_gets_no_data_classification(self):
        """Stock with no Yahoo info gets CLASSIFICATION_NO_DATA."""
        trending = [{"ticker": "XXXX.T", "name": "Unknown", "reason": "buzz"}]

        grok = _MockGrokClient(trending_stocks=trending)
        ts = TrendingScreener(_MockYahooClient(stock_info=None), grok)
        results, _ = ts.screen()

        assert len(results) == 1
        r = results[0]
        assert r["classification"] == "話題×データ不足"
        assert r["value_score"] == 0.0
        assert r["price"] is None

    def test_result_fields_with_data(self):
        """Results contain all expected fields when data is available."""
        trending = [{"ticker": "7203.T", "name": "Toyota", "reason": "earnings"}]
        info = _make_stock_info()

        grok = _MockGrokClient(trending_stocks=trending)
        ts = TrendingScreener(_MockYahooClient(stock_info=info), grok)
        results, _ = ts.screen()

        assert len(results) == 1
        r = results[0]
        expected_keys = [
            "symbol", "name", "trending_reason", "price", "per", "pbr",
            "dividend_yield", "dividend_yield_trailing", "roe",
            "value_score", "classification", "sector",
        ]
        for key in expected_keys:
            assert key in r, f"Missing key: {key}"

    def test_result_fields_no_data(self):
        """Results contain all fields even when stock info is None."""
        trending = [{"ticker": "XXXX.T", "name": "Unknown", "reason": "buzz"}]

        grok = _MockGrokClient(trending_stocks=trending)
        ts = TrendingScreener(_MockYahooClient(stock_info=None), grok)
        results, _ = ts.screen()

        r = results[0]
        expected_keys = [
            "symbol", "name", "trending_reason", "price", "per", "pbr",
            "dividend_yield", "dividend_yield_trailing", "roe",
            "value_score", "classification", "sector",
        ]
        for key in expected_keys:
            assert key in r

    def test_sorted_by_classification_then_score(self):
        """Results sorted by classification order, then by value_score desc."""
        trending = [
            {"ticker": "A.T", "name": "A", "reason": "r1"},
            {"ticker": "B.T", "name": "B", "reason": "r2"},
            {"ticker": "C.T", "name": "C", "reason": "r3"},
        ]

        def info_fn(symbol):
            mapping = {
                "A.T": _make_stock_info("A.T", per=5, pbr=0.3, roe=0.20, dividend_yield=0.06),   # high score
                "B.T": _make_stock_info("B.T", per=30, pbr=3.0, roe=0.03, dividend_yield=0.005),  # low score
                "C.T": _make_stock_info("C.T", per=10, pbr=0.8, roe=0.10, dividend_yield=0.03),   # medium score
            }
            return mapping.get(symbol)

        grok = _MockGrokClient(trending_stocks=trending)
        ts = TrendingScreener(_MockYahooClient(stock_info=info_fn), grok)
        results, _ = ts.screen()

        # Classification order: undervalued < fair < overvalued < no data
        _CLASS_ORDER = {"話題×割安": 0, "話題×適正": 1, "話題×割高": 2, "話題×データ不足": 3}
        class_values = [_CLASS_ORDER.get(r["classification"], 99) for r in results]
        for i in range(len(class_values) - 1):
            if class_values[i] == class_values[i + 1]:
                # Same class: higher score should come first
                assert results[i]["value_score"] >= results[i + 1]["value_score"]
            else:
                assert class_values[i] <= class_values[i + 1]

    def test_respects_top_n(self):
        """Only top_n results returned."""
        trending = [
            {"ticker": f"{i}.T", "name": f"Co{i}", "reason": "trending"}
            for i in range(1, 11)
        ]
        info = _make_stock_info()

        grok = _MockGrokClient(trending_stocks=trending)
        ts = TrendingScreener(_MockYahooClient(stock_info=info), grok)
        results, _ = ts.screen(top_n=3)
        assert len(results) <= 3

    def test_empty_ticker_skipped(self):
        """Trending items with empty ticker are skipped."""
        trending = [
            {"ticker": "", "name": "No Ticker", "reason": "rumor"},
            {"ticker": "7203.T", "name": "Toyota", "reason": "earnings"},
        ]
        info = _make_stock_info()

        grok = _MockGrokClient(trending_stocks=trending)
        ts = TrendingScreener(_MockYahooClient(stock_info=info), grok)
        results, _ = ts.screen()
        assert len(results) == 1
        assert results[0]["symbol"] == "7203.T"

    def test_no_ticker_key_skipped(self):
        """Trending items without ticker key are skipped."""
        trending = [
            {"name": "No Ticker Key", "reason": "rumor"},
        ]
        grok = _MockGrokClient(trending_stocks=trending)
        ts = TrendingScreener(_MockYahooClient(), grok)
        results, _ = ts.screen()
        assert results == []

    def test_name_from_info_preferred(self):
        """Stock name from Yahoo info is preferred over Grok name."""
        trending = [{"ticker": "7203.T", "name": "GrokName", "reason": "test"}]
        info = _make_stock_info("7203.T")
        info["name"] = "YahooName"

        grok = _MockGrokClient(trending_stocks=trending)
        ts = TrendingScreener(_MockYahooClient(stock_info=info), grok)
        results, _ = ts.screen()
        assert results[0]["name"] == "YahooName"

    def test_name_fallback_to_grok(self):
        """When Yahoo name is None, falls back to Grok name."""
        trending = [{"ticker": "7203.T", "name": "GrokName", "reason": "test"}]
        info = _make_stock_info("7203.T")
        info["name"] = None

        grok = _MockGrokClient(trending_stocks=trending)
        ts = TrendingScreener(_MockYahooClient(stock_info=info), grok)
        results, _ = ts.screen()
        assert results[0]["name"] == "GrokName"

    def test_mixed_data_and_no_data(self):
        """Mix of stocks with and without Yahoo data."""
        trending = [
            {"ticker": "7203.T", "name": "Toyota", "reason": "EV"},
            {"ticker": "XXXX.T", "name": "Unknown", "reason": "buzz"},
        ]

        def info_fn(symbol):
            if symbol == "7203.T":
                return _make_stock_info("7203.T")
            return None

        grok = _MockGrokClient(trending_stocks=trending)
        ts = TrendingScreener(_MockYahooClient(stock_info=info_fn), grok)
        results, _ = ts.screen()
        assert len(results) == 2

        classifications = [r["classification"] for r in results]
        # The no-data one should be last (sorted by class order)
        assert results[-1]["classification"] == "話題×データ不足"
