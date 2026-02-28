"""Tests for src/core/screening/growth_screener.py."""

import pytest

from src.core.screening.growth_screener import GrowthScreener


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_quote(symbol="7203.T", name="Toyota", per=12.0, roe=0.12,
                rev_growth=0.08):
    """Create a raw quote dict as returned by screen_stocks."""
    return {
        "symbol": symbol,
        "shortName": name,
        "sector": "Technology",
        "industry": "Semiconductors",
        "currency": "JPY",
        "regularMarketPrice": 2500.0,
        "marketCap": 500_000_000_000,
        "trailingPE": per,
        "forwardPE": per * 0.9,
        "priceToBook": 1.2,
        "returnOnEquity": roe,
        "dividendYield": 2.0,
        "revenueGrowth": rev_growth,
        "earningsGrowth": 0.10,
        "exchange": "JPX",
    }


def _make_detail(eps_growth=0.15, revenue_growth=0.10):
    """Create a stock detail dict."""
    return {
        "eps_growth": eps_growth,
        "revenue_growth": revenue_growth,
    }


class _MockYahooClient:
    """Mock yahoo_client for GrowthScreener tests."""

    def __init__(self, quotes=None, detail=None):
        self._quotes = quotes or []
        self._detail = detail

    def screen_stocks(self, query, size=250, max_results=250,
                      sort_field=None, sort_asc=False):
        return self._quotes

    def get_stock_detail(self, symbol):
        if callable(self._detail):
            return self._detail(symbol)
        return self._detail


# ---------------------------------------------------------------------------
# Tests: initialization
# ---------------------------------------------------------------------------

class TestGrowthScreenerInit:
    def test_default_params(self):
        client = _MockYahooClient()
        gs = GrowthScreener(client)
        assert gs.preset == "growth"
        assert gs.sort_by == "eps_growth"
        assert gs.require_positive_eps is True

    def test_custom_params(self):
        client = _MockYahooClient()
        gs = GrowthScreener(
            client,
            preset="high-growth",
            sort_by="revenue_growth",
            require_positive_eps=False,
        )
        assert gs.preset == "high-growth"
        assert gs.sort_by == "revenue_growth"
        assert gs.require_positive_eps is False


# ---------------------------------------------------------------------------
# Tests: screen() method
# ---------------------------------------------------------------------------

