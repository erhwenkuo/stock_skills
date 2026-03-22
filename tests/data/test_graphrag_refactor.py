"""Tests for KIK-573 GraphRAG schema refactoring."""

import pytest
from unittest.mock import MagicMock, patch

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


# ===================================================================
# P4: get_stock_history single query
# ===================================================================


class TestGetStockHistorySingleQuery:
    def test_returns_all_keys(self, gs_with_driver):
        gs, _, session = gs_with_driver
        record = MagicMock()
        record.__getitem__ = lambda s, k: {
            "screens": [], "reports": [], "trades": [],
            "health_checks": [], "notes": [], "themes": [],
            "researches": [],
        }[k]
        session.run.return_value.single.return_value = record

        result = gs.get_stock_history("7203.T")
        for key in ["screens", "reports", "trades", "health_checks",
                     "notes", "themes", "researches"]:
            assert key in result

    def test_single_query_call(self, gs_with_driver):
        """Should use only 1 session.run() call instead of 7."""
        gs, _, session = gs_with_driver
        record = MagicMock()
        record.__getitem__ = lambda s, k: []
        session.run.return_value.single.return_value = record

        gs.get_stock_history("TEST")
        assert session.run.call_count == 1

    def test_no_driver_returns_empty(self):
        import src.data.graph_store as gs
        with patch("src.data.graph_store._get_driver", return_value=None):
            result = gs.get_stock_history("7203.T")
        assert result["screens"] == []

    def test_null_record_returns_empty(self, gs_with_driver):
        gs, _, session = gs_with_driver
        session.run.return_value.single.return_value = None
        result = gs.get_stock_history("UNKNOWN")
        assert result["screens"] == []

    def test_filters_null_entries(self, gs_with_driver):
        gs, _, session = gs_with_driver
        record = MagicMock()
        record.__getitem__ = lambda s, k: {
            "screens": [
                {"date": "2026-03-01", "preset": "alpha", "region": "japan"},
                {"date": None, "preset": None, "region": None},
            ],
            "reports": [], "trades": [], "health_checks": [],
            "notes": [], "themes": [None, "AI"], "researches": [],
        }[k]
        session.run.return_value.single.return_value = record

        result = gs.get_stock_history("7203.T")
        assert len(result["screens"]) == 1
        assert result["themes"] == ["AI"]


# ===================================================================
# P5: vector_search single session
# ===================================================================


class TestVectorSearchSingleSession:
    def test_uses_single_session(self, gs_with_driver):
        gs, driver, session = gs_with_driver
        session.run.return_value = iter([])

        from src.data.graph_query.portfolio import vector_search
        vector_search([0.1] * 384, top_k=3)
        assert driver.session.call_count == 1

    def test_returns_empty_no_driver(self):
        from src.data.graph_query.portfolio import vector_search
        with patch("src.data.graph_store._get_driver", return_value=None):
            assert vector_search([0.1] * 384) == []


# ===================================================================
# P3/P6: Cleanup script
# ===================================================================


class TestCleanupExpired:
    def test_counts_expired(self, gs_with_driver):
        from scripts.cleanup_expired_nodes import cleanup_expired
        _, _, session = gs_with_driver

        rec = MagicMock()
        rec.__getitem__ = lambda s, k: {"cnt": 5}[k]
        result_mock = MagicMock()
        result_mock.single.return_value = rec
        session.run.return_value = result_mock

        stats = cleanup_expired(ttl_days=30, dry_run=True)
        assert stats["upcoming_events"] == 5
        assert stats["sector_rotations"] == 5

    def test_no_driver(self):
        from scripts.cleanup_expired_nodes import cleanup_expired
        with patch("scripts.cleanup_expired_nodes._get_driver", return_value=None):
            assert cleanup_expired() == {"upcoming_events": 0, "sector_rotations": 0}


class TestCleanupOrphans:
    def test_counts_orphans(self, gs_with_driver):
        from scripts.cleanup_expired_nodes import cleanup_orphans
        _, _, session = gs_with_driver

        rec = MagicMock()
        rec.__getitem__ = lambda s, k: {"cnt": 2}[k]
        result_mock = MagicMock()
        result_mock.single.return_value = rec
        session.run.return_value = result_mock

        stats = cleanup_orphans(dry_run=True)
        assert stats["orphan_notes"] == 2
        assert stats["orphan_stocks"] == 2

    def test_no_driver(self):
        from scripts.cleanup_expired_nodes import cleanup_orphans
        with patch("scripts.cleanup_expired_nodes._get_driver", return_value=None):
            assert cleanup_orphans() == {"orphan_notes": 0, "orphan_stocks": 0}
