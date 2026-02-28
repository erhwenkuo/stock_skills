"""Backward-compatible re-export of screener classes and registry (KIK-422, KIK-514).

Each screener class has been moved to its own module (KIK-422).
This module re-exports all classes so that existing import paths
(``from src.core.screening.screener import QueryScreener``) continue to work.

KIK-514 adds ScreenerRegistry and RegionConfig for OCP-compliant dispatch.
"""

from src.core.screening.alpha_screener import AlphaScreener
from src.core.screening.contrarian_screener import ContrarianScreener
from src.core.screening.growth_screener import GrowthScreener
from src.core.screening.momentum_screener import MomentumScreener
from src.core.screening.pullback_screener import PullbackScreener
from src.core.screening.query_screener import QueryScreener
from src.core.screening.screener_registry import (
    ScreenerSpec,
    ScreenerRegistry,
    RegionConfig,
    build_default_registry,
    run_screener_with_spec,
)
from src.core.screening.trending_screener import TrendingScreener
from src.core.screening.value_screener import ValueScreener

__all__ = [
    "ValueScreener",
    "QueryScreener",
    "PullbackScreener",
    "AlphaScreener",
    "GrowthScreener",
    "TrendingScreener",
    "ContrarianScreener",
    "MomentumScreener",
    "ScreenerSpec",
    "ScreenerRegistry",
    "RegionConfig",
    "build_default_registry",
    "run_screener_with_spec",
]
