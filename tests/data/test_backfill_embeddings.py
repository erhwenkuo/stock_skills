"""Tests for scripts/backfill_embeddings.py (KIK-492)."""

from unittest.mock import MagicMock, patch, call

import pytest

from scripts.backfill_embeddings import _rebuild_summary, backfill, NODE_TYPES


# ---------------------------------------------------------------------------
# _rebuild_summary tests
# ---------------------------------------------------------------------------

class TestRebuildSummary:
    """Test _rebuild_summary dispatches to correct summary_builder function."""

    @patch("scripts.backfill_embeddings.summary_builder")
    def test_screen_summary(self, mock_sb):
        mock_sb.build_screen_summary.return_value = "screen summary"
        result = _rebuild_summary("Screen", {"date": "2026-01-01", "preset": "alpha", "region": "japan"})
        assert result == "screen summary"
        mock_sb.build_screen_summary.assert_called_once_with("2026-01-01", "alpha", "japan", [])

    @patch("scripts.backfill_embeddings.summary_builder")
    def test_report_summary(self, mock_sb):
        mock_sb.build_report_summary.return_value = "report summary"
        result = _rebuild_summary("Report", {
            "symbol": "7203.T", "name": "Toyota", "score": 75.0,
            "verdict": "割安", "sector": "Auto",
        })
        assert result == "report summary"
        mock_sb.build_report_summary.assert_called_once_with("7203.T", "Toyota", 75.0, "割安", "Auto")

    @patch("scripts.backfill_embeddings.summary_builder")
    def test_trade_summary(self, mock_sb):
        mock_sb.build_trade_summary.return_value = "trade summary"
        result = _rebuild_summary("Trade", {
            "date": "2026-02-01", "type": "buy", "symbol": "AAPL",
            "shares": 10, "memo": "good price",
        })
        assert result == "trade summary"
        mock_sb.build_trade_summary.assert_called_once_with("2026-02-01", "buy", "AAPL", 10, "good price")

    @patch("scripts.backfill_embeddings.summary_builder")
    def test_health_summary(self, mock_sb):
        mock_sb.build_health_summary.return_value = "health summary"
        result = _rebuild_summary("HealthCheck", {
            "date": "2026-02-01", "total": 5, "healthy": 3, "exit_count": 1,
        })
        assert result == "health summary"

    @patch("scripts.backfill_embeddings.summary_builder")
    def test_research_summary(self, mock_sb):
        mock_sb.build_research_summary.return_value = "research summary"
        result = _rebuild_summary("Research", {
            "research_type": "stock", "target": "NVDA", "summary": "test",
        })
        assert result == "research summary"

    @patch("scripts.backfill_embeddings.summary_builder")
    def test_market_context_summary(self, mock_sb):
        mock_sb.build_market_context_summary.return_value = "market summary"
        result = _rebuild_summary("MarketContext", {"date": "2026-02-01"})
        assert result == "market summary"

    @patch("scripts.backfill_embeddings.summary_builder")
    def test_note_summary(self, mock_sb):
        mock_sb.build_note_summary.return_value = "note summary"
        result = _rebuild_summary("Note", {
            "symbol": "7203.T", "type": "thesis", "content": "bullish",
        })
        assert result == "note summary"

    @patch("scripts.backfill_embeddings.summary_builder")
    def test_watchlist_summary(self, mock_sb):
        mock_sb.build_watchlist_summary.return_value = "watchlist summary"
        result = _rebuild_summary("Watchlist", {"name": "tech-stocks"})
        assert result == "watchlist summary"

    @patch("scripts.backfill_embeddings.summary_builder")
    def test_stress_test_summary(self, mock_sb):
        mock_sb.build_stress_test_summary.return_value = "stress summary"
        result = _rebuild_summary("StressTest", {
            "date": "2026-02-01", "scenario": "crash",
            "portfolio_impact": -15.5, "symbol_count": 3,
        })
        assert result == "stress summary"

    @patch("scripts.backfill_embeddings.summary_builder")
    def test_forecast_summary(self, mock_sb):
        mock_sb.build_forecast_summary.return_value = "forecast summary"
        result = _rebuild_summary("Forecast", {
            "date": "2026-02-01", "optimistic": 20.0,
            "base": 10.0, "pessimistic": -5.0, "symbol_count": 5,
        })
        assert result == "forecast summary"

    @patch("scripts.backfill_embeddings.summary_builder")
    def test_unknown_label_returns_empty(self, mock_sb):
        result = _rebuild_summary("UnknownType", {})
        assert result == ""

    @patch("scripts.backfill_embeddings.summary_builder")
    def test_exception_returns_empty(self, mock_sb):
        mock_sb.build_screen_summary.side_effect = Exception("boom")
        result = _rebuild_summary("Screen", {})
        assert result == ""


