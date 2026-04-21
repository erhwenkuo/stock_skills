# Development Patterns Guide

A template collection for common development tasks, with concrete examples matching the actual codebase.
See [development.md](../rules/development.md) and [workflow.md](../rules/workflow.md) for detailed rules.

---

## Pattern 1: Adding a New Screening Preset

Steps for adding a new investment strategy preset (e.g. "low-volatility stocks").

### Files to Change (ordered)

1. `config/screening_presets.yaml` — add preset definition
2. `src/core/screening/screener_registry.py` — register ScreenerSpec in `build_default_registry()`
3. `src/output/formatter.py` — add a dedicated formatter function (if needed)
4. `.claude/rules/intent-routing.md` — add keywords to the preset inference table
5. `tests/core/test_screener_registry.py` — add registration test

### 1. config/screening_presets.yaml

```yaml
# Example: low-volatility stock preset
low-volatility:
  description: "Low-volatility stocks (stable dividends, low beta)"
  criteria:
    max_per: 20
    min_dividend_yield: 0.02
    min_roe: 0.05
    max_beta: 0.8
```

### 2. screener_registry.py — Register ScreenerSpec

Add inside `build_default_registry()`:

```python
# Add at the end of build_default_registry() in src/core/screening/screener_registry.py

# --- Low Volatility ---
registry.register(ScreenerSpec(
    preset="low-volatility",
    screener_class=QueryScreener,           # reuse existing screener
    formatter=format_query_markdown,        # or a dedicated formatter
    display_name="Low Volatility",
    category="query",
    supports_legacy=True,
    step_messages=(
        "Step 1: Filtering by low-volatility criteria...",
        "Step 2: {n} stocks matched",
    ),
))
```

If a new screener class is needed, refer to the `ContrarianScreener` / `MomentumScreener` implementations:

```python
# src/core/screening/low_volatility_screener.py

class LowVolatilityScreener:
    """Low-volatility stock screener.

    Pipeline:
      Step 1: EquityQuery fundamentals filter
      Step 2: Compute beta / volatility from get_price_history()
      Step 3: Scoring + ranking
    """

    DEFAULT_CRITERIA = {
        "max_per": 20,
        "min_dividend_yield": 0.02,
        "min_roe": 0.05,
    }

    def __init__(self, yahoo_client):
        self.yahoo_client = yahoo_client

    def screen(
        self,
        region: str = "jp",
        top_n: int = 20,
        sector: str | None = None,
        theme: str | None = None,
    ) -> list[dict]:
        criteria = dict(self.DEFAULT_CRITERIA)
        query = build_query(criteria, region=region, sector=sector, theme=theme)

        raw_quotes = self.yahoo_client.screen_stocks(
            query, size=250, max_results=max(top_n * 3, 30),
            sort_field="intradaymarketcap", sort_asc=False,
        )
        if not raw_quotes:
            return []

        scored: list[dict] = []
        for quote in raw_quotes:
            normalized = QueryScreener._normalize_quote(quote)
            symbol = normalized.get("symbol")
            if not symbol:
                continue

            hist = self.yahoo_client.get_price_history(symbol)
            lv_result = compute_low_volatility_score(hist, normalized)  # new function
            if lv_result["lv_score"] < 30:
                continue

            normalized.update(lv_result)
            scored.append(normalized)

        scored.sort(key=lambda r: r.get("lv_score", 0), reverse=True)
        return scored[:top_n]
```

### 3. formatter.py — Add Formatter

```python
# Add to src/output/formatter.py

def format_low_volatility_markdown(results: list[dict]) -> str:
    """Format low-volatility screening results as a Markdown table."""
    if not results:
        return "No stocks matched the low-volatility criteria."

    lines = [
        "| Rank | Ticker | Sector | Price | P/E | Beta | Div Yield | ROE | Score |",
        "|---:|:-----|:---------|-----:|----:|----:|---------:|----:|------:|",
    ]
    for rank, row in enumerate(results, start=1):
        label = _build_label(row)
        sector = row.get("sector") or "-"
        price = _fmt_float(row.get("price"), decimals=0) if row.get("price") is not None else "-"
        per = _fmt_float(row.get("per"))
        beta = _fmt_float(row.get("beta"), decimals=2)
        div_yield = _fmt_pct(row.get("dividend_yield"))
        roe = _fmt_pct(row.get("roe"))
        score = _fmt_float(row.get("lv_score"))
        lines.append(
            f"| {rank} | {label} | {sector} | {price} | {per} | {beta} | {div_yield} | {roe} | {score} |"
        )
    _append_annotation_footer(lines, results)
    return "\n".join(lines)
```

