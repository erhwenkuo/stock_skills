---
paths:
  - "src/core/screening/**"
  - ".claude/skills/screen-stocks/**"
  - "config/screening_presets.yaml"
---

# Screening Development Rules

> For specific steps to add a new screening preset (file list, code templates, test examples), see "Pattern 1" in [docs/patterns.md](../../docs/patterns.md).

## 5 Screener Engines

- **QueryScreener (default)**: `build_query()` → `screen_stocks()` [EquityQuery bulk API] → `_normalize_quote()` → `calculate_value_score()` → sort
- **ValueScreener (Legacy)**: Stock list approach. `get_stock_info()` → `apply_filters()` → `calculate_value_score()`. Japan/US/ASEAN only
- **PullbackScreener**: 3-stage pipeline. EquityQuery → `detect_pullback_in_uptrend()` → value_score. Two modes: "full" (exact match) and "partial" (bounce_score>=30)
- **AlphaScreener**: 4-stage pipeline. EquityQuery (undervaluation filter) → `compute_change_score()` → pullback detection → 2-axis scoring
- **MomentumScreener** (KIK-506): 2-stage pipeline. EquityQuery → `detect_momentum_surge()` → surge_score ranking. Two submodes: "stable" (sustained uptrend, 50MA +10-15%) and "surge" (rapid surge, 50MA +15%+)

## Value Score Distribution

P/E(25) + P/B(25) + Dividend Yield(20) + ROE(15) + Revenue Growth(15) = 100 points

## EquityQuery Rules

- Field names follow yfinance convention (`trailingPE`, `priceToBook`, `dividendYield`, etc.)
- Presets defined in `config/screening_presets.yaml`. Criteria thresholds managed in YAML

## yahoo_client Data Retrieval

- `get_stock_info(symbol)`: `ticker.info` only. Cache `{symbol}.json` (24h TTL)
- `get_stock_detail(symbol)`: info + price_history + balance_sheet + cashflow + income_stmt. Cache `{symbol}_detail.json`
- `screen_stocks(query)`: EquityQuery-based bulk screening (no cache)
- `get_price_history(symbol, period)`: OHLCV DataFrame (no cache, default 1 year)

## Anomaly Guard

`_sanitize_anomalies()` sanitizes the following:
- Dividend yield > 15% → None
- P/B < 0.1 or P/B > 100 → None
- P/E < 0 or P/E > 500 → None
- ROE > 200% → None

## Community Grouping (KIK-549)

The "📊 Graph Context" section (Neo4j connection only) of screening results displays community-based stock grouping.

- `screening_context.py`: Retrieves each stock's community membership via `symbol_communities` key
- `screening_summary_formatter.py`: Displays by community name × member count (e.g., "Technology x AI: A, B (2 stocks)")
- LLM interprets this grouping and generates summaries like "3 semiconductor-related stocks in top positions"
- Usage: Comparative analysis of similar stocks, checking overlap with existing holdings, assessing diversification
