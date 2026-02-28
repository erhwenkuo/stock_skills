"""Tests for src/core/screening/value_screener.py."""

import warnings

import pytest

from src.core.screening.value_screener import ValueScreener


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_stock_info(symbol="7203.T", per=8.0, pbr=0.7, roe=0.12,
                     dividend_yield=0.035, revenue_growth=0.05):
    """Create a stock info dict as returned by get_stock_info."""
    return {
        "symbol": symbol,
        "name": f"Company {symbol}",
        "price": 2500.0,
        "per": per,
        "pbr": pbr,
        "roe": roe,
        "dividend_yield": dividend_yield,
        "dividend_yield_trailing": dividend_yield * 0.95 if dividend_yield else None,
        "revenue_growth": revenue_growth,
        "market_cap": 500_000_000_000,
    }


class _MockMarket:
    """Mock market object for ValueScreener."""

    def __init__(self, symbols=None, thresholds=None):
        self._symbols = symbols or ["7203.T", "6758.T", "9984.T"]
        self._thresholds = thresholds or {}

    def get_default_symbols(self):
        return self._symbols

    def get_thresholds(self):
        return self._thresholds


class _MockYahooClient:
    """Mock yahoo_client for ValueScreener tests."""

    def __init__(self, stock_info=None):
        self._stock_info = stock_info

    def get_stock_info(self, symbol):
        if callable(self._stock_info):
            return self._stock_info(symbol)
        return self._stock_info


# ---------------------------------------------------------------------------
# Tests: initialization
# ---------------------------------------------------------------------------

