"""History store save functions — re-export shim (KIK-578).

.. deprecated::
    This module is a re-export shim kept for backward compatibility.
    Import directly from the sub-modules instead:

    - ``save_screen``: save_screening
    - ``save_report``: save_report
    - ``save_trade``: save_trade
    - ``save_health``: save_health
    - ``save_research``: save_research, save_market_context, _build_research_summary
    - ``save_misc``: save_stress_test, save_forecast
"""

import warnings as _warnings

_warnings.warn(
    "Importing from src.data.history.save is deprecated. "
    "Use the sub-modules (save_screen, save_report, save_trade, "
    "save_health, save_research, save_misc) instead. (KIK-578)",
    DeprecationWarning,
    stacklevel=2,
)

from src.data.history.save_screen import save_screening  # noqa: F401, E402
from src.data.history.save_report import save_report  # noqa: F401, E402
from src.data.history.save_trade import save_trade  # noqa: F401, E402
from src.data.history.save_health import save_health  # noqa: F401, E402
from src.data.history.save_research import (  # noqa: F401, E402
    _build_research_summary,
    save_research,
    save_market_context,
)
from src.data.history.save_misc import (  # noqa: F401, E402
    save_stress_test,
    save_forecast,
)
from src.data.history._helpers import (  # noqa: F401, E402
    _dual_write_graph,
    _history_dir,
    _sanitize,
    _safe_filename,
    _build_embedding,
)
