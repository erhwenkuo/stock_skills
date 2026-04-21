---
name: stock-portfolio
description: "Portfolio management. Display holdings, record trades, and analyze portfolio structure. Input data foundation for stress tests."
argument-hint: "[command] [args]  e.g.: snapshot, buy 7203.T 100 2850, sell AAPL 5, analyze, list"
allowed-tools: Bash(python3 *)
---

# Portfolio Management Skill

Parse $ARGUMENTS to determine the command and execute it as shown below.

## Execution Command

```bash
python3 /Users/kikuchihiroyuki/stock-skills/.claude/skills/stock-portfolio/scripts/run_portfolio.py <command> [args]
```

## Command Reference

### snapshot — Portfolio Snapshot

Generates a portfolio snapshot including current prices, P/L, and currency conversions.

```bash
python3 .../run_portfolio.py snapshot
```

### buy — Record a Purchase

```bash
python3 .../run_portfolio.py buy --symbol <sym> --shares <n> --price <p> [--currency JPY] [--date YYYY-MM-DD] [--memo text] [--yes]
```

Omitting `--yes` (`-y`) displays a confirmation preview of the purchase and exits. Specifying `--yes` skips confirmation and records directly (KIK-444).

### sell — Record a Sale

```bash
python3 .../run_portfolio.py sell --symbol <sym> --shares <n> [--price <sale price>] [--date YYYY-MM-DD] [--yes]
```

Omitting `--yes` (`-y`) displays a confirmation preview (cost basis, estimated realized P/L) and exits. Specifying `--yes` skips confirmation and records directly (KIK-444).

Specifying `--price` calculates and displays realized P/L, P/L ratio, and estimated after-tax amount, and saves to `data/history/trade/*.json` (KIK-441).

### review — Trade Performance Review (KIK-441)

Aggregates and displays P/L statistics from past sale records (those recorded with `--price`).

```bash
python3 .../run_portfolio.py review [--year 2026] [--symbol NVDA]
```

**Output:**
- Trade history table (symbol, sale date, shares, cost basis, sale price, holding period, realized P/L, P/L ratio)
- Statistics (trade count, win rate, average return, average holding period, total realized P/L)

### analyze — Structural Analysis

Calculates sector/region/currency/size HHI (Herfindahl index) and analyzes portfolio bias. Includes a 4-axis analysis with size composition table (large/mid/small/ETF/unknown) (KIK-438, KIK-469 P2: ETF classification). ETFs are independently classified as sector "ETF" and size "ETF."

```bash
python3 .../run_portfolio.py analyze
```

### health — Health Check

Checks whether the investment thesis for each holding is still valid. Outputs 3-level alerts across multiple axes: technical (SMA50/200, RSI, **Golden Cross/Dead Cross detection**) and fundamental (change quality score, **shareholder return stability**). **Small-cap stocks are automatically escalated in sensitivity** (KIK-438).

```bash
python3 .../run_portfolio.py health
```

**Technical Analysis (KIK-356/374/438):**
- Trend determination from SMA50/200 (uptrend/sideways/downtrend)
- **Golden Cross/Dead Cross detection**: Detects cross events within a 60-day lookback, displaying occurrence date and days elapsed
- **Small-cap cross lookback reduction (KIK-438)**: Small-cap stocks use a 30-day lookback for early detection of recent fluctuations

**Shareholder Return Stability (KIK-403):**
- Evaluates stability from total return rate (dividends + buybacks) (✅Stable high return/📈Increasing trend/⚠️Temporary high return/📉Declining trend)
- Temporary high return → escalate to early warning
- Declining trend → add reason to alert details
- Uses total return rate (dividends + buybacks) for long-term suitability assessment

**Small-Cap Allocation (KIK-438):**
- Classifies each stock by market cap size (large/mid/small/unknown) and displays `[small]` badge
- Small-cap stocks are automatically escalated: EARLY_WARNING → CAUTION
- Calculates portfolio-wide small-cap ratio; displays warning at >25%, critical at >35%

