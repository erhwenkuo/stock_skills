"""Backward-compatible shim (KIK-517). Real module: src.data.context.screening_context"""
import warnings as _warnings
_warnings.warn(
    "Import from the subpackage directly (e.g., src.data.context.screening_context)",
    DeprecationWarning,
    stacklevel=2,
)

import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("src.data.context.screening_context")