# ---------------------------------------------------------------------------
# backfill() tests
# ---------------------------------------------------------------------------

class TestBackfill:
    """Test backfill function."""

    @patch("scripts.backfill_embeddings._get_driver")
    def test_no_driver_returns_empty(self, mock_driver):
        mock_driver.return_value = None
        result = backfill()
        assert result == {}

    @patch("scripts.backfill_embeddings.embedding_client")
    @patch("scripts.backfill_embeddings._get_driver")
    def test_no_missing_nodes(self, mock_driver_fn, mock_emb):
        """When all nodes have embeddings, returns empty stats."""
        mock_session = MagicMock()
        mock_session.run.return_value = []  # no missing nodes
        mock_driver = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
        mock_driver_fn.return_value = mock_driver

        result = backfill()
        assert result == {}

    @patch("scripts.backfill_embeddings.summary_builder")
    @patch("scripts.backfill_embeddings.embedding_client")
    @patch("scripts.backfill_embeddings._get_driver")
    def test_backfill_updates_nodes(self, mock_driver_fn, mock_emb, mock_sb):
        """Backfill should update nodes missing embeddings."""
        mock_emb.get_embedding.return_value = [0.1] * 384

        # Simulate one Report node missing embedding
        mock_record = MagicMock()
        mock_record.__getitem__ = lambda self, key: {
            "node_id": "report-001",
            "props": {"symbol": "7203.T", "name": "Toyota", "score": 75.0,
                      "verdict": "割安", "sector": "Auto",
                      "semantic_summary": "existing summary"},
        }[key]

        mock_session = MagicMock()
        # First call returns missing nodes, subsequent calls for other types return empty
        call_count = [0]

        def mock_run(query, **kwargs):
            if "Report" in query and "WHERE" in query and "IS NULL" in query:
                return [mock_record]
            if "SET" in query:
                return []
            return []

        mock_session.run.side_effect = mock_run
        mock_driver = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
        mock_driver_fn.return_value = mock_driver

        result = backfill()
        assert result.get("Report", 0) == 1

    @patch("scripts.backfill_embeddings.summary_builder")
    @patch("scripts.backfill_embeddings.embedding_client")
    @patch("scripts.backfill_embeddings._get_driver")
    def test_dry_run_no_writes(self, mock_driver_fn, mock_emb, mock_sb):
        """Dry run should not write to Neo4j."""
        mock_emb.get_embedding.return_value = [0.1] * 384
        mock_sb.build_screen_summary.return_value = "test summary"

        mock_record = MagicMock()
        mock_record.__getitem__ = lambda self, key: {
            "node_id": "screen-001",
            "props": {"date": "2026-01-01", "preset": "alpha", "region": "japan"},
        }[key]

        mock_session = MagicMock()

        def mock_run(query, **kwargs):
            if "Screen" in query and "IS NULL" in query:
                return [mock_record]
            return []

        mock_session.run.side_effect = mock_run
        mock_driver = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
        mock_driver_fn.return_value = mock_driver

        result = backfill(dry_run=True)
        assert result.get("Screen", 0) == 1
        # No SET queries should have been run
        for c in mock_session.run.call_args_list:
            assert "SET" not in str(c)

    @patch("scripts.backfill_embeddings.embedding_client")
    @patch("scripts.backfill_embeddings._get_driver")
    def test_tei_returns_none_skips(self, mock_driver_fn, mock_emb):
        """When TEI returns None for embedding, node should be skipped."""
        mock_emb.get_embedding.return_value = None

        mock_record = MagicMock()
        mock_record.__getitem__ = lambda self, key: {
            "node_id": "note-001",
            "props": {"symbol": "AAPL", "type": "thesis", "content": "bullish",
                      "semantic_summary": "existing summary"},
        }[key]

        mock_session = MagicMock()

        def mock_run(query, **kwargs):
            if "Note" in query and "IS NULL" in query:
                return [mock_record]
            return []

        mock_session.run.side_effect = mock_run
        mock_driver = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
        mock_driver_fn.return_value = mock_driver

        result = backfill()
        # No nodes updated because embedding was None
        assert result == {}


