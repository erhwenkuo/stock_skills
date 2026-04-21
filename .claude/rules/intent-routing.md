# Intent Routing: Natural Language Interface

This system automatically determines and executes the appropriate skill just by speaking in natural language.
Users do not need to know command names.

## Principles

1. **Prioritize the user's intent** — Infer intent from context, not keyword matching
2. **Ask when ambiguous** — When multiple skills could apply, briefly present options
3. **Carry over conversation flow** — Remember the stock or portfolio state from the previous exchange and fill in omitted information
4. **Chain multiple skills when needed** — If a single statement contains multiple intents, execute them in order and integrate results
5. **Leverage graph context** — Follow the rules in `graph-context.md` to retrieve past context before skill execution and use it as a basis for judgment

---

## Step 1: Domain Classification

First classify the user's statement into one of 8 domains.

| Domain | Intent | Representative Expressions |
|:---|:---|:---|
| **Discovery** | Want to find new stocks | Search, screening, good stocks, recommendations, undervalued stocks, high-dividend stocks |
| **Analysis** | Want to know about a specific stock/industry/market | How is XX, look up, analyze, research, news |
| **Portfolio Management** | Want to operate or check holdings | PF, portfolio, I bought, I sold, profit/loss, health check |
| **Risk** | Want to evaluate risk or the future | Crash, stress, risk, worried, hedge |
| **Monitoring** | Want to record stocks of interest | Watch, interested, monitor |
| **Recording** | Want to memo investment decisions | Memo, note, record, thesis, lessons learned, concerns |
| **Knowledge** | Want to search past analysis results | Last time, before, history, recurring stocks, repeated, market conditions |
| **Plan Mode** | Want to plan before executing | Plan mode, plan it, make a plan, plan and execute |
| **Meta** | Want to know about the system itself | What can it do, feature list, improvements, Kaizen |

---

## Step 2: Select Skill within Domain

### Discovery Domain → `/screen-stocks`

```
"Any good Japanese stocks?"          → /screen-stocks japan alpha
"Find US high-dividend stocks"        → /screen-stocks us high-dividend
"Dip stocks"                         → /screen-stocks japan pullback
"What's trending on X?"              → /screen-stocks japan trending
"Stocks to hold long-term"           → /screen-stocks japan long-term
"Undervalued tech stocks"            → /screen-stocks japan value --sector Technology
"Undervalued AI stocks"              → /screen-stocks us --theme ai --preset value
"Growth stocks in semiconductors"    → /screen-stocks us --theme ai --preset high-growth
"Find defense stocks"                → /screen-stocks us --theme defense --preset alpha
"Oversold stocks"                    → /screen-stocks japan contrarian
"Stocks that look oversold"          → /screen-stocks japan contrarian
"Excessively sold-off stocks"        → /screen-stocks japan contrarian
"Surging stocks"                     → /screen-stocks japan momentum
"Breakout detection"                 → /screen-stocks japan momentum
"Momentum stocks"                    → /screen-stocks japan momentum
```

**KIK-452 GraphRAG Context**: At the end of screening results, sector trends, investment memos, and theme information retrieved from the Neo4j knowledge graph are automatically displayed as structured data (Neo4j connection only). The Claude Code LLM interprets this structured data to generate an integrated summary (KIK-532: Grok API calls eliminated). This section is hidden when Neo4j is not connected; the screening itself is unaffected.

**Region inference**: Japan/JP → japan, US → us, ASEAN → asean, Singapore → sg, Hong Kong → hk, Korea → kr, Taiwan → tw, China → cn, not specified → japan

**Preset inference**:

| User Expression | Preset |
|:---|:---|
| Good stocks, recommendations, promising | alpha |
| Undervalued, value, low P/E | value |
| High dividend, good dividend | high-dividend |
| Growth, high growth, growth rate focused | growth |
| Growth value, growth + undervalued | growth-value |
| Super undervalued, deep value | deep-value |
| Quality, high quality | quality |
| Dip, correcting, good stocks that are down | pullback |
| Trending, trending on X, SNS, buzzing | trending |
| Long-term, steady, stable growth, buy & hold | long-term |
| Shareholder return, buyback, total return | shareholder-return |
| Stable steady returns, continued high returns | shareholder-return (recommend ✅/📈 stocks) |
| Explosive growth, high-growth, loss-making growth stocks, PSR-focused, rapid revenue growth | high-growth |
| Small-cap growth, micro-cap, 10-bagger candidates, small-cap rapid growth | small-cap-growth |
| Contrarian, oversold, overreaction, bottoming, rebound play | contrarian |
| Surge, breakout, momentum, strong uptrend | momentum |
| Market darlings, growth with high P/E, growth premium, high-P/E growth | market-darling |
| Not specified | alpha |