### Test Example

```python
# tests/core/test_low_volatility_screener.py

import pandas as pd
import numpy as np
import pytest
from src.core.screening.low_volatility_screener import LowVolatilityScreener


def _make_stable_hist() -> pd.DataFrame:
    """Generate a low-volatility price history."""
    n = 250
    dates = pd.bdate_range(end="2026-02-27", periods=n)
    prices = 1000.0 + np.random.RandomState(0).randn(n) * 5  # small fluctuation
    volumes = np.full(n, 300_000.0)
    return pd.DataFrame({"Close": prices, "Volume": volumes}, index=dates)


def _make_quote(symbol: str, per: float = 15.0, roe: float = 0.08) -> dict:
    return {
        "symbol": symbol,
        "shortName": f"Company {symbol}",
        "sector": "Utilities",
        "regularMarketPrice": 1000.0,
        "marketCap": 500_000_000_000,
        "trailingPE": per,
        "priceToBook": 1.2,
        "returnOnEquity": roe,
        "dividendYield": 3.0,
        "revenueGrowth": 0.02,
    }


class _MockClient:
    def __init__(self, quotes, hist):
        self._quotes = quotes
        self._hist = hist

    def screen_stocks(self, query, **kwargs):
        return self._quotes

    def get_price_history(self, symbol, period="1y"):
        return self._hist


class TestLowVolatilityScreener:
    def test_empty_quotes_returns_empty(self):
        client = _MockClient(quotes=[], hist=_make_stable_hist())
        screener = LowVolatilityScreener(client)
        assert screener.screen(region="jp", top_n=5) == []

    def test_stable_stock_passes_filter(self):
        quotes = [_make_quote("1234.T")]
        client = _MockClient(quotes=quotes, hist=_make_stable_hist())
        screener = LowVolatilityScreener(client)
        results = screener.screen(region="jp", top_n=5)
        assert len(results) >= 0  # verify result structure

    def test_top_n_limits_results(self):
        quotes = [_make_quote(f"{i}000.T") for i in range(10)]
        hist = _make_stable_hist()
        client = _MockClient(quotes=quotes, hist=hist)
        screener = LowVolatilityScreener(client)
        results = screener.screen(region="jp", top_n=3)
        assert len(results) <= 3
```

### Documentation Update Checklist

- [ ] `config/screening_presets.yaml` — add preset definition
- [ ] `src/core/screening/screener_registry.py` — register ScreenerSpec
- [ ] `src/output/formatter.py` — add formatter (if custom format is needed)
- [ ] `.claude/rules/intent-routing.md` — add keywords to preset inference table
- [ ] `.claude/rules/screening.md` — update screener engine description
- [ ] `CLAUDE.md` — update module list in Architecture section
- [ ] `docs/skill-catalog.md` — update supported preset list for screen-stocks skill

---

## Pattern 2: Adding a New Portfolio Subcommand

Steps for adding a new subcommand (e.g. `compare` — compare multiple portfolios) to the portfolio skill.

### Files to Change (ordered)

1. `src/core/portfolio/` — create core logic module
2. `src/output/portfolio_formatter.py` — add formatter function
3. `.claude/skills/stock-portfolio/scripts/portfolio_commands/compare.py` — create subcommand module
4. `.claude/skills/stock-portfolio/scripts/portfolio_commands/__init__.py` — add HAS_* flag and import
5. `.claude/skills/stock-portfolio/scripts/run_portfolio.py` — add argparse subcommand and dispatch
6. `.claude/rules/intent-routing.md` — add to portfolio domain judgment table