# ---------------------------------------------------------------------------
# _build_embedding WARNING log test (KIK-492)
# ---------------------------------------------------------------------------

class TestBuildEmbeddingWarning:
    """Test that _build_embedding logs warning when TEI unavailable."""

    @patch("src.data.embedding_client.get_embedding")
    @patch("src.data.summary_builder.build_screen_summary")
    def test_warning_logged_when_tei_unavailable(self, mock_build, mock_get_emb, caplog):
        """When TEI returns None for embedding, a WARNING should be logged."""
        from src.data.history_store import _build_embedding

        mock_build.return_value = "screen summary text"
        mock_get_emb.return_value = None

        import logging
        with caplog.at_level(logging.WARNING, logger="src.data.history_store"):
            text, emb = _build_embedding(
                "screen", date="2026-01-01", preset="alpha",
                region="japan", top_symbols=["7203.T"],
            )

        assert text == "screen summary text"
        assert emb is None
        assert "TEI unavailable" in caplog.text
        assert "backfill_embeddings" in caplog.text

    @patch("src.data.embedding_client.get_embedding")
    @patch("src.data.summary_builder.build_screen_summary")
    def test_no_warning_when_embedding_succeeds(self, mock_build, mock_get_emb, caplog):
        """When embedding succeeds, no warning should be logged."""
        from src.data.history_store import _build_embedding

        mock_build.return_value = "screen summary text"
        mock_get_emb.return_value = [0.1] * 384

        import logging
        with caplog.at_level(logging.WARNING, logger="src.data.history_store"):
            text, emb = _build_embedding(
                "screen", date="2026-01-01", preset="alpha",
                region="japan", top_symbols=["7203.T"],
            )

        assert text == "screen summary text"
        assert emb is not None
        assert "TEI unavailable" not in caplog.text

    @patch("src.data.embedding_client.get_embedding")
    @patch("src.data.summary_builder.build_screen_summary")
    def test_no_warning_when_empty_summary(self, mock_build, mock_get_emb, caplog):
        """When summary is empty, no warning should be logged (no embedding attempted)."""
        from src.data.history_store import _build_embedding

        mock_build.return_value = ""

        import logging
        with caplog.at_level(logging.WARNING, logger="src.data.history_store"):
            text, emb = _build_embedding(
                "screen", date="2026-01-01", preset="alpha",
                region="japan", top_symbols=[],
            )

        assert text == ""
        assert emb is None
        assert "TEI unavailable" not in caplog.text


class TestNodeTypes:
    """Verify NODE_TYPES covers all expected types."""

    def test_node_types_count(self):
        assert len(NODE_TYPES) == 10

    def test_all_expected_types_present(self):
        expected = {
            "Screen", "Report", "Trade", "HealthCheck", "Research",
            "MarketContext", "Note", "Watchlist", "StressTest", "Forecast",
        }
        assert set(NODE_TYPES) == expected