**ETF Health Check (KIK-469 Phase 2):**
- Displays individual stocks and ETFs in separate tables
- ETF table: symbol / P/L / trend / expense ratio / AUM / ETF score / alert
- Individual stock table: as before (change quality / long-term suitability / return stability)

**Alert Levels:**
- **Early Warning**: Below SMA50 / RSI sharp decline / 1 fundamental indicator deteriorating / **temporary high return**
- **Caution**: SMA50 approaching SMA200 + indicator deterioration / multiple change score deteriorations / **small-cap EARLY_WARNING escalation**
- **Exit**: **Dead cross detected** / trend breakdown + change score deterioration

### adjust — Portfolio Adjustment Advisor (KIK-496)

Generates specific adjustment actions (SELL/SWAP/ADD/TRIM_CLASS/FLAG) using 17 rules (P1-P10: per-position, F1-F7: PF-wide) based on health check results + market regime determination.

```bash
python3 .../run_portfolio.py adjust [--full]
```

CLI options:
- `--full`: Full analysis mode (includes concentration and correlation analysis. Higher API load)

**Output:**
- Market regime (bull/bear/crash/neutral) — determined from SMA50/200, RSI, drawdown
- Action table by HIGH/MEDIUM/LOW priority (action type / target / reason / rule ID)
- Summary (action count)

**Regime adjustment:** During crash, urgency is raised one level. During bear, small-cap and downtrend rules are elevated.

### rebalance — Rebalancing Proposal

Analyzes current portfolio structure and presents proposals for reducing concentration risk and adjusting toward target allocation.

```bash
python3 .../run_portfolio.py rebalance [options]
```

CLI options:
- `--strategy defensive|balanced|aggressive` (default: balanced)
- `--reduce-sector SECTOR` (e.g., Technology)
- `--reduce-currency CURRENCY` (e.g., USD)
- `--max-single-ratio RATIO` (e.g., 0.15)
- `--max-sector-hhi HHI` (e.g., 0.25)
- `--max-region-hhi HHI` (e.g., 0.30)
- `--additional-cash AMOUNT` (JPY, e.g., 1000000)
- `--min-dividend-yield YIELD` (e.g., 0.03)

### forecast — Estimated Yield

Estimates 12-month expected return for each holding in 3 scenarios (optimistic/base/pessimistic) from analyst target prices or historical return distributions. Includes value trap warnings and TOP/BOTTOM rankings.

```bash
python3 .../run_portfolio.py forecast
```

**Estimation methods:**
- **Analyst method**: Analyst target price + dividend yield + buyback yield (including shareholder return)
- **Historical return method**: For stocks without analyst coverage (ETFs, etc.), estimates from historical CAGR + standard deviation (KIK-469 P2: ETFs show annualized volatility + `[ETF]` badge)
- **Industry catalyst adjustment** (KIK-433, when Neo4j connected): Adds recent same-sector `growth_driver` catalyst count × 1.7% to optimistic scenario, subtracts `risk` catalyst count × 1.7% from pessimistic scenario (max ±10%)

**Output structure (KIK-390):**
1. Portfolio-wide 3-scenario yield and P/L table
2. Caution stocks section (aggregate stocks with value trap warnings)
3. Expected return TOP 3 / BOTTOM 3 rankings
4. Per-stock details (analyst target / Forward P/E / news count / X sentiment / 3 scenarios)

### what-if — What-If Simulation (KIK-376 / KIK-451)

Simulates adding, selling, or swapping stocks and displays the impact on the portfolio as a Before/After comparison.

```bash
# Add only (traditional)
python3 .../run_portfolio.py what-if --add "SYMBOL:SHARES:PRICE[,...]"

# Swap (sell then buy) (KIK-451)
python3 .../run_portfolio.py what-if --remove "SYMBOL:SHARES[,...]" --add "SYMBOL:SHARES:PRICE[,...]"

# Sell-only simulation (KIK-451)
python3 .../run_portfolio.py what-if --remove "SYMBOL:SHARES[,...]"
```

CLI options:
- `--add`: List of stocks to add (optional). Format: `SYMBOL:SHARES:PRICE` comma-separated
- `--remove`: List of stocks to sell (optional). Format: `SYMBOL:SHARES` comma-separated (no price needed — calculated at market value)
- At least one of `--add` or `--remove` is required

