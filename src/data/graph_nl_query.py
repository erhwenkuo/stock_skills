"""Backward-compatible shim (KIK-517). Real module: src.data.graph_query.nl_query"""
import warnings as _warnings
_warnings.warn(
    "Import from the subpackage directly (e.g., src.data.graph_query.nl_query)",
    DeprecationWarning,
    stacklevel=2,
)

import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("src.data.graph_query.nl_query")
