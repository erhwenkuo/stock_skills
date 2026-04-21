# Skill Catalog

A catalog of 8 Claude Code Skills. All defined in `.claude/skills/<name>/SKILL.md` and implemented in `scripts/*.py`.

---

## Overview

<!-- BEGIN AUTO-GENERATED OVERVIEW -->
| Skill | Description |
|:---|:---|
| graph-query | Natural language queries to the knowledge graph. Search past reports, screenings, trades, research, and market context. |
| investment-note | Investment note management. Record, retrieve, and delete investment theses, concerns, and lessons. |
| market-research | Deep research on stocks, industries, markets, and business models. Integrates Grok API (X/Web search) and yfinance for multi-angle analysis reports. |
| plan-execute | Plan mode — design a workflow then execute skills. Activated when "plan mode" is requested. |
| screen-stocks | Undervalued stock screening. EquityQuery-based screening without a pre-defined ticker list. Screens Japanese, US, ASEAN, Hong Kong... stocks by P/E, P/B, dividend yield, ROE, etc. |
| stock-portfolio | Portfolio management. List holdings, record trades, structural analysis. Foundation for stress test input data. |
| stock-report | Detailed report for individual stocks and ETFs. Generates a financial analysis report from a ticker symbol. Individual stocks show valuation, undervaluation score, and shareholder return rate. ETFs show expense ratio, AUM, and fund size. |
| stress-test | Portfolio stress test. Receives a list of holdings and identifies portfolio weaknesses through shock sensitivity, scenario analysis, and causal chains. |
| watchlist | Watchlist management. Add, remove, and list stocks. |
<!-- END AUTO-GENERATED OVERVIEW -->

---

## 1. screen-stocks

Undervalued stock screening. Executes EquityQuery-based screening without a pre-defined ticker list.

**Script**: `.claude/skills/screen-stocks/scripts/run_screen.py`

**Options**:
- `--region`: Target region (japan, us, asean, sg, hk, kr, tw, cn, etc.)
- `--preset`: Strategy preset (alpha, value, high-dividend, growth, growth-value, deep-value, quality, pullback, trending, long-term, shareholder-return, high-growth, small-cap-growth, contrarian, momentum)
- `--sector`: Sector filter (e.g. Technology)
- `--top N`: Show top N results
- `--with-pullback`: Add pullback analysis
- `--theme`: Theme filter for trending preset

**Examples**:
```bash
python3 run_screen.py --region japan --preset alpha --top 10
python3 run_screen.py --region us --preset trending --theme "AI" --top 10
python3 run_screen.py --region japan --preset growth --top 10
python3 run_screen.py --region japan --preset long-term --top 10
python3 run_screen.py --region japan --preset momentum --top 10
python3 run_screen.py --region japan --preset contrarian --top 10
```

**Output**: Markdown table (ticker / name / score / P/E / P/B / dividend yield / ROE). The contrarian preset (KIK-504) includes a 3-axis score (technical / valuation / fundamental divergence); the momentum preset (KIK-506) includes a 4-axis momentum score (RSI / MACD / ROC / volume). Recently sold tickers are automatically excluded (KIK-418); tickers with concern/lesson notes are marked (KIK-419).

**Annotation Markers** (KIK-418/419):
- ⚠️ = Has concern note
- 📝 = Has lesson note
- 👀 = On watch (observation note with keywords like "pass" or "wait")
- Tickers sold within the last 90 days are automatically excluded from results

**Core Dependencies**: `src/core/screening/screener.py`, `indicators.py`, `filters.py`, `query_builder.py`, `alpha.py`, `technicals.py`, `contrarian.py`, `contrarian_screener.py`, `momentum.py`, `momentum_screener.py`, `src/data/screen_annotator.py`

---

## 2. stock-report

Detailed valuation report for an individual stock.

**Script**: `.claude/skills/stock-report/scripts/generate_report.py`

**Input**: Ticker symbol (e.g. 7203.T, AAPL)

**Examples**:
```bash
python3 generate_report.py 7203.T
python3 generate_report.py AAPL
```

**Output**: Markdown report (basic info / valuation / undervaluation score / contrarian signals / shareholder return rate / 3-year return history / value trap detection)