**Output:**
- **[On sell] Sell candidate context (KIK-470)**: When `--remove` is specified, automatically displays screening appearance count, investment memos, and research history before the simulation (when Neo4j connected)
- Before/After sector HHI / region HHI / currency HHI comparison
- Basic info on added stocks (P/E / P/B / dividend yield / ROE)
- **[On swap] Sell stock table** (symbol, shares, estimated sale proceeds)
- **[On swap] Fund balance** (required purchase funds / estimated sale proceeds / difference)
- **[On swap] Health check on sold stocks** (alert status of sell targets)
- Judgment label: Recommended / Proceed with caution / Not recommended (for swaps: "This swap is recommended," etc.)
- **ETF quality assessment (KIK-469 P2)**: When adding an ETF, ETF score is reflected in the judgment (quality good ≥75, warning if quality low <40)

### backtest — Backtest

Verifies returns from accumulated screening results and compares against benchmarks (Nikkei 225 / S&P 500).

```bash
python3 .../run_portfolio.py backtest [options]
```

CLI options:
- `--preset PRESET`: Screening preset to verify (e.g., alpha, value)
- `--region REGION`: Region to verify (e.g., jp, us)
- `--days N`: Verifies return N days after retrieval (default: 90)

**Output:**
- Average return by screening date
- Benchmark comparison (excess return)
- Win rate, average return, max return / max loss

### simulate — Compound Interest Simulation

Simulates future asset growth with compound interest based on the current portfolio. Calculates compound interest using forecast expected returns + dividend reinvestment + monthly accumulation, displayed in 3 scenarios (optimistic/base/pessimistic).

```bash
python3 .../run_portfolio.py simulate [options]
```

CLI options:
- `--years N` (simulation years, default: 10)
- `--monthly-add AMOUNT` (monthly accumulation, JPY, default: 0)
- `--target AMOUNT` (target amount, JPY, e.g., 15000000)
- `--reinvest-dividends` (reinvest dividends, default: ON)
- `--no-reinvest-dividends` (do not reinvest dividends)

### list — Holdings List

Displays the contents of portfolio.csv as-is.

```bash
python3 .../run_portfolio.py list
```

## Natural Language Routing

For natural language → skill selection, see [.claude/rules/intent-routing.md](../../rules/intent-routing.md).

## Constraints

- Japan stocks: 100-share lots (standard trading unit)
- ASEAN stocks: 100-share lots (minimum fee: JPY 3,300)
- Rakuten Securities compatible (fee structure)
- portfolio.csv path: `.claude/skills/stock-portfolio/data/portfolio.csv`

## Output

Display results in Markdown format.

### snapshot output items
- Symbol / Name / Shares held / Cost basis / Current price / Market value / P/L / P/L ratio / Currency

### analyze output items
- Sector HHI / Region HHI / Currency HHI / **Size HHI (KIK-438)**
- Composition ratio for each axis (**size composition table: large/mid/small/ETF/unknown**)
- ETF annotation (note that look-through is not supported)
- Risk level determination

### health output items
- **Individual stock table**: Symbol (**small-cap stocks show `[small]` badge**) / P/L ratio / Trend / **Cross event** / Change quality / Alert / **Long-term suitability** / **Return stability**
- **ETF table (KIK-469 P2)**: Symbol / P/L / Trend / Expense ratio / AUM / ETF score / Alert
- Details for stocks with alerts (reason, SMA/RSI values, cross occurrence date & days elapsed, change score, shareholder return stability, recommended action)
- **Small-cap allocation**: Portfolio-wide small-cap ratio summary (✅Normal/⚠️Warning/🔴Critical)

### forecast output items
- Portfolio-wide: 3-scenario yield (optimistic/base/pessimistic) + P/L + total market value
- Caution stocks section: List of stocks with value trap warnings
- TOP 3 / BOTTOM 3: Expected return rankings (with analyst count)
- Per-stock: Analyst target price / Forward P/E / news count / X sentiment / 3 scenarios / **ETFs show annualized volatility + `[ETF]` badge**

