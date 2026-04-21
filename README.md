# stock-skills

[English](README.md) | [繁體中文](README_zh-TW.md) | [简体中文](README_zh-CN.md)

An undervalued stock screening system. Screens for undervalued stocks across 60+ regions using the Yahoo Finance API (yfinance). Runs as [Claude Code](https://claude.ai/code) Skills — just speak in natural language and the right function executes automatically.

## Credits

Thanks to [okiku](https://qiita.com/okikusan-public) who published three interesting articles how he has utilized Claude Code to design [stock-skills](https://github.com/okikusan-public/stock_skills) using agents skills.

1. [Claude Code Skills × 投資分析シリーズ — 記事一覧](https://qiita.com/okikusan-public/items/6707fa0c99dbcc3e493f)
2. [Claude Code Skills で株スクリーニングを自動化した話 Vol.1【Python × yfinance × バイブコーディング】](https://qiita.com/okikusan-public/items/61100a5b1aa8d752ae24)
3. [Claude Code Skills で「使うほど賢くなる」投資分析AIを作った話 Vol.2【Neo4j × 個人開発】](https://qiita.com/okikusan-public/items/405949f83e8a39a49566)
4. [Claude Code Skills × 投資分析 Vol.3 — 処方箋エンジン・逆張り検出・銘柄クラスタリング](https://qiita.com/okikusan-public/items/1765d6afb8c548f019f1)
5. [Claude Code Skills で株スクリーニングを自動化した話 Vol.4【マルチAIエージェント × Agentic AI Pattern】](https://qiita.com/okikusan-public/items/27d9b0f0177293db8b1a)

The origin repo - [stock_skills](https://github.com/okikusan-public/stock_skills) is the result of "Vol.1〜3" that mentioned above.

There are many Japan characters in origin repo, so this repo translate most of remark, comments, docstring to English for users who want to learn from these awesome sharings.

## Prerequisites

| Requirement | Version | Notes |
|:---|:---|:---|
| Python | 3.13+ | Required |
| [uv](https://github.com/astral-sh/uv) | Latest | Package & venv manager |
| Docker | Latest | For Neo4j & TEI (optional) |
| Neo4j | 5.x (Community) | Knowledge graph — runs via Docker Compose |
| Grok API key (`XAI_API_KEY`) | — | X sentiment analysis & theme detection (optional) |

**Optional services** (all skills work without them via graceful degradation):
- **Neo4j** — enables knowledge graph search, context injection, and cross-session memory
- **TEI (Text Embeddings Inference)** — enables vector similarity search across past analyses
- **Grok API** — enables X/web sentiment analysis, trending stock detection, and auto-theme screening

## Setup

```bash
uv sync
```

Activate the virtual environment before running any commands:

```bash
source .venv/bin/activate
```

### Optional: Start Neo4j & TEI with Docker

```bash
docker compose up -d
python3 scripts/init_graph.py --rebuild  # Initialize schema + import existing data
```

### Environment Variables

```bash
# Grok API (X sentiment analysis, optional)
export XAI_API_KEY=xai-xxxxxxxxxxxxx

# Neo4j write depth (off/summary/full, default: full)
export NEO4J_MODE=full

# TEI vector search endpoint (default: http://localhost:8081)
export TEI_URL=http://localhost:8081

# Context freshness thresholds (in hours)
export CONTEXT_FRESH_HOURS=24    # Within this → answer from cache
export CONTEXT_RECENT_HOURS=168  # Within this → incremental update / beyond → full re-fetch
```

All are optional. The system works with default values if not set.

## Skills

### `/screen-stocks` — Undervalued Stock Screening

Searches for stocks from Japan, US, ASEAN, and more using EquityQuery. Supports 15 presets and 60+ regions.

```bash
# Basic usage
/screen-stocks japan value        # Japanese value stocks
/screen-stocks us high-dividend   # US high-dividend stocks
/screen-stocks asean growth-value # ASEAN growth-value stocks

# Preset list (15 strategies)
# value / high-dividend / growth / growth-value / deep-value / quality / pullback / alpha / trending
# long-term / shareholder-return / high-growth / small-cap-growth / contrarian / momentum

# Theme filtering
/screen-stocks us value --theme ai                    # AI-related undervalued stocks
/screen-stocks japan growth-value --theme ev          # EV-related growth-value stocks

# Contrarian & momentum
/screen-stocks japan contrarian    # Oversold stocks (3-axis score)
/screen-stocks us momentum         # Surging stocks (4-axis momentum)

# Options
/screen-stocks japan value --sector Technology  # Filter by sector
/screen-stocks japan value --with-pullback      # Add pullback filter
```

### `/stock-report` — Individual Stock Report

Generates a financial analysis report for a specified ticker symbol. Displays valuation, undervaluation score, **shareholder return rate** (dividends + buybacks), and value trap assessment.

```bash
/stock-report 7203.T    # Toyota
/stock-report AAPL      # Apple
```

**Output includes:**
- Sector & industry
- Valuation (P/E, P/B, dividend yield, ROE, earnings growth)
- Undervaluation score (0–100)
- **Shareholder return** (dividend yield + buyback yield = total shareholder return rate)

### `/watchlist` — Watchlist Management

Add, remove, and list stocks of interest.

```bash
/watchlist list
/watchlist add my-list 7203.T AAPL
/watchlist show my-list
```

### `/stress-test` — Stress Test

Portfolio shock sensitivity, scenario analysis, correlation analysis, VaR, and recommended actions. 8 predefined scenarios (triple meltdown, tech crash, JPY appreciation, etc.).

```bash
/stress-test 7203.T,AAPL,D05.SI
/stress-test 7203.T,9984.T --scenario triple-meltdown
```

### `/market-research` — Deep Research

In-depth analysis of stocks, industries, markets, and business models. Fetches latest news, X sentiment, and industry trends via the Grok API.

```bash
/market-research stock 7203.T      # Stock research
/market-research industry semiconductors  # Industry research
/market-research market nikkei     # Market overview
/market-research business 7751.T   # Business model analysis
```

### `/stock-portfolio` — Portfolio Management

Record buy/sell trades, view P&L, analyze portfolio structure, run health checks, estimate yield, rebalance, and simulate. Multi-currency support (converted to JPY).

```bash
/stock-portfolio snapshot   # Current P&L
/stock-portfolio buy 7203.T 100 2850 JPY
/stock-portfolio sell AAPL 5
/stock-portfolio analyze    # HHI concentration analysis
/stock-portfolio health     # Health check (3-level alerts + cross detection + value trap + return stability)
/stock-portfolio forecast   # Estimated yield (optimistic/base/pessimistic + news + X sentiment)
/stock-portfolio rebalance  # Rebalancing suggestions
/stock-portfolio simulate   # Compound interest simulation (3 scenarios + dividend reinvestment + DCA)
/stock-portfolio what-if    # What-if simulation
/stock-portfolio backtest   # Backtest screening results
```

### `/investment-note` — Investment Notes

Record, retrieve, and delete investment theses, concerns, and lessons.

```bash
/investment-note save --symbol 7203.T --type thesis --content "EV adoption drives parts demand growth"
/investment-note list
/investment-note list --symbol AAPL
```

### `/graph-query` — Knowledge Graph Search

Search past reports, screenings, trades, and research history in natural language.

```bash
/graph-query "Previous report on 7203.T?"
/graph-query "Stocks that keep appearing as candidates?"
/graph-query "NVDA sentiment trend"
```

## Architecture

```
Skills (.claude/skills/*/SKILL.md → scripts/*.py)
  │
  ▼
Core (src/core/)
  screening/ ─ screener, indicators, filters, query_builder, alpha, technicals, momentum, contrarian
  portfolio/ ─ portfolio_manager, portfolio_simulation, concentration, rebalancer, simulator, backtest
  risk/      ─ correlation, shock_sensitivity, scenario_analysis, scenario_definitions, recommender
  research/  ─ researcher (yfinance + Grok API integration)
  [root]     ─ common, models, ticker_utils, health_check, return_estimate, value_trap
  │
  ├─ Markets (src/markets/) ─ japan/us/asean
  ├─ Data (src/data/)
  │    yahoo_client.py ─ 24h JSON cache
  │    grok_client.py ─ Grok API (X sentiment analysis)
  │    graph_store.py ─ Neo4j knowledge graph (dual-write)
  │    history_store.py ─ automatic execution history accumulation
  ├─ Output (src/output/) ─ Markdown formatters
  └─ Config (config/) ─ presets (15 strategies) · exchange definitions (60 regions)
```

For details, see [CLAUDE.md](CLAUDE.md).

## Neo4j Knowledge Graph (Optional)

Accumulates skill execution history in Neo4j, enabling cross-search across past analyses, trades, and research.

```bash
# Start Neo4j with Docker
docker compose up -d

# Initialize schema + import existing data
python3 scripts/init_graph.py --rebuild
```

All skills work normally without a Neo4j connection (graceful degradation).

## Tests

```bash
pytest tests/           # All 1573 tests (< 6 seconds)
pytest tests/core/ -v   # Core modules
```

## Disclaimer

This software provides reference information for investment decisions and **does not guarantee investment outcomes**. All investment decisions based on the output of this software are made at the user's own risk. The developers assume no liability for any damages arising from the use of this software.

## License

This software is license-free. Anyone is free to use, modify, and redistribute it.