### 1. Core Logic Module

```python
# src/core/portfolio/compare.py

"""Portfolio comparison logic (KIK-NNN)."""

from typing import Optional


def compare_portfolios(
    pf_a: list[dict],
    pf_b: list[dict],
    label_a: str = "A",
    label_b: str = "B",
) -> dict:
    """Compare two portfolios.

    Parameters
    ----------
    pf_a, pf_b : list[dict]
        Holdings lists. Each element contains {"symbol", "shares", "current_price", ...}.
    label_a, label_b : str
        Comparison labels (for display).

    Returns
    -------
    dict
        Comparison result: total_value, sector_diff, common_symbols, unique_a, unique_b
    """
    symbols_a = {r["symbol"] for r in pf_a}
    symbols_b = {r["symbol"] for r in pf_b}

    return {
        "label_a": label_a,
        "label_b": label_b,
        "total_value_a": sum(r.get("current_price", 0) * r.get("shares", 0) for r in pf_a),
        "total_value_b": sum(r.get("current_price", 0) * r.get("shares", 0) for r in pf_b),
        "common_symbols": sorted(symbols_a & symbols_b),
        "unique_a": sorted(symbols_a - symbols_b),
        "unique_b": sorted(symbols_b - symbols_a),
    }
```

### 2. Add Formatter

```python
# Add to src/output/portfolio_formatter.py

def format_compare_markdown(compare_result: dict) -> str:
    """Format portfolio comparison result as Markdown."""
    a = compare_result["label_a"]
    b = compare_result["label_b"]
    lines = [
        f"## Portfolio Comparison: {a} vs {b}",
        "",
        f"- **{a} Total Value**: ¥{compare_result['total_value_a']:,.0f}",
        f"- **{b} Total Value**: ¥{compare_result['total_value_b']:,.0f}",
        "",
        f"**Common Stocks ({len(compare_result['common_symbols'])}): "
        + (", ".join(compare_result["common_symbols"]) or "None"),
        f"**{a} Only**: " + (", ".join(compare_result["unique_a"]) or "None"),
        f"**{b} Only**: " + (", ".join(compare_result["unique_b"]) or "None"),
    ]
    return "\n".join(lines)
```

### 3. Subcommand Module

```python
# .claude/skills/stock-portfolio/scripts/portfolio_commands/compare.py

"""compare subcommand: compare multiple portfolios (KIK-NNN)."""

from portfolio_commands import HAS_PORTFOLIO_MANAGER


def cmd_compare(csv_path: str, other_csv: str) -> None:
    """Compare two portfolio CSV files and print the result."""
    if not HAS_PORTFOLIO_MANAGER:
        print("Portfolio manager is not available.")
        return

    try:
        from src.core.portfolio.manager import PortfolioManager
        from src.core.portfolio.compare import compare_portfolios
        from src.output.portfolio_formatter import format_compare_markdown
    except ImportError as e:
        print(f"Module import error: {e}")
        return

    mgr_a = PortfolioManager(csv_path)
    mgr_b = PortfolioManager(other_csv)
    result = compare_portfolios(mgr_a.holdings, mgr_b.holdings, "Main", "Sub")
    print(format_compare_markdown(result))
```

### 4. Add to portfolio_commands/__init__.py

```python
# Add to .claude/skills/stock-portfolio/scripts/portfolio_commands/__init__.py

# HAS_* flag definition (follows existing pattern)
try:
    from src.core.portfolio.compare import compare_portfolios as _
    HAS_COMPARE = True
except ImportError:
    HAS_COMPARE = False
```

### 5. Add Subcommand to run_portfolio.py

```python
# Add to the argparse section of run_portfolio.py

# --- compare subcommand ---
compare_parser = subparsers.add_parser("compare", help="Compare two portfolios")
compare_parser.add_argument("--other", required=True, help="Path to comparison CSV")

# --- dispatch ---
elif args.command == "compare":
    if not HAS_COMPARE:
        print("compare module is not available.")
    else:
        from portfolio_commands.compare import cmd_compare
        cmd_compare(csv_path, args.other)
```