**KIK-439 Related (Theme Screening)**:
- Theme + preset: use `--theme <theme>` combined with a preset
- "AI stocks", "semiconductors", "AI-related" → `--theme ai`
- "EV", "electric vehicles", "next-gen automotive" → `--theme ev`
- "Cloud", "SaaS" → `--theme cloud-saas`
- "Cybersecurity", "security stocks" → `--theme cybersecurity`
- "Biotech", "drug discovery" → `--theme biotech`
- "Renewable energy", "solar" → `--theme renewable-energy`
- "Defense", "military", "aerospace" → `--theme defense`
- "Fintech", "financial tech" → `--theme fintech`
- "Healthcare", "medical devices" → `--theme healthcare`
- Combination example: "undervalued AI stocks" → `--theme ai --preset value`, "semiconductor growth stocks" → `--theme ai --preset high-growth`
- `trending`/`pullback`/`alpha` presets do not support `--theme` (other presets only)

**KIK-440 Related (Automatic Trend Theme Detection)**:
- "What themes are hot?" "trending themes" "noteworthy sectors" → `--auto-theme` (Grok auto-detects themes)
- "Which sectors are hot now?" → `--auto-theme` (theme list + screening)
- "What should I buy in this market?" → `--auto-theme` (theme detection + default preset)
- "Undervalued stocks in trending themes" → `--auto-theme --preset value`
- "Growth stocks in noteworthy themes" → `--auto-theme --preset high-growth`
- `--auto-theme` and `--theme` are mutually exclusive
- `--auto-theme` is incompatible with `trending`/`pullback`/`alpha` presets
- `XAI_API_KEY` is required (Grok API for theme detection)
- Difference: `trending` = detects trending **individual stocks** on X, `--auto-theme` = detects trending **themes/sectors** and finds quality stocks in each theme

### Analysis Domain → `/stock-report` or `/market-research`

**Decision criteria**: Quantitative vs. qualitative analysis

| User Intent | Skill | Judgment Basis |
|:---|:---|:---|
| Valuation, undervaluation, P/E/P/B, return rate | `/stock-report` | Number-based analysis |
| Latest news, sentiment, deep dive | `/market-research stock` | Qualitative deep dive |
| Industry trends | `/market-research industry` | Industry name/theme as subject |
| Market overview, market conditions | `/market-research market` | Overall market as subject |
| Market check, temperature, VIX, F&G, rate trends, yield curve | Quantitative + qualitative simultaneously | See KIK-567 below |
| Business model, business structure, segments, revenue structure, how they make money | `/market-research business` | Business mechanism as subject |
| Past analysis results, previous reports, past screenings | `/graph-query` | Reference to past data (link to knowledge domain) |
| Similar stocks, related stocks, same group | `/graph-query` | Community search (KIK-547) |

**When uncertain**:
- "How is XX?" "Look up XX" → `/stock-report` (start with numbers)
- "Deep dive XX" "Latest on XX" "XX news" → `/market-research stock`
- "XX's business model" "How does XX make money?" "Explain the business structure" → `/market-research business`
- "Tell me more about XX" → Run both and produce an integrated report

**KIK-567 Related (Market Check — Quantitative + Qualitative)**:
- "Market check", "market temperature", "VIX?", "F&G?", "rate trends", "yield curve" → Run 2 simultaneously:
  1. `python3 scripts/market_dashboard.py` (quantitative: VIX/F&G/rates/yield curve)
  2. `/market-research market` (qualitative: news/sentiment via Grok)
  → Claude integrates both outputs to answer
- "Just show me VIX", "rate trends" → `python3 scripts/market_dashboard.py` only (quantitative only)
- "Market news", "latest market view" → `/market-research market` only (qualitative only)

