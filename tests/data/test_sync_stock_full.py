"""Tests for sync_stock_full and save_trade stock_info enrichment (KIK-555)."""

import pytest
from unittest.mock import MagicMock, patch, call

pytestmark = pytest.mark.no_auto_mock


@pytest.fixture(autouse=True)
def reset_driver():
    import src.data.graph_store as gs
    gs._driver = None
    yield
    gs._driver = None


@pytest.fixture
def mock_driver():
    driver = MagicMock()
    session = MagicMock()
    driver.session.return_value.__enter__ = MagicMock(return_value=session)
    driver.session.return_value.__exit__ = MagicMock(return_value=False)
    return driver, session


@pytest.fixture
def gs_with_driver(mock_driver):
    import src.data.graph_store as gs
    driver, session = mock_driver
    gs._driver = driver
    return gs, driver, session


class TestSyncStockFull:
    def test_mode_off_returns_default(self, gs_with_driver):
        gs, _, _ = gs_with_driver
        with patch("src.data.graph_store._get_mode", return_value="off"):
            result = gs.sync_stock_full("7203.T")
        assert result["stock"] is False
        assert result["trades"] == 0

    def test_enriches_stock_metadata(self, gs_with_driver):
        gs, _, session = gs_with_driver

        mock_info = {"name": "Toyota", "sector": "Industrials", "country": "Japan"}
        mock_client = MagicMock()
        mock_client.get_stock_info.return_value = mock_info

        with patch("src.data.graph_store._get_mode", return_value="full"):
            result = gs.sync_stock_full("7203.T", client=mock_client)

        assert result["stock"] is True
        # merge_stock should have been called with metadata
        merge_calls = [c for c in session.run.call_args_list
                       if "Stock" in str(c) and "sector" in str(c)]
        assert len(merge_calls) > 0

    def test_returns_result_dict(self, gs_with_driver):
        gs, _, _ = gs_with_driver
        mock_client = MagicMock()
        mock_client.get_stock_info.return_value = {"name": "X", "sector": "Tech", "country": "US"}

        with patch("src.data.graph_store._get_mode", return_value="full"):
            result = gs.sync_stock_full("AAPL", client=mock_client)

        assert "stock" in result
        assert "trades" in result
        assert "community" in result

    def test_graceful_on_yfinance_error(self, gs_with_driver):
        gs, _, _ = gs_with_driver
        mock_client = MagicMock()
        mock_client.get_stock_info.side_effect = Exception("API error")

        with patch("src.data.graph_store._get_mode", return_value="full"):
            result = gs.sync_stock_full("BAD", client=mock_client)

        # Should not crash
        assert result["stock"] is False


class TestSaveTradeStockInfo:
    """Test that save_trade enriches Stock metadata via stock_info param."""

    def test_stock_info_passed_to_merge_stock(self, tmp_path):
        """When stock_info is provided, merge_stock gets metadata."""
        from src.data.history.save import save_trade

        stock_info = {"name": "Toyota", "sector": "Industrials", "country": "Japan"}

        with patch("src.data.history.save._dual_write_graph") as mock_dw:
            save_trade(
                symbol="7203.T", trade_type="buy", shares=100,
                price=2850.0, currency="JPY", date_str="2026-03-19",
                base_dir=str(tmp_path),
                stock_info=stock_info,
            )

        # _dual_write_graph should have been called
        assert mock_dw.called

    def test_save_trade_backward_compatible(self, tmp_path):
        """save_trade without stock_info still works (backward compat)."""
        from src.data.history.save import save_trade

        with patch("src.data.history.save._dual_write_graph"):
            path = save_trade(
                symbol="AAPL", trade_type="buy", shares=10,
                price=250.0, currency="USD", date_str="2026-03-19",
                base_dir=str(tmp_path),
            )

        assert path.endswith(".json")


class TestCheckGraphSync:
    def test_check_sync_returns_issues(self):
        from scripts.check_graph_sync import check_sync

        driver = MagicMock()
        session = MagicMock()
        driver.session.return_value.__enter__ = MagicMock(return_value=session)
        driver.session.return_value.__exit__ = MagicMock(return_value=False)

        # Mock: Stock exists but no metadata, no trade, no HOLDS
        def mock_run(query, **kwargs):
            result = MagicMock()
            rec = MagicMock()
            if "s.name" in query:
                rec.__getitem__ = lambda s, k: {"name": "", "sector": "", "country": ""}[k]
                result.single.return_value = rec
            elif "count" in query:
                rec.__getitem__ = lambda s, k: {"cnt": 0}[k]
                result.single.return_value = rec
            return result

        session.run.side_effect = mock_run

        import src.data.graph_store as gs
        gs._driver = driver

        with patch("scripts.check_graph_sync._load_portfolio_symbols", return_value=["TEST.T"]):
            issues = check_sync()

        assert len(issues) == 1
        assert issues[0]["symbol"] == "TEST.T"
        assert "Stock metadata empty" in issues[0]["issues"]
        gs._driver = None

    def test_check_sync_no_driver(self):
        from scripts.check_graph_sync import check_sync

        with patch("scripts.check_graph_sync._get_driver", return_value=None):
            assert check_sync() == []
