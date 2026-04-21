---
paths:
  - "src/core/portfolio/**"
  - "src/core/risk/**"
  - "src/core/health_check.py"
  - "src/core/return_estimate.py"
  - "src/core/value_trap.py"
  - "src/output/portfolio_formatter.py"
  - "src/output/stress_formatter.py"
  - ".claude/skills/stock-portfolio/**"
  - ".claude/skills/stress-test/**"
---

# Portfolio & Stress Test Development Rules

## Portfolio Management

- CSV-based: `.claude/skills/stock-portfolio/data/portfolio.csv`
- `.CASH` symbols (JPY.CASH, USD.CASH) skip the Yahoo Finance API
- Use `_is_cash()` / `_cash_currency()` helpers for detection

## Health Check (KIK-356/357/374/403/438)

- `check_trend_health()`: Determines "uptrend/sideways/downtrend" from SMA50/200 and RSI
  - **Golden Cross/Dead Cross Detection (KIK-374)**: Detects cross events within a 60-day lookback. Returns `cross_signal`, `days_since_cross`, `cross_date`
  - **Small-cap cross lookback reduction (KIK-438)**: Small-cap stocks use `cross_lookback=30` for early detection of recent fluctuations
- `check_change_quality()`: Reuses `compute_change_score()` from alpha.py. ETFs are detected with `_is_etf()` and get `quality_label="N/A"`
- `compute_alert_level()`: 3 levels (early warning / caution / exit). Exit requires both technical breakdown AND fundamental deterioration. Dead cross triggers EXIT
  - **Shareholder return stability (KIK-403)**: `temporary` (temporary high return) → promote to EARLY_WARNING; `decreasing` (declining trend) → add reason only
  - **Small-cap alert escalation (KIK-438)**: When `is_small_cap=True`, automatically escalate EARLY_WARNING → CAUTION
- `check_long_term_suitability()`: Long-term suitability assessment. Uses `total_return_rate` (dividends + buybacks) if `shareholder_return_data` is available, otherwise falls back to `dividend_yield`
- ETF detection: `_is_etf()` uses `bool()` truthiness check

## Small-Cap Allocation (KIK-438)

- `src/core/portfolio/small_cap.py`: Centralized module for small-cap classification and allocation assessment
- `classify_market_cap(market_cap, region_code)`: Classifies as "small/mid/large/unknown" using region-specific thresholds
  - JP: ≤¥100B, US: ≤$1B, SG: ≤SGD 2B, others: see `_SMALL_CAP_THRESHOLDS`
  - Large-cap threshold = small-cap threshold × 5
- `check_small_cap_allocation(small_cap_weight)`: Checks the portfolio's overall small-cap ratio
  - `>25%` → warning, `>35%` → critical (configurable in `thresholds.yaml`)
- Added `infer_region_code()` to `src/core/ticker_utils.py` (suffix → 2-char region code)
- Health check output: Symbol with `[small]` badge + portfolio-wide small-cap ratio summary
- Structural analysis (analyze): Size composition table (large/mid/small/unknown) + size_hhi added (4-axis)

## Community Concentration Monitoring (KIK-549)

- `src/core/health_check.py`: `_compute_community_concentration()` measures concentration by community
- Community HHI = Σ(community market cap ratio)²
- Warning thresholds (only when count>=2 stocks in the same community):
  - weight `>30%` → warning "Community concentration somewhat high"
  - weight `>50%` → critical "Effective diversification may not be achieved"
- Health check output: `⚠️ Community concentration: XX community △ stocks (%%)`
- Community = stock cluster based on co-occurrence signals (Screen/Theme/Sector/News) (KIK-547)
- When Neo4j is not connected: `community_concentration = None` (no warning, graceful degradation)

## Shareholder Return Rate (KIK-375)

- `calculate_shareholder_return()`: Calculates total return rate of dividends + buybacks
- yahoo_client extracts `dividend_paid` and `stock_repurchase` from cashflow (3-step fallback)
- Output in stock-report under "## Shareholder Returns" section

## Return Estimation (KIK-359/360)

- Stocks: Calculate expected return from yfinance `targetHighPrice`/`targetMeanPrice`/`targetLowPrice`
- ETF: Calculate CAGR from past 2-year monthly returns and branch scenarios by ±1σ (capped at ±30%)
- News: Retrieve official media news via yfinance `ticker.news`
- X sentiment: Grok API (`grok-4-1-fast-non-reasoning` + X Search). Skip if `XAI_API_KEY` not set

## Rebalancing (KIK-363)

- 3 strategies: defensive (10%, 0.20), balanced (15%, 0.25), aggressive (25%, 0.35)
- Action generation: (1) sell: health=EXIT or base<-10%, (2) reduce: overweight/correlated concentration, (3) increase: positive return + within constraints

## Swap Proposal Rules (KIK-450)

When proposing portfolio swaps (replacement of EXIT stocks / presenting alternative candidates), **always run `what-if` simulation before proposing**.

- **When proposing a swap**: Run `what-if --remove "<EXIT stock>:SHARES" --add "<alternative>:SHARES:PRICE"` and present HHI changes, fund balance, and judgment label to the user
- **When proposing addition only**: Run `what-if --add "<additional stock>:SHARES:PRICE"` before proposing
- Proposing "consider switching to XX" verbally without running a simulation is prohibited
- **Single-lot cost limit**: If the single-lot cost (shares × price) exceeds 20% of total portfolio value, always state "1 lot ¥XX is YY% of total portfolio value"
- If the price needed for `what-if` is unknown, retrieve it via `yahoo_client.get_stock_info(symbol)["price"]` first

### Proposal Flow (Required Steps)

1. Detect EXIT/caution stocks with `health`
2. Search for alternative candidates with `/screen-stocks` (same sector/region)
3. **Run `what-if --remove "<EXIT stock>:<held shares>" --add "<alternative>:<shares>:<price>"`**
4. Present simulation results (HHI changes, fund balance, swap judgment) before proposing

## Scenario Analysis (KIK-354/358)

- 8 scenarios: Triple meltdown, USD/JPY surge, US recession, BOJ rate hike, US-China conflict, inflation resurgence, tech crash, JPY appreciation
- `SCENARIO_ALIASES` handles natural language input
- ETF asset class matching: `_ETF_ASSET_CLASS` mapping classifies gold, long-term bonds, equity income
- `_match_target()`: Priority order — region → currency → export/domestic → ETF asset class → non-tech → sector