class TestValueScreenerInit:
    def test_init_emits_deprecation_warning(self):
        """ValueScreener.__init__ emits a DeprecationWarning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ValueScreener(_MockYahooClient(), _MockMarket())
            assert len(w) >= 1
            assert any(issubclass(x.category, DeprecationWarning) for x in w)

    def test_init_stores_client_and_market(self):
        """Client and market are stored as instance attributes."""
        client = _MockYahooClient()
        market = _MockMarket()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            vs = ValueScreener(client, market)
        assert vs.yahoo_client is client
        assert vs.market is market


# ---------------------------------------------------------------------------
# Tests: screen() method
# ---------------------------------------------------------------------------

class TestValueScreenerScreen:
    @pytest.fixture(autouse=True)
    def _suppress_deprecation(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            yield

    def test_empty_symbols_returns_empty(self):
        """No symbols -> empty results."""
        market = _MockMarket(symbols=[])
        vs = ValueScreener(_MockYahooClient(), market)
        results = vs.screen()
        assert results == []

    def test_none_stock_info_skipped(self):
        """get_stock_info returns None -> stock skipped."""
        market = _MockMarket(symbols=["1001.T", "1002.T"])
        vs = ValueScreener(_MockYahooClient(stock_info=None), market)
        results = vs.screen()
        assert results == []

    def test_normal_screening(self):
        """Normal case: returns scored results."""
        info = _make_stock_info(per=8.0, pbr=0.7, roe=0.12, dividend_yield=0.035)
        market = _MockMarket(symbols=["1001.T"])
        vs = ValueScreener(_MockYahooClient(stock_info=info), market)
        results = vs.screen()
        assert len(results) == 1
        assert results[0]["symbol"] == "7203.T"  # from info dict
        assert "value_score" in results[0]
        assert results[0]["value_score"] > 0

    def test_result_fields(self):
        """Results contain expected fields."""
        info = _make_stock_info()
        market = _MockMarket(symbols=["1001.T"])
        vs = ValueScreener(_MockYahooClient(stock_info=info), market)
        results = vs.screen()
        assert len(results) == 1
        r = results[0]
        for key in ["symbol", "name", "price", "per", "pbr",
                     "dividend_yield", "dividend_yield_trailing",
                     "roe", "value_score"]:
            assert key in r

    def test_sorted_by_value_score_descending(self):
        """Results sorted by value_score descending."""
        def info_fn(symbol):
            scores = {
                "1001.T": _make_stock_info("1001.T", per=5, pbr=0.3, roe=0.20, dividend_yield=0.05),
                "1002.T": _make_stock_info("1002.T", per=20, pbr=2.0, roe=0.05, dividend_yield=0.01),
                "1003.T": _make_stock_info("1003.T", per=10, pbr=1.0, roe=0.10, dividend_yield=0.03),
            }
            return scores.get(symbol)

        market = _MockMarket(symbols=["1001.T", "1002.T", "1003.T"])
        vs = ValueScreener(_MockYahooClient(stock_info=info_fn), market)
        results = vs.screen()
        scores = [r["value_score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_respects_top_n(self):
        """Only top_n results returned."""
        info = _make_stock_info()
        market = _MockMarket(symbols=[f"{i}.T" for i in range(1001, 1021)])
        vs = ValueScreener(_MockYahooClient(stock_info=info), market)
        results = vs.screen(top_n=3)
        assert len(results) <= 3

    def test_custom_symbols_override(self):
        """symbols parameter overrides market defaults."""
        info = _make_stock_info("AAPL")
        market = _MockMarket(symbols=["7203.T"])
        vs = ValueScreener(_MockYahooClient(stock_info=info), market)
        results = vs.screen(symbols=["AAPL"])
        assert len(results) == 1

    def test_criteria_filter_applied(self):
        """Criteria filter excludes stocks that exceed thresholds."""
        info = _make_stock_info(per=20.0)  # PER=20 exceeds max_per=15
        market = _MockMarket(symbols=["1001.T"])
        vs = ValueScreener(_MockYahooClient(stock_info=info), market)
        results = vs.screen(criteria={"max_per": 15})
        assert results == []

    def test_criteria_filter_passes(self):
        """Criteria filter allows stocks within thresholds."""
        info = _make_stock_info(per=10.0)  # PER=10 within max_per=15
        market = _MockMarket(symbols=["1001.T"])
        vs = ValueScreener(_MockYahooClient(stock_info=info), market)
        results = vs.screen(criteria={"max_per": 15})
        assert len(results) == 1

    def test_preset_loads_criteria(self):
        """preset parameter loads criteria from YAML."""
        info = _make_stock_info(per=8.0, pbr=0.7, roe=0.10)
        market = _MockMarket(symbols=["1001.T"])
        vs = ValueScreener(_MockYahooClient(stock_info=info), market)
        # "value" preset exists in config/screening_presets.yaml
        results = vs.screen(preset="value")
        assert isinstance(results, list)

    def test_explicit_criteria_overrides_preset(self):
        """Explicit criteria takes priority over preset."""
        info = _make_stock_info(per=20.0)
        market = _MockMarket(symbols=["1001.T"])
        vs = ValueScreener(_MockYahooClient(stock_info=info), market)
        # Explicit criteria with max_per=25 should pass (ignoring preset)
        results = vs.screen(criteria={"max_per": 25}, preset="value")
        assert len(results) == 1

    def test_no_criteria_no_preset_no_filter(self):
        """No criteria and no preset -> all stocks pass filter."""
        info = _make_stock_info(per=100.0)  # Very high PER
        market = _MockMarket(symbols=["1001.T"])
        vs = ValueScreener(_MockYahooClient(stock_info=info), market)
        results = vs.screen()  # No criteria, no preset
        assert len(results) == 1

    def test_thresholds_passed_to_value_score(self):
        """Market thresholds are passed to calculate_value_score."""
        info = _make_stock_info()
        market = _MockMarket(
            symbols=["1001.T"],
            thresholds={"target_per": 10, "target_pbr": 1.0},
        )
        vs = ValueScreener(_MockYahooClient(stock_info=info), market)
        results = vs.screen()
        assert len(results) == 1
        assert "value_score" in results[0]