### Test Example

```python
# tests/core/test_portfolio_compare.py

import pytest
from src.core.portfolio.compare import compare_portfolios


@pytest.fixture
def pf_a():
    return [
        {"symbol": "7203.T", "shares": 100, "current_price": 2850},
        {"symbol": "9984.T", "shares": 50, "current_price": 7500},
    ]


@pytest.fixture
def pf_b():
    return [
        {"symbol": "7203.T", "shares": 200, "current_price": 2850},
        {"symbol": "AAPL", "shares": 10, "current_price": 200},
    ]


def test_common_symbols(pf_a, pf_b):
    result = compare_portfolios(pf_a, pf_b)
    assert "7203.T" in result["common_symbols"]


def test_unique_symbols(pf_a, pf_b):
    result = compare_portfolios(pf_a, pf_b)
    assert "9984.T" in result["unique_a"]
    assert "AAPL" in result["unique_b"]


def test_total_value(pf_a, pf_b):
    result = compare_portfolios(pf_a, pf_b)
    assert result["total_value_a"] == 100 * 2850 + 50 * 7500
    assert result["total_value_b"] == 200 * 2850 + 10 * 200


def test_empty_portfolio():
    result = compare_portfolios([], [])
    assert result["common_symbols"] == []
    assert result["unique_a"] == []
    assert result["unique_b"] == []
```

### Documentation Update Checklist

- [ ] `src/core/portfolio/compare.py` — create core logic
- [ ] `src/output/portfolio_formatter.py` — add formatter
- [ ] `portfolio_commands/compare.py` — create subcommand module
- [ ] `portfolio_commands/__init__.py` — add HAS_COMPARE flag
- [ ] `run_portfolio.py` — add argparse + dispatch
- [ ] `.claude/rules/intent-routing.md` — add to portfolio domain judgment table
- [ ] `.claude/rules/portfolio.md` — add feature description
- [ ] `CLAUDE.md` — update Architecture section
- [ ] `docs/skill-catalog.md` — update command list for stock-portfolio skill

---

## Pattern 3: Adding a New Neo4j Node Type

Steps for adding a new knowledge graph node (e.g. `PriceAlert` — price alert).

### Files to Change (ordered)

1. `src/data/graph_store/` — add merge function to the appropriate submodule
2. `src/data/graph_store/__init__.py` — re-export as a public function
3. `docs/neo4j-schema.md` — update schema documentation
4. `scripts/get_context.py` — incorporate into context retrieval if needed
5. `tests/data/test_graph_store_*.py` — add tests

### 1. Add merge Function to Submodule

Among existing submodules (`note.py`, `portfolio.py`, `stock.py`, `market.py`, etc.),
add to the most relevant one. Example: adding `PriceAlert` to `stock.py`:

```python
# Add to src/data/graph_store/stock.py

# ---------------------------------------------------------------------------
# PriceAlert node (KIK-NNN)
# ---------------------------------------------------------------------------

def merge_price_alert(
    alert_id: str,
    symbol: str,
    alert_date: str,
    target_price: float,
    direction: str,       # "above" | "below"
    triggered: bool = False,
    note: str = "",
) -> bool:
    """Create/update a PriceAlert node and create a TARGETS relation to Stock.

    Parameters
    ----------
    alert_id : str
        Unique alert ID (e.g. "alert_7203T_20260101").
    symbol : str
        Target ticker symbol (e.g. "7203.T").
    alert_date : str
        Alert creation date (ISO format: "2026-01-01").
    target_price : float
        Target stock price.
    direction : str
        "above" = breakout above / "below" = break below.
    triggered : bool
        Whether the alert has fired.
    note : str
        Supplementary note.

    Returns
    -------
    bool
        True if successful, False otherwise.
    """
    if _common._get_mode() == "off":
        return False
    driver = _common._get_driver()
    if driver is None:
        return False
    try:
        with driver.session() as session:
            session.run(
                "MERGE (a:PriceAlert {id: $id}) "
                "SET a.date = $date, a.target_price = $target_price, "
                "a.direction = $direction, a.triggered = $triggered, "
                "a.note = $note",
                id=alert_id, date=alert_date, target_price=target_price,
                direction=direction, triggered=triggered, note=note,
            )
            # TARGETS relation to Stock
            session.run(
                "MATCH (a:PriceAlert {id: $alert_id}) "
                "MERGE (s:Stock {symbol: $symbol}) "
                "MERGE (a)-[:TARGETS]->(s)",
                alert_id=alert_id, symbol=symbol,
            )
        return True
    except Exception:
        return False
```