### what-if output items
- **[On sell] Sell candidate context (KIK-470)**: Screening appearance count, investment memos, research history
- Before/After HHI comparison (sector/region/currency)
- Fundamentals of added stocks
- Concentration change judgment
- **[On swap]** Sell stock table (estimated sale proceeds)
- **[On swap]** Fund balance (required purchase funds / sale proceeds / difference)
- **[On swap]** Health check on sold stocks
- **[On swap]** "This swap is recommended / Proceed with caution / Not recommended"

### backtest output items
- Return by screening date
- Benchmark comparison (excess return)
- Win rate, statistics

### adjust output items
- Market regime (regime name / SMA50 vs SMA200 / RSI / drawdown)
- HIGH Priority table: SELL/SWAP/TRIM_CLASS actions
- MEDIUM Priority table: FLAG/SELL actions
- LOW Priority table: FLAG actions
- Summary (HIGH/MEDIUM/LOW counts, regime)

### rebalance output items
- Current HHI (sector/region/currency) and target HHI
- Sell candidates (symbol, shares, reason)
- Buy candidates (symbol, shares, reason, dividend yield)
- Projected HHI after rebalancing

### simulate output items
- Annual progression table (year / market value / total invested / investment gain / cumulative dividends)
- 3-scenario comparison (optimistic/base/pessimistic final year)
- Goal achievement analysis (year of reaching goal / required monthly contribution)
- Compound interest effect of dividend reinvestment

## Execution Examples

```bash
# Snapshot
python3 .../run_portfolio.py snapshot

# Record purchase
python3 .../run_portfolio.py buy --symbol 7203.T --shares 100 --price 2850 --currency JPY --date 2025-06-15 --memo Toyota

# Record sale
python3 .../run_portfolio.py sell --symbol AAPL --shares 5

# Structural analysis
python3 .../run_portfolio.py analyze

# List holdings
python3 .../run_portfolio.py list

# Health check
python3 .../run_portfolio.py health

# Estimated yield
python3 .../run_portfolio.py forecast

# Rebalancing proposal
python3 .../run_portfolio.py rebalance
python3 .../run_portfolio.py rebalance --strategy defensive
python3 .../run_portfolio.py rebalance --reduce-sector Technology --additional-cash 1000000

# What-If simulation (add only)
python3 .../run_portfolio.py what-if --add "7203.T:100:2850,AAPL:10:250"

# What-If simulation (swap: sell 7203.T → buy 9984.T) (KIK-451)
python3 .../run_portfolio.py what-if --remove "7203.T:100" --add "9984.T:50:7500"

# What-If simulation (sell only) (KIK-451)
python3 .../run_portfolio.py what-if --remove "7203.T:50"

# Adjustment advisor (KIK-496)
python3 .../run_portfolio.py adjust
python3 .../run_portfolio.py adjust --full

# Backtest
python3 .../run_portfolio.py backtest --preset alpha --region jp --days 90
```

## Prior Knowledge Integration Rules (KIK-466)

### health command

When `get_context.py` output contains the following, integrate with health check results:

- **Trade history (BOUGHT/SOLD)**: Reference purchase price and date to add unrealized P/L context. If a sold stock appears in warnings, explicitly state "already sold — no issue"
- **Investment memos (Note)**: If thesis or concern memos exist, cross-check with health check results. e.g., "Value trap concern memo → BT score also high this time → truly needs attention"
- **Previous health check (HealthCheck)**: Show diff from previous result. "Previous: HOLD → This time: EXIT: situation deteriorated" / "Previous: EXIT → This time: HOLD: improved"
- **Screening history (SURFACED)**: If a flagged stock has historically been in the top of screenings, "High attention (top 3 times) but currently needs caution"
- **Thesis age**: If a thesis memo is 90+ days old, prompt "time to review the thesis"

### snapshot / forecast

- If a previous snapshot or forecast exists, add diff comments
- e.g., "vs. previous: market value +5.2%, yield improved"

### Prompting to Record Analysis Conclusions

When the response includes specific judgments about EXIT/warnings (e.g., "sell recommended," "continue holding"):
> 💡 Would you like to record this judgment as an investment memo?