**Core Dependencies**: `src/core/screening/indicators.py`, `src/core/value_trap.py`, `src/core/screening/contrarian.py`, `src/data/yahoo_client.py`

---

## 3. market-research

Deep research integrating Grok API (X search/Web search) and yfinance.

**Script**: `.claude/skills/market-research/scripts/run_research.py`

**Subcommands**:
- `stock <symbol>`: Latest news and X sentiment for an individual stock
- `industry <name>`: Industry trend research
- `market <name>`: Market overview
- `business <symbol>`: Business model and corporate structure analysis

**Examples**:
```bash
python3 run_research.py stock 7203.T
python3 run_research.py industry semiconductors
python3 run_research.py market nikkei
python3 run_research.py business 7751.T
```

**Output**: Markdown report (overview / news / X trends / analysis)

**Core Dependencies**: `src/core/research/researcher.py`, `src/data/grok_client.py`, `src/data/yahoo_client.py`

**Note**: Requires the `XAI_API_KEY` environment variable. If unset, the Grok portion is skipped and the report is generated from yfinance data only.

---

## 4. watchlist

CRUD management for watchlists.

**Script**: `.claude/skills/watchlist/scripts/manage_watchlist.py`

**Subcommands**:
- `list [--name NAME]`: List watchlists
- `add --name NAME --symbols SYM1,SYM2`: Add tickers
- `remove --name NAME --symbols SYM1`: Remove tickers

**Examples**:
```bash
python3 manage_watchlist.py list
python3 manage_watchlist.py add --name "watchlist" --symbols "7203.T,AAPL"
python3 manage_watchlist.py remove --name "watchlist" --symbols "7203.T"
```

**Output**: Markdown list

**Core Dependencies**: None (reads/writes JSON files directly)

---

## 5. stress-test

Portfolio stress test. 8 predefined scenarios + custom scenarios.

**Script**: `.claude/skills/stress-test/scripts/run_stress_test.py`

**Options**:
- `--portfolio`: Comma-separated ticker list or auto-fetched from portfolio
- `--scenario`: Scenario name (triple-meltdown, USD/JPY surge, etc.)

**Examples**:
```bash
python3 run_stress_test.py --portfolio 7203.T,AAPL,D05.SI
python3 run_stress_test.py --scenario tech-crash
```

**Output**: Markdown report (correlation matrix / shock sensitivity / scenario analysis / causal chain / recommended actions). Results are auto-saved to `data/history/stress_test/` (KIK-428).

**Scenarios**: Triple meltdown, USD/JPY surge, US recession, BOJ rate hike, US-China conflict, inflation resurgence, tech crash, JPY appreciation

**Auto-Save** (KIK-428): On completion, auto-saved to `data/history/stress_test/{date}_{scenario}.json`. Also dual-writes a StressTest node + STRESSED relationship to Neo4j.

**Core Dependencies**: `src/core/risk/correlation.py`, `shock_sensitivity.py`, `scenario_analysis.py`, `scenario_definitions.py`, `recommender.py`, `src/data/history_store.py`

---

## 6. stock-portfolio

Portfolio management. 13 subcommands for holdings management, analysis, and simulation.

**Script**: `.claude/skills/stock-portfolio/scripts/run_portfolio.py`

**Subcommands**:

| Command | Description |
|:---|:---|
| `list` | List holdings (CSV display) |
| `snapshot` | Snapshot of current prices, P&L, and currency conversion |
| `buy` | Record a purchase |
| `sell` | Record a sale |
| `analyze` | Structural analysis (sector / region / currency HHI) |
| `health` | Health check (3-level alerts + cross detection + value trap + return stability) |
| `forecast` | Estimated yield (3 scenarios). Results are auto-saved (KIK-428) |
| `rebalance` | Rebalancing suggestions |
| `simulate` | Compound interest simulation |
| `what-if` | What-If simulation (impact of adding a stock) |
| `backtest` | Verify returns from past screening results |
| `adjust` | Portfolio adjustment advisor (17-rule diagnosis → action suggestions, KIK-496) |