**KIK-375 Related**:
- "Return rate", "buyback", "shareholder return", "total return" → `/stock-report` (displayed in shareholder return section)

**KIK-380 Related**:
- "Past return rate", "3-year return trends", "return history" → `/stock-report` (displayed in 3-year return rate history)

**KIK-383 Related**:
- "Stocks with stable returns", "consistently high returns" → `/screen-stocks --preset shareholder-return` (with stability marks)
- "Temporary high return?", "Will returns really continue?" → `/stock-report` (displayed in stability assessment)
- Stocks marked ⚠️ in screening results may have temporary high returns

**KIK-469 Related (ETF Support)**:
- "How is VGK?", "Look up SPY", "What's this ETF's expense ratio?" → `/stock-report` (auto-detects ETF → ETF-specific report)
- For ETFs, expense ratio, AUM, and fund size are shown instead of P/E/P/B/ROE
- ETF-specific assessments (expense ratio label, AUM label) are also shown in health checks

### Portfolio Management Domain → `/stock-portfolio`

**KIK-596 Related (Investment Decision Multi-Agent)**:
- For statements involving **execution** of replacement proposals, new purchase decisions, sell decisions, rebalancing, or adjustment advice, apply the Plan→Execute→Review flow in `.claude/rules/plan-check.md`
- Information queries like "show me the PF" or "what's the P/L?" and records like "I bought" are excluded
- Judgment: The statement ends with an action request like "want to ~", "should ~?", "find ~", "fix ~"
- First run `python3 scripts/extract_constraints.py "<user input>"` to extract constraint conditions from lessons, then formulate a plan

**Subcommand determination**:

| User Intent | Command |
|:---|:---|
| **Status check**: Show PF, P/L, snapshot | `snapshot` |
| **Trade recording**: Bought/sold XX | `buy` / `sell` |
| **List display**: Stock list, list, CSV | `list` |
| **Structural analysis**: Bias, concentration, HHI, sector ratio, size composition, large/small ratio | `analyze` |
| **Health**: Health check, take profit, stop-loss, should I still hold?, small-cap ratio, small-cap allocation | `health` |
| **Future outlook**: Expected return, yield, future prospects, forecast | `forecast` |
| **Rebalancing**: Improve balance, allocation adjustment, fix bias | `rebalance` |
| **Simulation**: In N years, compound interest, accumulation, retirement, target amount | `simulate` |
| **Back-testing**: Backtest, verify, past performance | `backtest` |
| **What-If**: What if I add, what happens if I buy, impact, add simulation | `what-if` |
| **Performance review**: Trade performance, win rate, P/L stats, what % did I get | `review` |
| **Adjustment advice**: What should I sell?, how to fix?, what specifically should I do?, prescription, adjustment plan, what should I do, advice, improve, fix, countermeasures, take action, action plan, next action, issues and countermeasures | `adjust` |
| **Trade → Record**: Want to record the reason for buying, memo the investment rationale | `buy` → `/investment-note save --type thesis` |
| **Stop-loss → Lesson**: Record the lesson from a stop-loss, reflection memo | `sell` → `/investment-note save --type lesson` |

**KIK-376 Related**:
- "What happens if I add XX?", "How will the PF change if I buy XX?", "Impact?" → `what-if`
- Format: `what-if --add "SYMBOL:SHARES:PRICE,..."` e.g., `what-if --add "7203.T:100:2850,AAPL:10:250"`

**KIK-451 Related (Swap Simulation)**:
- "What if I sell XX and buy YY?", "What if I switch?", "Replacement simulation" → `what-if --remove --add`
- "How much money would I get if I sell XX?", "Sell simulation", "How would the PF change if I let go of XX?" → `what-if --remove`
- Format:
  - Swap: `what-if --remove "SYMBOL:SHARES,..." --add "SYMBOL:SHARES:PRICE,..."`
  - Sell only: `what-if --remove "SYMBOL:SHARES,..."` (no price needed — calculated at market value)
- Example: `what-if --remove "7203.T:100" --add "9984.T:50:7500"`
- Swap output: Estimated sale proceeds / Fund balance (difference) / Health check of sold stock / Judgment like "this swap is recommended"

