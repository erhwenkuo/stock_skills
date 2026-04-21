# Data Model Definitions (KIK-524)

Two dict schemas returned by `yahoo_client`. All core modules — screeners, reports, health checks, etc. — depend on these structures.

---

## stock_info dict (28 fields)

Basic data returned by `yahoo_client.get_stock_info(symbol)`. Subject to JSON caching.

| Key | Type | Description | yfinance raw key | Normalization |
|:---|:---|:---|:---|:---|
| `symbol` | `str` | Ticker symbol | argument | — |
| `name` | `str \| None` | Company name | `shortName` / `longName` | — |
| `sector` | `str \| None` | Sector | `sector` | — |
| `industry` | `str \| None` | Industry | `industry` | — |
| `currency` | `str \| None` | Currency code (JPY/USD, etc.) | `currency` | — |
| `price` | `float \| None` | Current stock price | `regularMarketPrice` | — |
| `market_cap` | `float \| None` | Market capitalization | `marketCap` | — |
| `per` | `float \| None` | P/E ratio (trailing) | `trailingPE` | — |
| `forward_per` | `float \| None` | Forward P/E ratio | `forwardPE` | — |
| `pbr` | `float \| None` | P/B ratio | `priceToBook` | — |
| `psr` | `float \| None` | P/S ratio | `priceToSalesTrailing12Months` | — |
| `roe` | `float \| None` | ROE. Ratio (0.12 = 12%) | `returnOnEquity` | — |
| `roa` | `float \| None` | ROA. Ratio | `returnOnAssets` | — |
| `profit_margin` | `float \| None` | Net profit margin. Ratio | `profitMargins` | — |
| `operating_margin` | `float \| None` | Operating margin. Ratio | `operatingMargins` | — |
| `dividend_yield` | `float \| None` | Forward dividend yield. Ratio (0.028 = 2.8%) | `dividendYield` | `_normalize_ratio` |
| `dividend_yield_trailing` | `float \| None` | Trailing dividend yield. Ratio | `trailingAnnualDividendYield` | — |
| `payout_ratio` | `float \| None` | Dividend payout ratio. Ratio | `payoutRatio` | — |
| `revenue_growth` | `float \| None` | Revenue growth rate. Ratio (0.15 = 15%) | `revenueGrowth` | — |
| `earnings_growth` | `float \| None` | Earnings growth rate. Ratio | `earningsGrowth` | — |
| `debt_to_equity` | `float \| None` | D/E ratio (percentage, 105.0 = 105%) | `debtToEquity` | — |
| `current_ratio` | `float \| None` | Current ratio | `currentRatio` | — |
| `free_cashflow` | `float \| None` | Free cash flow (absolute value) | `freeCashflow` | — |
| `beta` | `float \| None` | Beta | `beta` | — |
| `fifty_two_week_high` | `float \| None` | 52-week high | `fiftyTwoWeekHigh` | — |
| `fifty_two_week_low` | `float \| None` | 52-week low | `fiftyTwoWeekLow` | — |
| `quoteType` | `str \| None` | Type ("EQUITY" / "ETF", etc.) | `quoteType` | — |

**Total: 27 keys** (`quoteType` added in KIK-469)

### Normalization Rule (`_normalize_ratio`)

yfinance returns `dividendYield` as a percentage value (e.g. 2.52). `_normalize_ratio()` always divides by 100 to convert to a ratio.

```python
def _normalize_ratio(value):
    if value is None:
        return None
    return value / 100.0  # 2.52 → 0.0252
```

`dividend_yield_trailing` (`trailingAnnualDividendYield`) is already returned as a ratio by yfinance and does not need normalization.

### Anomaly Sanitization (`_sanitize_anomalies`)

| Field | Condition | Action |
|:---|:---|:---|
| `dividend_yield` | > 0.15 (15%) | → `None` |
| `dividend_yield_trailing` | > 0.15 (15%) | → `None` |
| `pbr` | < 0.05 | → `None` |
| `per` | 0 < per < 1.0 | → `None` |
| `roe` | < -1.0 or > 2.0 | → `None` |

### Alias Support (`indicators.py`)

`calculate_value_score()` and similar functions accept both yfinance raw keys and normalized keys:

| Normalized key | yfinance raw key |
|:---|:---|
| `per` | `trailingPE` |
| `pbr` | `priceToBook` |
| `dividend_yield` | `dividendYield` |
| `roe` | `returnOnEquity` |
| `revenue_growth` | `revenueGrowth` |

---

## stock_detail dict (45+ fields)

Detailed data returned by `yahoo_client.get_stock_detail(symbol)`. Includes all fields from `stock_info` plus financial statement data.

### Inherited from stock_info (27 fields)

All keys from the `stock_info dict` above are included as-is.

### Additional Fields: Price

