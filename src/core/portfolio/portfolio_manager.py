"""Portfolio management core logic (KIK-342).

.. deprecated::
    This module is a re-export shim kept for backward compatibility.
    Import directly from ``portfolio_io`` or ``portfolio_query`` instead:

    - ``src.core.portfolio.portfolio_io``: CSV I/O and position operations
    - ``src.core.portfolio.portfolio_query``: Snapshot, analysis, and merge

Split in KIK-578.
"""

import warnings as _warnings

_warnings.warn(
    "Importing from src.core.portfolio.portfolio_manager is deprecated. "
    "Use src.core.portfolio.portfolio_io or src.core.portfolio.portfolio_query instead. "
    "(KIK-578)",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from the split modules for backward compatibility
from src.core.portfolio.portfolio_io import (  # noqa: F401, E402
    DEFAULT_CSV_PATH,
    CSV_COLUMNS,
    load_portfolio,
    save_portfolio,
    add_position,
    sell_position,
    get_performance_review,
)

from src.core.portfolio.portfolio_query import (  # noqa: F401, E402
    get_snapshot,
    get_structure_analysis,
    get_portfolio_shareholder_return,
    merge_positions,
)

# Re-export FX utilities for backward compatibility
from src.core.portfolio.fx_utils import (  # noqa: F401, E402
    FX_PAIRS as _FX_PAIRS,
    fx_symbol_for_currency as _fx_symbol_for_currency,
    get_fx_rates,
    get_rate as _get_fx_rate_for_currency,
)

# Re-export private names that may be referenced externally
from src.core.common import is_cash as _is_cash  # noqa: F401, E402
from src.core.ticker_utils import (  # noqa: F401, E402
    SUFFIX_TO_REGION as _SUFFIX_TO_COUNTRY,
    SUFFIX_TO_CURRENCY as _SUFFIX_TO_CURRENCY,
    cash_currency as _cash_currency,
    infer_country as _infer_country,
    infer_currency as _infer_currency,
)
