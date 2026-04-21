---
name: market-research
description: "Deep research on stocks, industries, markets, and business models. Integrates Grok API (X/Web search) and yfinance for multi-angle analysis reports."
argument-hint: "[stock|industry|market|business] [target]  e.g.: stock 7203.T, industry semiconductors, market nikkei, business 7751.T"
allowed-tools: Bash(python3 *)
---

# Deep Research Skill

Parse $ARGUMENTS to determine research type and target, then run the following command.

## Execution Command

```bash
python3 /Users/kikuchihiroyuki/stock-skills/.claude/skills/market-research/scripts/run_research.py <command> <target>
```

## Natural Language Routing

For natural language → skill selection, see [.claude/rules/intent-routing.md](../../rules/intent-routing.md).

## Output by Research Type

### stock (stock research)
- Basic info + valuation (yfinance)
- Latest news (yfinance)
- X sentiment (Grok API)
- Deep analysis: news, earnings catalysts, analyst views, competitive comparison (Grok API)

### industry (industry research)
- Trends, key players, growth drivers, risks, regulatory landscape (Grok API)

### market (market overview)
- Price movement, macro factors, sentiment, notable events, sector rotation (Grok API)

### business (business model analysis)
- Business overview (how the company makes money)
- Business segment breakdown (segment names, revenue share, overview)
- Revenue model (recurring/transactional/subscription, etc.)
- Competitive advantages (entry barriers, brand, technology, moat)
- Key KPIs (metrics investors should focus on)
- Growth strategy (mid-term business plan, M&A, new businesses)
- Business risks (structural risks, dependencies)

## About the APIs

### Grok API
- Only uses Grok API when `XAI_API_KEY` environment variable is set
- When not set, generates report from yfinance data only (for `stock`)

### 2-Layer Structure
1. **Layer 1 (yfinance)**: Always available (fundamentals, price data)
2. **Layer 2 (Grok API)**: When `XAI_API_KEY` is set (X posts, web search for deep analysis)

- industry / market / business require Layer 2. Displays a message when not set

### API Status Summary (KIK-431)

Displays Grok API status at the end of each report:

| Status | Display |
|:-----|:-----|
| Normal | ✅ OK |
| Not set | 🔑 Not set — Set XAI_API_KEY to enable |
| Auth error | ❌ Auth error (401) — Check your XAI_API_KEY |
| Rate limit | ⚠️ Rate limited (429) — Wait and retry |
| Timeout | ⏱️ Timeout — Check network connection |
| Other error | ❌ Error — Check stderr for details |

## Output Supplement

After displaying the script output as-is, Claude should add:

### For stock
- Check consistency between fundamentals data and Grok research
- Point out any divergence between value score and market sentiment
- Add additional context relevant to investment decisions

### For industry
- Supplement Japan-specific circumstances (regulatory environment, entry barriers, etc.)
- Suggest related stock screening (/screen-stocks integration)

### For market
- Estimate impact on portfolio (/stock-portfolio integration)
- Mention comparable past cases if available

### For business
- Consider relationship between segment composition and stock valuation
- Revenue model sustainability (recurring is stable, transactional has higher cyclicality, etc.)
- Confirm whether competitive advantages appear in actual financial metrics (ROE, margins, etc.)
- Supplement fundamentals consistency using `/stock-report` results

## Execution Examples

```bash
# Stock research
python3 .../run_research.py stock 7203.T
python3 .../run_research.py stock AAPL

# Industry research
python3 .../run_research.py industry semiconductors
python3 .../run_research.py industry "Electric Vehicles"

# Market research
python3 .../run_research.py market nikkei
python3 .../run_research.py market "S&P500"

# Business model analysis
python3 .../run_research.py business 7751.T
python3 .../run_research.py business AAPL
```

## Knowledge Integration Rules (KIK-466)

When `get_context.py` output contains the following, integrate with research results:

- **Relation to held stocks**: If the research target sector includes PF holdings, "7203.T is affected → health check recommended"
- **Past research (SUPERSEDES)**: Compare with previous research on the same target. "2 weeks ago: neutral sentiment → now: slightly bullish"
- **Investment notes**: If there are concerns or thesis for the target stock, cross-check with research results and suggest updates
- **Watchlist**: If the research target is on the watchlist, add context: "Watching → material for buy timing decision"

### Prompting to Record Analysis Conclusions

When a response for stock/business/industry research contains specific investment opinions or thesis-level conclusions:
> 💡 This analysis has not yet been recorded as an investment note. Would you like to record it as a thesis or concern?