**KIK-374 Related**:
- "Golden cross", "dead cross", "cross" → `health` (displayed in cross event detection)

**KIK-381 Related**:
- "Value trap", "value trap?", "check if it's a value trap" → `health` (displayed in value trap detection)
- Individual stock value trap assessment is also shown in `/stock-report`

**KIK-403 Related**:
- "Return stability", "temporary high return", "will returns continue?" → `health` (displayed in return stability assessment)
- Temporary high returns (⚠️) in health checks are escalated to early warning
- Long-term suitability uses total return rate (dividends + buybacks)

**KIK-438 Related (Small-Cap Allocation)**:
- "Small-cap ratio", "small-cap allocation", "small-cap proportion", "too many small caps?" → `health` (displayed in small-cap ratio summary)
- "Size composition", "large/small ratio", "market cap balance" → `analyze` (displayed in size composition table)
- Small caps in health check get a `[small]` badge + automatic EARLY_WARNING→CAUTION escalation
- Portfolio-wide small-cap ratio: >25% warning, >35% critical

**Natural language conversion for buy/sell**:
- "I bought 100 shares of Toyota at 2850" → `buy --symbol 7203.T --shares 100 --price 2850 --currency JPY`
- "I sold 5 shares of AAPL" → `sell --symbol AAPL --shares 5`
- "I sold 5 shares of NVDA at $138" → `sell --symbol NVDA --shares 5 --price 138`
- Convert company names to ticker symbols

**KIK-444: buy/sell confirmation step**:
- Running without `--yes` displays a confirmation preview and the command ends (no recording)
- After confirmation "record it", "OK", "yes" → re-run with `buy --yes` / `sell --yes`
- "Record without confirmation", "just enter it" → run with `--yes` from the start

**KIK-441: Sell price confirmation flow**:
- When the user says "I sold" and the price is not specified, ask: "Could you tell me the sale price? I can record the realized profit/loss. (It's also OK to skip.)"
- With price → run `sell --symbol ... --shares ... --price <price>`
- Skip → run `sell --symbol ... --shares ...` (no price)

**KIK-441: Natural language conversion for the review command**:
- "I want to see my trade performance", "What's my win rate?", "P/L stats", "What % did I get?" → `review`
- "This year's performance" → `review --year <current year>`
- "NVDA trade performance" → `review --symbol NVDA`

**KIK-568: Natural language determination for adjust**:
- "What should I do with the PF?", "PF advice", "Improve the PF", "PF countermeasures", "take action" → `adjust` (can be run directly even without health)
- Decision criteria vs health: "improve", "countermeasures", "advice", "fix", "what should I do", "what should I do about it", "action" → adjust priority. "Check", "confirm", "diagnose", "is it OK?" → health

**Rebalancing strategy inference**:
- "I want to reduce risk" → `--strategy defensive`
- "I want to be more aggressive" → `--strategy aggressive`
- "I want to fix tech overweight" → `--reduce-sector Technology`

**Simulate parameter inference**:
- "How much in 5 years?" → `--years 5`
- "If I add 100K per month for 3 years, can I reach 20M?" → `--years 3 --monthly-add 100000 --target 20000000`

### Risk Domain → `/stress-test`

```
"What happens in a crash?"            → /stress-test (auto-retrieves stocks from PF)
"What about yen weakness risk?"       → /stress-test --scenario USD/JPY surge
"Can it survive a tech crash?"        → /stress-test --scenario tech crash
```

**PF integration**: When a portfolio exists, the stock list is automatically retrieved for execution

**Scenario inference**: Triple meltdown, USD/JPY surge, US recession, BOJ rate hike, US-China conflict, inflation resurgence, tech crash, JPY appreciation + custom

### Monitoring Domain → `/watchlist`

```
"Record it because I'm interested"    → /watchlist add
"Show me the watchlist"               → /watchlist list
```

### Recording Domain → `/investment-note`