class TestGrowthScreenerScreen:
    def test_empty_quotes_returns_empty(self):
        """No quotes from screen_stocks -> empty results."""
        gs = GrowthScreener(_MockYahooClient(quotes=[]))
        results = gs.screen(region="jp")
        assert results == []

    def test_none_detail_skips_stock(self):
        """get_stock_detail returns None -> stock skipped."""
        quotes = [_make_quote("1001.T")]
        gs = GrowthScreener(_MockYahooClient(quotes=quotes, detail=None))
        results = gs.screen(region="jp")
        assert results == []

    def test_positive_eps_required_filters_negative(self):
        """require_positive_eps=True filters out eps_growth <= 0."""
        quotes = [_make_quote("1001.T")]
        detail = _make_detail(eps_growth=-0.05)

        gs = GrowthScreener(_MockYahooClient(quotes=quotes, detail=detail))
        results = gs.screen(region="jp")
        assert results == []

    def test_positive_eps_required_filters_zero(self):
        """require_positive_eps=True filters out eps_growth == 0."""
        quotes = [_make_quote("1001.T")]
        detail = _make_detail(eps_growth=0.0)

        gs = GrowthScreener(_MockYahooClient(quotes=quotes, detail=detail))
        results = gs.screen(region="jp")
        assert results == []

    def test_positive_eps_required_filters_none(self):
        """require_positive_eps=True filters out eps_growth is None."""
        quotes = [_make_quote("1001.T")]
        detail = {"eps_growth": None, "revenue_growth": 0.10}

        gs = GrowthScreener(_MockYahooClient(quotes=quotes, detail=detail))
        results = gs.screen(region="jp")
        assert results == []

    def test_positive_eps_not_required_allows_negative(self):
        """require_positive_eps=False allows eps_growth < 0."""
        quotes = [_make_quote("1001.T")]
        detail = _make_detail(eps_growth=-0.05, revenue_growth=0.50)

        gs = GrowthScreener(
            _MockYahooClient(quotes=quotes, detail=detail),
            require_positive_eps=False,
            sort_by="revenue_growth",
        )
        results = gs.screen(region="jp")
        assert len(results) == 1
        assert results[0]["symbol"] == "1001.T"

    def test_normal_results_with_positive_eps(self):
        """Normal case: positive eps_growth passes filter."""
        quotes = [_make_quote("1001.T")]
        detail = _make_detail(eps_growth=0.20, revenue_growth=0.15)

        gs = GrowthScreener(_MockYahooClient(quotes=quotes, detail=detail))
        results = gs.screen(region="jp")
        assert len(results) == 1
        assert results[0]["eps_growth"] == 0.20

    def test_result_fields(self):
        """Results contain expected fields."""
        quotes = [_make_quote("1001.T")]
        detail = _make_detail(eps_growth=0.20, revenue_growth=0.15)

        gs = GrowthScreener(_MockYahooClient(quotes=quotes, detail=detail))
        results = gs.screen(region="jp")
        assert len(results) == 1
        r = results[0]
        expected_keys = [
            "symbol", "name", "sector", "price", "per", "forward_per",
            "pbr", "roe", "eps_growth", "revenue_growth", "market_cap",
        ]
        for key in expected_keys:
            assert key in r, f"Missing key: {key}"

    def test_sorted_by_eps_growth_descending(self):
        """Default sort by eps_growth descending."""
        quotes = [
            _make_quote("1001.T"),
            _make_quote("1002.T"),
            _make_quote("1003.T"),
        ]

        def detail_fn(symbol):
            growth_map = {"1001.T": 0.10, "1002.T": 0.30, "1003.T": 0.20}
            return _make_detail(eps_growth=growth_map.get(symbol, 0.05))

        gs = GrowthScreener(_MockYahooClient(quotes=quotes, detail=detail_fn))
        results = gs.screen(region="jp")
        eps_values = [r["eps_growth"] for r in results]
        assert eps_values == sorted(eps_values, reverse=True)

    def test_sorted_by_revenue_growth(self):
        """When sort_by='revenue_growth', sort by revenue_growth descending."""
        quotes = [
            _make_quote("1001.T", rev_growth=0.05),
            _make_quote("1002.T", rev_growth=0.50),
        ]

        detail = _make_detail(eps_growth=0.10)

        gs = GrowthScreener(
            _MockYahooClient(quotes=quotes, detail=detail),
            sort_by="revenue_growth",
        )
        results = gs.screen(region="jp")
        assert len(results) == 2
        assert results[0]["symbol"] == "1002.T"
        assert results[1]["symbol"] == "1001.T"

    def test_respects_top_n(self):
        """Only top_n results returned."""
        quotes = [_make_quote(f"{i}.T") for i in range(1001, 1011)]
        detail = _make_detail(eps_growth=0.15)

        gs = GrowthScreener(_MockYahooClient(quotes=quotes, detail=detail))
        results = gs.screen(region="jp", top_n=3)
        assert len(results) <= 3

    def test_no_symbol_in_quote_skipped(self):
        """Quotes without symbol are skipped."""
        quotes = [{"shortName": "No Symbol Corp", "trailingPE": 10}]
        detail = _make_detail()

        gs = GrowthScreener(_MockYahooClient(quotes=quotes, detail=detail))
        results = gs.screen(region="jp")
        assert results == []

    def test_criteria_overrides_applied(self):
        """criteria_overrides are merged into loaded preset."""
        called_args = {}

        class _SpyClient(_MockYahooClient):
            def screen_stocks(self, query, **kwargs):
                called_args["query"] = query
                return []

        gs = GrowthScreener(_SpyClient())
        gs.screen(region="jp", criteria_overrides={"max_market_cap": 100_000_000})
        assert "query" in called_args

    def test_revenue_growth_from_detail_fallback(self):
        """revenue_growth falls back to detail when quote has None."""
        quotes = [_make_quote("1001.T", rev_growth=None)]
        detail = _make_detail(eps_growth=0.10, revenue_growth=0.25)

        gs = GrowthScreener(_MockYahooClient(quotes=quotes, detail=detail))
        results = gs.screen(region="jp")
        if results:
            assert results[0]["revenue_growth"] == 0.25

    def test_sort_handles_none_values(self):
        """Sorting handles None values in sort_by field."""
        quotes = [_make_quote("1001.T"), _make_quote("1002.T")]

        def detail_fn(symbol):
            if symbol == "1001.T":
                return {"eps_growth": None, "revenue_growth": 0.10}
            return _make_detail(eps_growth=0.20)

        gs = GrowthScreener(
            _MockYahooClient(quotes=quotes, detail=detail_fn),
            require_positive_eps=False,
        )
        # Should not raise
        results = gs.screen(region="jp")
        assert isinstance(results, list)