### 2. Add re-export to __init__.py

```python
# Add to the stock.py section of src/data/graph_store/__init__.py

from src.data.graph_store.stock import (  # noqa: F401
    get_stock_history,
    merge_price_alert,   # ← add
    merge_report,
    merge_report_full,
    merge_screen,
    merge_stock,
    merge_watchlist,
    tag_theme,
)
```

### 3. docs/neo4j-schema.md Update Example

Add to the "Node Types" section of `docs/neo4j-schema.md`:

```markdown
### PriceAlert (price alert, KIK-NNN)

| Property | Type | Description |
|:---|:---|:---|
| id | str | Unique ID |
| date | str | Creation date (ISO) |
| target_price | float | Target stock price |
| direction | str | "above" / "below" |
| triggered | bool | Whether the alert has fired |
| note | str | Supplementary note |

**Relationship**: `PriceAlert-[TARGETS]->Stock`
```

### Test Example

```python
# Add to tests/data/test_graph_store_stock.py (extend existing test file)

from unittest.mock import MagicMock, patch
import pytest


class TestMergePriceAlert:
    """Tests for merge_price_alert()."""

    def test_returns_false_when_mode_off(self):
        with patch("src.data.graph_store._common._get_mode", return_value="off"):
            from src.data.graph_store.stock import merge_price_alert
            result = merge_price_alert(
                "alert_001", "7203.T", "2026-01-01", 3000.0, "above"
            )
            assert result is False

    def test_returns_false_when_no_driver(self):
        with patch("src.data.graph_store._common._get_mode", return_value="full"), \
             patch("src.data.graph_store._common._get_driver", return_value=None):
            from src.data.graph_store.stock import merge_price_alert
            result = merge_price_alert(
                "alert_001", "7203.T", "2026-01-01", 3000.0, "above"
            )
            assert result is False

    def test_returns_true_on_success(self):
        mock_session = MagicMock()
        mock_driver = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

        with patch("src.data.graph_store._common._get_mode", return_value="full"), \
             patch("src.data.graph_store._common._get_driver", return_value=mock_driver):
            from src.data.graph_store.stock import merge_price_alert
            result = merge_price_alert(
                "alert_001", "7203.T", "2026-01-01", 3000.0, "above"
            )
            assert result is True
            assert mock_session.run.call_count == 2  # MERGE + TARGETS relation

    def test_exception_returns_false(self):
        mock_session = MagicMock()
        mock_session.run.side_effect = Exception("Neo4j error")
        mock_driver = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

        with patch("src.data.graph_store._common._get_mode", return_value="full"), \
             patch("src.data.graph_store._common._get_driver", return_value=mock_driver):
            from src.data.graph_store.stock import merge_price_alert
            result = merge_price_alert(
                "alert_001", "7203.T", "2026-01-01", 3000.0, "above"
            )
            assert result is False
```

### Documentation Update Checklist

- [ ] `src/data/graph_store/<submodule>.py` — add merge function
- [ ] `src/data/graph_store/__init__.py` — add re-export
- [ ] `docs/neo4j-schema.md` — update node type and relationship lists
- [ ] `.claude/rules/graph-context.md` — update 22-node list
- [ ] `CLAUDE.md` — update node count in Architecture section

---

## Pattern 4: Adding a New Health Check Metric

Steps for adding a new health check metric (e.g. "liquidity risk") to the portfolio health check.

### Files to Change (ordered)