```
"Memo about Toyota"                           → /investment-note save --symbol 7203.T
"Record the investment thesis"                → /investment-note save --type thesis
"Leave a lesson"                              → /investment-note save --type lesson
"Memo for the whole PF", "PF retrospective"   → /investment-note save --category portfolio --type review
"Market memo", "macro insight"                → /investment-note save --category market --type observation
"Memo list"                                   → /investment-note list
"AAPL memos"                                  → /investment-note list --symbol AAPL
"PF memos"                                    → /investment-note list --category portfolio
"Delete memo"                                 → /investment-note delete --id NOTE_ID
"Diary", "investment diary", "today's review" → /investment-note save --type journal
"No trading this week", "no trade"            → /investment-note save --type journal --content ...
"Thoughts", "musings"                         → /investment-note save --type journal
```

**Type inference**:

| User Expression | type |
|:---|:---|
| Thesis, hypothesis, investment rationale | thesis |
| Insight, observation | observation |
| Concern, worry, risk | concern |
| Retrospective, review | review |
| Target price, target | target |
| Lesson, reflection, teaching | lesson |
| Stop-loss line, take-profit line, stop loss, take profit, exit criteria | exit-rule |
| Diary, journal, retrospective diary, free memo, thoughts, musings | journal |

**KIK-503: Prompt to register Linear issue after saving a target memo**:

After running `/investment-note save --type target`, display the following prompt at the end:

> 📋 Would you like to also register this plan as a Linear issue? (Investment Checkpoints project)

- User says "yes" or "register" → Create issue via MCP (`mcp__claude_ai_Linear__create_issue`)
  - team: `Kikuchi`
  - project: `Investment Checkpoints`
  - title: Summary from memo content (e.g., "7203.T Purchase Review — Target Price 3000 JPY")
  - description: Full memo text
  - priority: 3 (Normal)
- User says "not needed" or "skip" → Do nothing
- **Only for `target` type**. Do not prompt for thesis/concern/review/lesson/journal/observation

### Knowledge Domain → `/graph-query`

```
"Previous report on 7203.T?"               → /graph-query "7203.T previous report"
"Stocks that repeatedly come up?"          → /graph-query "recurring candidates"
"AAPL research history"                    → /graph-query "AAPL research history"
"Recent market conditions?"                → /graph-query "market conditions"
"7203.T trade history"                     → /graph-query "7203.T trade history"
"NVDA news history"                        → /graph-query "NVDA news history"
"NVDA sentiment trend"                     → /graph-query "NVDA sentiment trend"
"NVDA catalysts"                           → /graph-query "NVDA catalysts"
"7203.T P/E trend"                         → /graph-query "7203.T P/E trend"
"Upcoming events"                          → /graph-query "upcoming events"
"Macro indicator trends"                   → /graph-query "macro indicator trends"
"Previous stress test results"             → /graph-query "stress test history"
"Forecast trend"                           → /graph-query "forecast trend"
"Previous outlook"                         → /graph-query "previous outlook"
"Action items"                             → /graph-query "action items"
"Task list"                                → /graph-query "action items"
"What should I do?"                        → /graph-query "action items"
"7203.T actions"                           → /graph-query "7203.T action items"
"Stocks similar to 7203.T?"               → /graph-query "7203.T community"
"Show me similar stocks"                   → /graph-query "stock community"
"Stocks in the same group"                 → /graph-query "community"
"Related stocks"                           → /graph-query "community"
"What do these stocks have in common?"     → /graph-query "stock relationships"
"Theme trends"                             → /graph-query "theme trend history"
"Previous trending themes"                 → /graph-query "theme trend history"
"Which themes were hot?"                   → /graph-query "theme trend history"
```

**Trigger**: "previous", "before", "history", "recurring", "repeated", "market context", "news", "sentiment", "catalyst", "material", "valuation trends", "events", "indicators", "stress test results", "forecast trends", "outlook", "action items", "tasks", "what to do", "similar stocks", "related stocks", "community", "same group", "cluster", "theme trend", "theme history", etc.

### Plan Mode Domain → `/plan-execute` (KIK-600)

When the user says "in plan mode", "plan it", "make a plan", etc., activate the `/plan-execute` skill.

- Plan mode can be combined with all domains
- "Check the PF, in plan mode" → /plan-execute (design and execute PF check plan)
- "Look up Toyota, plan mode" → /plan-execute (design and execute research plan)
- "Improve the PF, plan mode" → /plan-execute → escalate to Plan-Check