**Examples**:
```bash
python3 run_portfolio.py snapshot
python3 run_portfolio.py buy --symbol 7203.T --shares 100 --price 2850 --currency JPY
python3 run_portfolio.py sell --symbol AAPL --shares 5
python3 run_portfolio.py health
python3 run_portfolio.py simulate --years 5 --monthly-add 50000 --target 15000000
python3 run_portfolio.py what-if --add "7203.T:100:2850,AAPL:10:250"
python3 run_portfolio.py backtest --preset alpha --region jp --days 90
python3 run_portfolio.py adjust
python3 run_portfolio.py adjust --full
```

**Auto-Save** (KIK-428): On `forecast` subcommand completion, auto-saved to `data/history/forecast/{date}_forecast.json`. Also dual-writes a Forecast node + FORECASTED relationship to Neo4j.

**Core Dependencies**: `src/core/portfolio/portfolio_manager.py`, `concentration.py`, `rebalancer.py`, `simulator.py`, `backtest.py`, `portfolio_simulation.py`, `adjustment_advisor.py`, `market_regime.py`, `src/core/health_check.py`, `return_estimate.py`, `value_trap.py`, `src/data/history_store.py`

---

## 7. investment-note

Investment note management. Dual-write pattern with JSON + Neo4j.

**Script**: `.claude/skills/investment-note/scripts/manage_note.py`

**Subcommands**:
- `save --symbol SYM --type TYPE --content TEXT [--source SRC]`
- `list [--symbol SYM] [--type TYPE]`
- `delete --id NOTE_ID`

**Note Types**: thesis, observation, concern, review, target, lesson

**Examples**:
```bash
python3 manage_note.py save --symbol 7203.T --type thesis --content "EV adoption increases parts demand"
python3 manage_note.py list --symbol 7203.T
python3 manage_note.py list --type lesson
python3 manage_note.py delete --id abc123
```

**Output**: Markdown table (date / ticker / type / content)

**Core Dependencies**: `src/data/note_manager.py`, `src/data/graph_store.py`

---

## 8. graph-query

Natural language queries to the knowledge graph. Dispatches regex pattern matches from natural language to functions in `graph_query.py`.

**Script**: `.claude/skills/graph-query/scripts/run_query.py`

**Input**: Natural language query

**Supported Query Types**:

| Pattern | Query Type | Function |
|:---|:---|:---|
| last time, previous, past report | prior_report | `get_prior_report(symbol)` |
| appeared many times, recurring candidate | recurring_picks | `get_recurring_picks()` |
| research history, previously researched | research_chain | `get_research_chain(type, target)` |
| recent market, market context | market_context | `get_recent_market_context()` |
| trade history, buy/sell record | trade_context | `get_trade_context(symbol)` |
| notes, memo list | stock_notes | `get_trade_context(symbol).notes` |
| stress test history, last stress test | stress_test_history | `get_stress_test_history(symbol)` (KIK-428) |
| forecast trend, last outlook | forecast_history | `get_forecast_history(symbol)` (KIK-428) |

**Examples**:
```bash
python3 run_query.py "What was the last report on 7203.T?"
python3 run_query.py "Which stocks keep showing up as candidates?"
python3 run_query.py "AAPL trade history"
python3 run_query.py "What is the recent market context?"
```

**Output**: Markdown table (format depends on query type)

**Core Dependencies**: `src/data/graph_nl_query.py`, `src/data/graph_query.py`, `src/data/graph_store.py`

---

## Skill → Core Module Dependency Map

```
screen-stocks ──→ screening/{screener,indicators,filters,query_builder,alpha,technicals,contrarian,contrarian_screener}
                   yahoo_client, grok_client (trending only)

stock-report ───→ screening/{indicators,contrarian}, value_trap
                   yahoo_client

market-research → research/researcher
                   grok_client, yahoo_client

watchlist ──────→ (none - direct JSON)

stress-test ────→ risk/{correlation,shock_sensitivity,scenario_analysis,scenario_definitions,recommender}
                   yahoo_client

stock-portfolio → portfolio/{portfolio_manager,concentration,rebalancer,simulator,backtest,portfolio_simulation,adjustment_advisor,market_regime}
                   health_check, return_estimate, value_trap
                   yahoo_client

investment-note → note_manager, graph_store

graph-query ────→ graph_nl_query, graph_query, graph_store

(auto-context) ─→ auto_context (graph_store, graph_query)
                   ※ Not a skill — uses rules/graph-context.md + scripts/get_context.py
                   ※ Context is automatically injected before skill execution
```