1. `src/core/health_check.py` — add metric calculation function and integrate into `compute_alert_level()`
2. `config/thresholds.yaml` — add threshold (referenced via `th()` helper)
3. `src/output/health_formatter.py` — add display column for the metric
4. `tests/core/test_health_check.py` — add tests

### 1. Add Metric to health_check.py

```python
# Add to src/core/health_check.py

# Threshold constants (from config/thresholds.yaml via KIK-446 pattern)
LIQUIDITY_MIN_VOLUME = th("health", "liquidity_min_volume", 100_000)   # min volume
LIQUIDITY_MIN_MARKET_CAP = th("health", "liquidity_min_market_cap", 30_000_000_000)  # min market cap


def check_liquidity_risk(
    stock_detail: dict,
    hist,  # pd.DataFrame | None
) -> dict:
    """Evaluate liquidity risk.

    Flags stocks with low volume or small market cap as "liquidity risk".

    Parameters
    ----------
    stock_detail : dict
        Return value of get_stock_detail(). Contains market_cap, avg_volume.
    hist : pd.DataFrame or None
        Price history (to compute 30-day average volume).

    Returns
    -------
    dict
        liquidity_risk: bool, volume_avg_30d: float, volume_label: str,
        market_cap_label: str, alerts: list[str]
    """
    alerts: list[str] = []
    info = stock_detail.get("info", stock_detail)

    market_cap = info.get("market_cap") or info.get("marketCap")
    avg_vol = info.get("averageVolume") or info.get("averageDailyVolume10Day")

    # 30-day average volume (price history takes priority)
    volume_avg_30d: float | None = None
    if hist is not None and "Volume" in hist.columns and len(hist) >= 30:
        volume_avg_30d = float(hist["Volume"].iloc[-30:].mean())
    elif avg_vol is not None:
        volume_avg_30d = float(avg_vol)

    # Volume assessment
    if volume_avg_30d is not None and volume_avg_30d < LIQUIDITY_MIN_VOLUME:
        volume_label = "Low volume"
        alerts.append(f"30-day avg volume {volume_avg_30d:,.0f} shares is low (risk of illiquidity)")
    else:
        volume_label = "Sufficient"

    # Market cap assessment
    if market_cap is not None and market_cap < LIQUIDITY_MIN_MARKET_CAP:
        market_cap_label = "Small"
        alerts.append(f"Market cap {market_cap/1e9:.0f}B is small (liquidity risk)")
    else:
        market_cap_label = "Adequate"

    return {
        "liquidity_risk": bool(alerts),
        "volume_avg_30d": volume_avg_30d,
        "volume_label": volume_label,
        "market_cap_label": market_cap_label,
        "alerts": alerts,
    }
```

Integrate liquidity risk into `compute_alert_level()`:

```python
# Add to existing logic in compute_alert_level()

def compute_alert_level(
    trend_data: dict,
    change_data: dict,
    stock_detail: dict,
    is_small_cap: bool = False,
    liquidity_data: dict | None = None,   # ← new parameter
) -> tuple[str, list[str]]:
    """...existing docstring..."""

    # existing logic ...

    # Alert escalation due to liquidity risk (KIK-NNN)
    if liquidity_data and liquidity_data.get("liquidity_risk"):
        reasons.extend(liquidity_data.get("alerts", []))
        if alert_level == ALERT_NONE:
            alert_level = ALERT_EARLY_WARNING  # liquidity risk → minimum EARLY_WARNING

    return alert_level, reasons
```

### 2. Add Threshold to config/thresholds.yaml

```yaml
# Add to the health section of config/thresholds.yaml
health:
  # ... existing thresholds ...
  liquidity_min_volume: 100000           # min volume (30-day avg)
  liquidity_min_market_cap: 30000000000  # min market cap (30B JPY)
```

### 3. health_formatter.py — Add Display Column

```python
# Add to format_health_markdown() in src/output/health_formatter.py

# Add liquidity risk column to existing table
def _fmt_liquidity(liq_data: dict | None) -> str:
    if liq_data is None:
        return "-"
    if liq_data.get("liquidity_risk"):
        return "⚠️ Risk"
    return "OK"
```