**Note**: When a skill is directly specified (e.g., `/stock-report 7203.T`), skip planning and execute immediately.

### Meta Domain — Questions About the System Itself

When the user asks about how to use skills or the system's features, refer to the following to answer.

**"What can it do?", "Feature list", "How to use"**:

```
This system can do the following in natural language:

🔍 Find Stocks
  "Any good Japanese stocks?" "Find US high-dividend stocks" "Trending stocks"
  → Screening across 14 strategies × 60 regions

📊 Analyze Stocks
  "How is Toyota?" "What's AAPL's return rate?"
  → Valuation, undervaluation, shareholder return rate
  → 3-year shareholder return history (dividends + buybacks)
  → Value trap assessment (low P/E + declining earnings warning)

📰 Deep Research
  "Look up the semiconductor industry" "What's the market like now?"
  → Latest news, X sentiment, industry trends via Grok API

💼 Portfolio Management
  "Show me the PF" "I bought 100 Toyota shares" "Health check"
  → P/L display, trade recording, structural analysis, health check
  → Golden Cross/Dead Cross detection
  → Value trap detection (low P/E + declining earnings warning)
  → Shareholder return stability assessment (✅stable/📈increasing/⚠️temporary/📉declining)
  → Small-cap allocation monitoring ([small] badge, ratio warning, sensitivity escalation)
  → Estimated yield, rebalancing, compound interest simulation

⚡ Risk Analysis
  "What happens in a crash?" "What about yen weakness risk?"
  → 8 scenarios × correlation analysis × VaR × recommended actions

👀 Watchlist
  "Record it because I'm interested" "Show me the monitoring list"

📝 Investment Memos
  "Memo about Toyota" "Record the lesson" "Memo list"
  → Record and reference investment theses, concerns, and lessons as notes

🔎 Knowledge Graph Search
  "What was the previous report?" "Recurring stocks?" "Recent market conditions?"
  → Search past analysis, screenings, and trade history in natural language
```

**"Any improvements?", "Kaizen", "System weaknesses"**:

Analyze the system from the following perspectives and output improvement proposals:
1. Read all SKILL.md files, confirm coverage and implementation status
2. Cross-reference `src/core/` module list with usage from each skill
3. Identify areas with thin test coverage
4. Detect missing keywords in intent-routing
5. Check incomplete Linear issues
6. Organize proposals by category (new features/UX improvements/bug fixes/documentation) × priority (High/Medium/Low)

Create a Linear issue if the proposal is agreed upon.

---

## Context Carry-Over Rules

When a specific stock or operation result appears in the previous conversation, fill in omitted information.

| Previous Action | User Statement | Inference |
|:---|:---|:---|
| Ran `/stock-report 7203.T` | "Add to watchlist" | → `/watchlist add <list> 7203.T` |
| Ran `/stock-report 7203.T` | "Tell me more" | → `/market-research stock 7203.T` |
| Ran `/stock-report 7203.T` | "Run a stress test" | → `/stress-test --portfolio 7203.T` |
| After `/screen-stocks` result | "Look up the #1 stock" | → `/stock-report <#1 symbol>` |
| EXIT in `/stock-portfolio health` | "Find an alternative" | → `/screen-stocks` (same sector/region) |
| After `/stock-portfolio forecast` | "I want to see the simulation too" | → `/stock-portfolio simulate` |
| Value trap detected in `/stock-portfolio health` | "I want to see more detail" | → `/stock-report <relevant stock>` |
| ⚠️ in `/screen-stocks shareholder-return` result | "Tell me more about the ⚠️ stock" | → `/stock-report <relevant stock>` |
| After `/screen-stocks shareholder-return` result | "I only want to see stable ones" | → Filter ✅/📈 from results |
| After purchase recorded with `/stock-portfolio buy` | "Memo it", "record the investment rationale" | → `/investment-note save --symbol <stock> --type thesis --content ...` |
| EXIT judgment in `/stock-portfolio health` | "Record the lesson", "reflection memo" | → `/investment-note save --symbol <stock> --type lesson --content ...` |
| EXIT judgment in `/stock-portfolio health` | "What specifically should I do?", "Give me a prescription", "What should I do", "Improve it", "Advice" | → `/stock-portfolio adjust` |
| EXIT judgment in `/stock-portfolio health` | "I want to sell and switch", "What happens if I buy the alternative?" | → `what-if --remove "<EXIT stock>:SHARES" --add "<alternative>:SHARES:PRICE"` |
| After `what-if --remove` | "Find an alternative", "Look for a replacement" | → `/screen-stocks` (same sector) |
| Past report shown via `/graph-query` | "I want to see the latest too", "How is it now?" | → `/stock-report <stock>` |
| Memos shown via `/investment-note list` | "Look up this stock" | → `/stock-report <stock>` |
| Report generated with `/stock-report` | "Memo the concerns" | → `/investment-note save --symbol <stock> --type concern --content ...` |
| After `/screen-stocks` results | "Has it come up before?", "Is it a recurring candidate?" | → `/graph-query "frequently appearing stocks"` |
| Ran `/stock-report 7203.T` | "Similar stocks?", "Stocks in the same group" | → `/graph-query "7203.T community"` |
| Community concentration warning in `/stock-portfolio health` | "How to fix?", "I want to diversify" | → Confirm community members → propose alternative candidates from a different community |

