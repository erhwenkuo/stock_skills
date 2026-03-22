"""History store -- save and load screening/report/trade/health/research JSON files.

Sub-modules (KIK-512 split, KIK-517 package, KIK-578 save split):
  _helpers.py: Internal helpers (_sanitize, _build_embedding, _dual_write_graph)
  save_screen.py: save_screening
  save_report.py: save_report
  save_trade.py: save_trade
  save_health.py: save_health
  save_research.py: save_research, save_market_context, _build_research_summary
  save_misc.py: save_stress_test, save_forecast
  save.py: Re-export shim (deprecated, KIK-578)
  load.py: load_history, list_history_files

All public functions are re-exported here for backward compatibility.
"""

__all__ = [
    "Path",
    "_safe_filename", "_history_dir", "_HistoryEncoder",
    "_sanitize", "_build_embedding", "_dual_write_graph",
    "save_screening", "save_report", "save_trade", "save_health",
    "_build_research_summary", "save_research", "save_market_context",
    "save_stress_test", "save_forecast",
    "load_history", "list_history_files",
]

# Re-export Path for backward compat (tests may patch src.data.history_store.Path)
from pathlib import Path  # noqa: F401

# Re-export helpers (used by note_manager, manage_watchlist, backfill_embeddings)
from src.data.history._helpers import (  # noqa: F401
    _safe_filename,
    _history_dir,
    _HistoryEncoder,
    _sanitize,
    _build_embedding,
    _dual_write_graph,
)

# Re-export save functions from split sub-modules (KIK-578)
from src.data.history.save_screen import save_screening  # noqa: F401
from src.data.history.save_report import save_report  # noqa: F401
from src.data.history.save_trade import save_trade  # noqa: F401
from src.data.history.save_health import save_health  # noqa: F401
from src.data.history.save_research import (  # noqa: F401
    _build_research_summary,
    save_research,
    save_market_context,
)
from src.data.history.save_misc import (  # noqa: F401
    save_stress_test,
    save_forecast,
)

# Re-export load functions
from src.data.history.load import (  # noqa: F401
    load_history,
    list_history_files,
)