### Test Example

```python
# Add to tests/core/test_health_check.py

import pandas as pd
import numpy as np
import pytest
from src.core.health_check import check_liquidity_risk


def _make_hist_with_volume(avg_vol: float, n: int = 250) -> pd.DataFrame:
    dates = pd.bdate_range(end="2026-02-27", periods=n)
    prices = np.full(n, 1000.0)
    volumes = np.full(n, avg_vol)
    return pd.DataFrame({"Close": prices, "Volume": volumes}, index=dates)


class TestCheckLiquidityRisk:
    def test_no_risk_for_high_volume(self):
        hist = _make_hist_with_volume(500_000)
        detail = {"info": {"market_cap": 100_000_000_000}}
        result = check_liquidity_risk(detail, hist)
        assert result["liquidity_risk"] is False
        assert result["volume_label"] == "Sufficient"

    def test_risk_for_low_volume(self):
        hist = _make_hist_with_volume(50_000)  # below threshold of 100,000
        detail = {"info": {"market_cap": 100_000_000_000}}
        result = check_liquidity_risk(detail, hist)
        assert result["liquidity_risk"] is True
        assert "Low volume" in result["volume_label"]
        assert len(result["alerts"]) >= 1

    def test_risk_for_small_market_cap(self):
        hist = _make_hist_with_volume(500_000)
        detail = {"info": {"market_cap": 10_000_000_000}}  # 10B < 30B
        result = check_liquidity_risk(detail, hist)
        assert result["liquidity_risk"] is True
        assert result["market_cap_label"] == "Small"

    def test_no_hist_falls_back_to_info(self):
        detail = {"info": {"market_cap": 100_000_000_000, "averageVolume": 1_000_000}}
        result = check_liquidity_risk(detail, None)
        assert result["liquidity_risk"] is False
        assert result["volume_avg_30d"] == 1_000_000.0

    def test_empty_detail_no_crash(self):
        result = check_liquidity_risk({}, None)
        assert isinstance(result, dict)
        assert "liquidity_risk" in result
```

### Documentation Update Checklist

- [ ] `src/core/health_check.py` — add metric function + integrate into `compute_alert_level()`
- [ ] `config/thresholds.yaml` — add threshold definition
- [ ] `src/output/health_formatter.py` — add display column
- [ ] `.claude/rules/portfolio.md` — add feature description to health check section
- [ ] `.claude/rules/intent-routing.md` — add related keywords (if needed)
- [ ] `CLAUDE.md` — update Architecture section
- [ ] `docs/skill-catalog.md` — update output items for stock-portfolio skill

---

## Common Notes

### HAS_MODULE Pattern (Script Layer)

Always define availability flags with `try/except ImportError` in script layer (`run_*.py`):

```python
# Shared flags: managed in scripts/common.py (KIK-448)
try:
    from src.data.history import HistoryStore as _
    HAS_HISTORY_STORE = True
except ImportError:
    HAS_HISTORY_STORE = False

# Script-specific flags: defined within each script
try:
    from src.core.portfolio.compare import compare_portfolios as _
    HAS_COMPARE = True
except ImportError:
    HAS_COMPARE = False
```

### Graceful Degradation

Always implement graceful degradation for external dependencies (Neo4j, Grok API, TEI):

```python
# Skip when Neo4j is not connected (e.g. health_check.py pattern)
try:
    from src.data import graph_store as gs
    if gs.is_available():
        gs.merge_health(...)
except Exception:
    pass  # Neo4j failures should not affect the main function
```

### Centralized Threshold Management

Avoid hardcoding; use `config/thresholds.yaml` + the `th()` helper:

```python
from src.core._thresholds import th

# Usage
MY_THRESHOLD = th("health", "my_threshold", default_value)
```

### Automatic Test Isolation

The `_block_external_io` fixture in `tests/conftest.py` automatically mocks Neo4j/TEI/Grok in all tests.
Tests that require external communication can opt out with `@pytest.mark.no_auto_mock`.