---

## Multi-Intent Auto-Chaining

When a single statement contains multiple intents, execute them in an appropriate order and integrate the results.

**Patterns are not fixed** — the following are representative examples; combine flexibly based on user intent.

### Diagnose → Countermeasure
```
"Check PF risks, if there are problematic stocks find alternatives"
→ 1. /stock-portfolio health
→ 2. If EXIT stocks exist, search for alternatives with /screen-stocks
→ 3. If alternative candidates found, run what-if --remove "<EXIT stock>:SHARES" --add "<alternative>:SHARES:PRICE" before proposing (KIK-450)
```

### Trade → Confirm
```
"I bought 100 Toyota shares, check the balance"
→ 1. /stock-portfolio buy
→ 2. /stock-portfolio analyze
```

### Full Diagnosis
```
"Do a comprehensive PF check"
→ 1. /stock-portfolio snapshot (current status)
→ 2. /stock-portfolio health (health)
→ 3. /stock-portfolio forecast (outlook)
→ 4. If issues found, improvement plan with /stock-portfolio rebalance
```

### Research → Investment Decision
```
"Look up the semiconductor industry and find promising stocks"
→ 1. /market-research industry semiconductors
→ 2. /screen-stocks --sector Technology
```

### Market Check → PF Judgment
```
"Check the current market, see if the PF is OK"
→ 1. /market-research market
→ 2. /stock-portfolio health
→ 3. Supplement with judgment informed by market environment
```

### Outlook → Future Projection
```
"Check the PF outlook and simulate 5 years out"
→ 1. /stock-portfolio forecast
→ 2. /stock-portfolio simulate --years 5
```

### Trade → Record
```
"I bought 100 Toyota shares, also memo the reason"
→ 1. /stock-portfolio buy --symbol 7203.T --shares 100 --price ...
→ 2. /investment-note save --symbol 7203.T --type thesis --content ...
```

### Research → Record
```
"Look up Toyota and memo what I'm concerned about"
→ 1. /stock-report 7203.T
→ 2. /investment-note save --symbol 7203.T --type observation --content ...
```

### Knowledge Graph → Latest Analysis
```
"Check the latest status of the stocks I looked up before"
→ 1. /graph-query "stocks I looked up before"
→ 2. Run /stock-report on the resulting stocks
```

---

## Handling Ambiguous Cases

When intent is unclear, briefly present options and confirm.

```
User: "About dividends"

→ Which meaning?
  1. Find high-dividend stocks (screening)
  2. Check dividends/return rate for a specific stock (report)
  3. Check portfolio dividend yield (forecast)
```

```
User: "Check if it's a value trap"

→ Depends on the target:
  1. All holdings → /stock-portfolio health (with value trap detection)
  2. A specific stock → /stock-report (individual value trap assessment)
```

```
User: "Show me the memos"

→ Which meaning?
  1. Memos for a specific stock → /investment-note list --symbol <stock>
  2. All memos → /investment-note list
  3. Past analysis records → /graph-query "past reports"
```

However, when the answer is obvious from context, execute without asking for confirmation.