| Key | Type | Description | Source |
|:---|:---|:---|:---|
| `price_history` | `list[float] \| None` | 2-year closing price list (chronological) | `ticker.history(period="2y")` |

### Additional Fields: Balance Sheet

| Key | Type | Description | Source |
|:---|:---|:---|:---|
| `equity_ratio` | `float \| None` | Equity ratio (net assets / total assets) | `balance_sheet` |
| `total_assets` | `float \| None` | Total assets | `balance_sheet` |
| `equity_history` | `list[float]` | Net assets trend (latest → past, max 4 periods) | `balance_sheet` |

### Additional Fields: Cash Flow

| Key | Type | Description | Source |
|:---|:---|:---|:---|
| `operating_cashflow` | `float \| None` | Operating cash flow | `cashflow` |
| `fcf` | `float \| None` | Free cash flow | `cashflow` |
| `dividend_paid` | `float \| None` | Dividends paid (negative = outflow) | `cashflow` (KIK-375) |
| `stock_repurchase` | `float \| None` | Stock buybacks (negative = outflow) | `cashflow` (KIK-375) |
| `dividend_paid_history` | `list[float]` | Dividends paid trend (latest → past, max 4 periods) | `cashflow` (KIK-380) |
| `stock_repurchase_history` | `list[float]` | Stock buyback trend (latest → past, max 4 periods) | `cashflow` (KIK-380) |
| `cashflow_fiscal_years` | `list[int]` | Fiscal year for each period (e.g. [2025, 2024, 2023]) | `cashflow` (KIK-380) |

### Additional Fields: Income Statement

| Key | Type | Description | Source |
|:---|:---|:---|:---|
| `net_income_stmt` | `float \| None` | Net income | `income_stmt` |
| `eps_current` | `float \| None` | Diluted EPS (latest period) | `income_stmt` |
| `eps_previous` | `float \| None` | Diluted EPS (prior period) | `income_stmt` |
| `eps_growth` | `float \| None` | EPS growth rate. Ratio (0.094 = 9.4%) | calculated |
| `revenue_history` | `list[float]` | Revenue trend (latest → past, max 4 periods) | `income_stmt` |
| `net_income_history` | `list[float]` | Net income trend (latest → past, max 4 periods) | `income_stmt` |

### Additional Fields: Debt & Valuation

| Key | Type | Description | Source |
|:---|:---|:---|:---|
| `total_debt` | `float \| None` | Total interest-bearing debt | `ticker.info` |
| `ebitda` | `float \| None` | EBITDA | `ticker.info` |

### Additional Fields: Analyst (KIK-359)

| Key | Type | Description | Source |
|:---|:---|:---|:---|
| `target_high_price` | `float \| None` | Analyst target price (high) | `ticker.info` |
| `target_low_price` | `float \| None` | Analyst target price (low) | `ticker.info` |
| `target_mean_price` | `float \| None` | Analyst target price (mean) | `ticker.info` |
| `number_of_analyst_opinions` | `int \| None` | Number of analyst opinions | `ticker.info` |
| `recommendation_mean` | `float \| None` | Mean recommendation (1=Strong Buy ~ 5=Strong Sell) | `ticker.info` |
| `forward_eps` | `float \| None` | Forward EPS | `ticker.info` |

### Additional Fields: ETF (KIK-469)

Only meaningful for ETFs. Mostly `None` for individual stocks.

| Key | Type | Description | Source |
|:---|:---|:---|:---|
| `expense_ratio` | `float \| None` | Expense ratio | `ticker.info` (`annualReportExpenseRatio`) |
| `total_assets_fund` | `float \| None` | AUM (assets under management) | `ticker.info` (`totalAssets`) |
| `fund_category` | `str \| None` | Fund category | `ticker.info` (`category`) |
| `fund_family` | `str \| None` | Fund family | `ticker.info` (`fundFamily`) |

---

## Common Utilities

### `finite_or_none(v)` (`src/core/common.py`)

A widely used helper in Core modules. Converts NaN/Inf to `None` for safe numeric retrieval.

```python
def finite_or_none(v):
    """Return v if finite number, else None."""
    if v is None:
        return None
    f = float(v)
    return None if (math.isnan(f) or math.isinf(f)) else f
```

### `_safe_get(info, key)` (`yahoo_client/_normalize.py`)

Safely retrieves a value from a yfinance info dict. Converts NaN/Inf to `None`.

---

## Test Fixtures

| File | Contents | Usage |
|:---|:---|:---|
| `tests/fixtures/stock_info.json` | stock_info equivalent (27 fields, Toyota 7203.T) | `stock_info_data` fixture in `conftest.py` |
| `tests/fixtures/stock_detail.json` | stock_detail equivalent (stock_info + additional fields) | `stock_detail_data` fixture in `conftest.py` |

Tests use `monkeypatch` to mock `yahoo_client.get_stock_info` / `get_stock_detail` and return these JSON files.
