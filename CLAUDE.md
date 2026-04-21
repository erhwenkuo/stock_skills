# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Design Philosophy

**This system is designed with a "natural language first" approach.**

Users do not need to memorize slash commands or parameters. Simply convey your intent in plain language and the appropriate skill is automatically selected and executed.

- "Any good Japanese stocks?" → screening runs
- "What do you think about Toyota?" → individual report is generated
- "Is my portfolio okay?" → health check is executed
- "Any room for improvement?" → the system analyzes itself and makes suggestions

Skills (such as `/screen-stocks`) are internal implementation details, not the user interface. Intent inference from natural language is the primary entry point; commands are merely a supplementary means.

When adding new features, always consider **what words a user might use to invoke that feature** and reflect those expressions in `intent-routing.md`.

## Project Overview

An undervalued-stock screening system. Uses the Yahoo Finance API (yfinance) to screen for undervalued stocks across 60+ regions including Japan, US, ASEAN, Hong Kong, Korea, and Taiwan. Runs as Claude Code Skills — just speak in natural language and the right function executes automatically.

## Development Environment

The development environment is managed using [UV](https://github.com/astral-sh/uv). Before running any Python commands, activate the virtual environment:

```bash
source .venv/bin/activate
```

To install or sync dependencies:

```bash
uv sync
```

## Commands

See [docs/skill-catalog.md](docs/skill-catalog.md) for full command details for each skill.

### Key Commands
```bash
# Activate environment first
source .venv/bin/activate

# Screening
python3 .claude/skills/screen-stocks/scripts/run_screen.py --region japan --preset alpha --top 10

# Individual report
python3 .claude/skills/stock-report/scripts/generate_report.py 7203.T

# Portfolio
python3 .claude/skills/stock-portfolio/scripts/run_portfolio.py snapshot

# Tests
python3 -m pytest tests/ -q

# Install / sync dependencies
uv sync
```

## Architecture

See [docs/architecture.md](docs/architecture.md) (3-layer structure · Mermaid diagram), [docs/neo4j-schema.md](docs/neo4j-schema.md) (graph schema), and [docs/skill-catalog.md](docs/skill-catalog.md) (8 skills) for details.

### Layer Overview
<!-- BEGIN AUTO-GENERATED ARCHITECTURE -->
```
Skills (.claude/skills/*/SKILL.md → scripts/*.py) — 9 skills
Core   (src/core/) — health/, portfolio/, ports/, research/, risk/, screening/, action_item_bridge (KIK-472: GraphRAG linking), action_item_detector (KIK-472: Linear integration), common, health_check (KIK-469: ETF support + PF integration), health_etf (KIK-469/512: ETF health check), health_labels (KIK-371/512: long-term suitability label generation), market_dashboard, models, proactive_engine (KIK-435), return_estimate (KIK-469 P2: volatility+is_etf), ticker_utils (KIK-449), value_trap (KIK-381)
Data   (src/data/) — context/ (KIK-517: context module consolidation), graph_query/ (KIK-508: submodule split), graph_query_pkg/, graph_store/ (KIK-507: submodule split), grok_client/ (KIK-508: submodule split), grok_client_pkg/, history/ (KIK-512/517: history store package), yahoo_client/ (KIK-449: submodule split, KIK-469: ETF fields), embedding_client (KIK-420: TEI vector search), lesson_community, lesson_conflict, linear_client (KIK-472), note_manager (KIK-473: journal type + auto symbol detection), user_profile
Output (src/output/) — adjust_formatter (KIK-496), analyze_formatter, forecast_formatter, formatter, health_formatter (KIK-469 P2: stock/ETF table split), portfolio_formatter, rebalance_formatter (KIK-376), research_formatter, review_formatter (KIK-441), screening_summary_formatter (KIK-452/532), simulate_formatter (KIK-376), stress_formatter

Config: config/screening_presets.yaml (16 presets), config/exchanges.yaml (60+ regions)
Rules:  .claude/rules/ (graph-context, intent-routing, workflow, development, screening, portfolio, testing)
Docs:   docs/ (architecture, neo4j-schema, skill-catalog, api-reference, data-models)
```
<!-- END AUTO-GENERATED ARCHITECTURE -->

## Post-Implementation Rule

**Always update documentation and rules after implementing a feature.** See "7. Documentation & Rule Updates" in `.claude/rules/workflow.md` for details.

Auto-generated: `docs/api-reference.md`, `CLAUDE.md` Architecture, `development.md` test count, `docs/skill-catalog.md` overview (auto-run by pre-commit hook)
Manual updates: `intent-routing.md`, relevant `SKILL.md`, `rules/*.md`, `README.md`
