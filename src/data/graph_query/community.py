"""Community detection via co-occurrence analysis (KIK-547).

.. deprecated::
    This module is a re-export shim kept for backward compatibility.
    Import directly from the sub-modules instead:

    - ``community_detect``: detect_communities, discover_hidden_themes,
      label_community, _auto_name_community, _fetch_cooccurrence_vectors,
      _compute_jaccard_similarity, _run_louvain, _extract_news_keyword,
      _save_communities, _jaccard_single
    - ``community_query``: get_communities, get_stock_community,
      get_similar_stocks, update_stock_community, get_community_lessons

Split in KIK-578.
"""

import warnings as _warnings

_warnings.warn(
    "Importing from src.data.graph_query.community is deprecated. "
    "Use community_detect or community_query instead. (KIK-578)",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export detection functions
from src.data.graph_query.community_detect import (  # noqa: F401, E402
    _DEFAULT_WEIGHTS,
    _HAS_NETWORKX,
    detect_communities,
    discover_hidden_themes,
    label_community,
    _auto_name_community,
    _fetch_cooccurrence_vectors,
    _jaccard_single,
    _compute_jaccard_similarity,
    _run_louvain,
    _extract_news_keyword,
    _save_communities,
)

# Re-export query functions
from src.data.graph_query.community_query import (  # noqa: F401, E402
    get_communities,
    get_stock_community,
    get_similar_stocks,
    update_stock_community,
    get_community_lessons,
)
