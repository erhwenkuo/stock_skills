# Graph Context: Knowledge Graph Schema + Automatic Context Injection (KIK-411/420)

## Neo4j Knowledge Graph Schema

CSV/JSON are the master; Neo4j is a view for search and association (dual-write pattern). See `docs/neo4j-schema.md` for details.

**24 Nodes:**
Stock (central), Screen, Report, Trade, HealthCheck, Note, Theme, Sector,
Research, Watchlist, MarketContext, Portfolio,
News, Sentiment, Catalyst, AnalystView, Indicator, UpcomingEvent, SectorRotation,
StressTest, Forecast, ActionItem, Community, ThemeTrend

**Key Relations:**
- `Screen-[SURFACED]->Stock` / `Report-[ANALYZED]->Stock` / `Trade-[BOUGHT|SOLD]->Stock`
- `Portfolio-[HOLDS]->Stock` (current holdings, KIK-414) / `Watchlist-[BOOKMARKED]->Stock`
- `Research-[HAS_NEWS]->News-[MENTIONS]->Stock` / `Research-[HAS_SENTIMENT]->Sentiment`
- `Research-[HAS_CATALYST]->Catalyst` / `Research-[HAS_ANALYST_VIEW]->AnalystView`
- `Research-[SUPERSEDES]->Research` (new-old chain for the same subject)
- `MarketContext-[INCLUDES]->Indicator` / `MarketContext-[HAS_EVENT]->UpcomingEvent`
- `Note-[ABOUT]->Stock` / `Note-[ABOUT]->Portfolio` / `Note-[ABOUT]->MarketContext` (KIK-491)
- `Research-[ANALYZES]->Sector` / `Research-[COMPLEMENTS]->MarketContext` (KIK-491)
- `Stock-[IN_SECTOR]->Sector` / `Stock-[HAS_THEME]->Theme`
- `ActionItem-[TARGETS]->Stock` / `HealthCheck-[TRIGGERED]->ActionItem` (KIK-472)
- `Stock-[BELONGS_TO]->Community` (KIK-547: community detection)
- `ThemeTrend-[FOR_THEME]->Theme` (KIK-603: theme trend detection)

**Data Flow:** Skill execution → JSON/CSV save (master) → Neo4j sync (view) → retrieved via `get_context.py` on next run

---

## Automatic Context Injection

When the user's prompt contains a stock name or ticker symbol,
run the following script before skill execution to retrieve context.

## When to Run

**Every time.** As long as TEI + Neo4j are available, perform a vector similarity search on every prompt (KIK-420).

Additionally, combine with symbol-based search under the following conditions:
- Contains a ticker symbol (7203.T, AAPL, D05.SI, etc.)
- Contains a company name (Toyota, Apple, etc.) + analysis intent (how, look up, analyze, etc.)
- Contains "PF" or "portfolio" + status check intent
- Contains market inquiry intent (market conditions, situation, etc.)

### Hybrid Search (KIK-420)

| TEI | Neo4j | Behavior |
|:---|:---|:---|
| OK | OK | **Vector search every time** + symbol-based search |
| NG | OK | Symbol-based search only (as before) |
| OK | NG | As before (intent-routing only) |
| NG | NG | As before (intent-routing only) |

Even for ambiguous queries without symbols (e.g., "semiconductor-related stocks I looked up before"), vector search can retrieve related past nodes.

## Context Retrieval Command

```bash
python3 scripts/get_context.py "<user input>"
```

## How to Use Context

1. **Follow the action instruction on the first line of the output** (KIK-428):
   - `⛔ FRESH — No skill execution needed. Answer using this context only.` → Answer using context only, without running skills
   - `⚡ RECENT — Lightweight update in diff mode.` → Fetch diff only
   - `🔄 STALE — Full re-fetch. Run the skill.` → Run skill fully
   - `🆕 NONE — No data. Run the skill.` → Run skill fully
2. Refer to "Recommended Skill" as a reference alongside intent-routing.md for final skill selection
3. If previous values exist, make the output diff-aware
5. When Neo4j is not connected, output shows "no context" → make decisions using intent-routing only as before

## Context Freshness Assessment (KIK-427)

`get_context.py` output includes a freshness label (FRESH/RECENT/STALE/NONE), allowing the LLM to decide whether to re-fetch data.

### Freshness Labels

| Label | Criteria | LLM Action |
|:---|:---|:---|
| **FRESH** | Within `CONTEXT_FRESH_HOURS` (default 24h) | Answer using context only. Do not re-fetch API |
| **RECENT** | Within `CONTEXT_RECENT_HOURS` (default 168h=7 days) | Lightweight update in diff mode |
| **STALE** | Exceeds `CONTEXT_RECENT_HOURS` | Full re-fetch (re-run report/research) |
| **NONE** | No data | Run from scratch |

### Environment Variables

```bash
# Global thresholds (in hours)
CONTEXT_FRESH_HOURS=24      # Within this → FRESH
CONTEXT_RECENT_HOURS=168    # Within this → RECENT / Exceeds this → STALE
```

Default values (24h / 168h) are used when not set.

## Using Community Data (KIK-547/549/550)

When `get_context.py` output includes community membership information (`- Community: XX (N stocks)`), use it in the following situations.

### When to Reference

- **During stock analysis**: Present stocks in the same community as "related stocks"
- **During watchlist review**: If a watchlist stock is in the same community as an already-held stock, note "same group already held"
- **During portfolio diagnosis**: If `community_concentration` includes a warning, alert "concentrated in XX community"
- **During EXIT alternative proposals**: Same community = same risk, different community = diversification effect. Use appropriately based on objective

### Integration Rules

1. If community information exists, weave "same group: XX, YY" into the answer
2. During portfolio concentration warning: "N stocks concentrated in XX community (XX%). Consider diversifying to a different group"
3. If community name is `Community_N` (fallback name), it may be a hidden theme. Refer to News co-occurrence patterns
4. When Neo4j is not connected or communities not yet generated → hide section (graceful degradation)

## Skill Recommendation Priority

| Relationship | Recommended Skill | Reason |
|:---|:---|:---|
| Held stock (BOUGHT exists) | `/stock-portfolio health` | Diagnosis as holder takes priority |
| Thesis older than 3 months | `/stock-portfolio health` + review prompt | Timing for periodic reflection |
| EXIT judgment exists | `/screen-stocks` (same sector alternative) | Propose replacement |
| On watchlist (BOOKMARKED) | `/stock-report` + previous diff | Basis for buy timing decision |
| Appeared in screening 3+ times | `/stock-report` + attention flag | High attention from repeated top appearances |
| Recently researched (RECENT) | Diff only | Reduce API cost (auto-judged by freshness) |
| Concern memo exists | `/stock-report` + concern re-verification | Checking worries |
| Past data exists | `/stock-report` | Analysis with past context |
| Unknown stock | `/stock-report` | Research from scratch |
| Market inquiry | `/market-research market` | Reference market context |
| Portfolio inquiry | `/stock-portfolio health` | Full portfolio diagnosis |

## Integration with intent-routing.md

1. **graph-context first**: Retrieve context first and check recommended skill
2. **Final decision via intent-routing**: Cross-reference user intent and recommended skill for final decision
3. **Recommendations are reference only**: graph-context recommendations are merely suggestions. Explicit user intent takes priority

Example:
- graph-context: Held stock → health recommended
- User: "What's the latest news on 7203.T?"
- Final decision: User intent (news) takes priority → `/market-research stock 7203.T`
  However, "it is a held stock" is used as context

## Prior Knowledge Integration Principle (KIK-466)

After script execution, integrate `get_context.py` output (Neo4j knowledge) with skill output (numerical data) to compose the answer.
Don't just list numbers — add **interpretation** informed by accumulated context.

### 5 Integration Rules

1. **Don't just list numbers** — PER 8.5x → "Significant drop from 12.3x at last report. Check whether this is due to deteriorating earnings or undervaluation"
2. **Show diff from the past** — If previous data exists, always add a comparison comment (improved/deteriorated/flat)
3. **Reference investment memos** — If concern memos, theses, or targets exist, weave them into the answer (e.g., "Concern memo: China risk → signs of improvement in latest news")
4. **Use trade history** — If BOUGHT/SOLD records exist, add holder perspective comments ("currently held," "already sold," etc.)
5. **Graceful degradation** — When Neo4j is not connected, answer using skill output only (works without knowledge integration)
6. **Check history before proposing sell candidates (KIK-470)** — Before proposing a sell in what-if/swap, run `get_context.py` for that stock and check screening appearances, investment memos, and research history. Don't judge based on health check labels (EARLY WARNING, etc.) alone

### Prompting to Record Analysis Conclusions

After research, reports, or health checks where Claude provides an answer containing an analysis conclusion (thesis, concern, judgment), add a prompt at the end to record it:

> 💡 This analysis has not yet been recorded as an investment memo. Would you like to record it as a thesis/concern?

**Target**: market-research (stock/business/industry), stock-report, stock-portfolio health (EXIT/warning)
**Condition**: When Claude's answer contains a specific investment judgment, view, or risk assessment
**Not recorded**: Raw data lists, content the user has already recorded

**KIK-503: target memo → Linear issue integration**: After saving an investment memo with `type: target` (planned purchase/sale), prompt to register a Linear issue. See the record domain section in `intent-routing.md` for details

## Referencing Investment Lessons (KIK-534)

`get_context.py` output automatically includes an "## Investment Lessons" section. When notes of type=lesson contain a trigger (trigger condition) and expected_action (next action), they are displayed as context during skill execution.

### When to Reference

- **Before skill execution**: Automatically retrieved via `get_context.py`. When a symbol is specified, lessons for that symbol are shown; when no symbol, up to 5 lessons overall are shown
- **Judgment bias correction**: When a lesson's recorded failure pattern (trigger) matches the current situation, modify the judgment according to expected_action

### Correction Rules

1. When a lesson's trigger matches the current analysis subject/situation, **always incorporate that lesson into the answer**
2. Explicitly state "this is the same pattern as a past failure" and recommend the expected_action
3. When there are no lessons or none are applicable, hide the section entirely (graceful degradation)

### Example

```
## Investment Lessons
- [7203.T] Bought at high → Don't buy when RSI > 70 next time (2026-02-15)
- Jumped on momentum → Confirm volume before entering (2026-02-10)
```

→ When running a report for 7203.T, if RSI is above 70, warn "past lesson: high-price purchase risk"

## Grok Prompt Context Injection (KIK-488)

`src/data/grok_context.py` compactly extracts investor context (holding status, previous reports, theses, concerns, etc.) from Neo4j and injects it into the Grok API prompt.

- **Injection targets**: `researcher.py` → `grok_client.py` 5 search functions (stock_deep, x_sentiment, industry, market, business)
- **Token budget**: Max 300 tokens (~900 characters). Truncated line-by-line
- **Data priority**: Holding status (high) > Previous report (high) > Thesis/concern (high) > Screening appearances (medium) > Research history (medium) > Health check (medium) > Theme (low)
- **Graceful degradation**: When Neo4j is not connected → context="" → Grok operates normally without context

## Graceful Degradation

- When Neo4j is not connected: Script outputs "no context" → operates as usual
- When Neo4j is not connected (Grok context): `grok_context` returns empty string → no context in Grok prompt (KIK-488)
- When TEI is not running: Skip vector search → symbol-based search only (KIK-420)
- On script error: Ignore and judge using intent-routing only
- When symbol cannot be detected + TEI not running: "no context" → normal intent-routing
- When symbol cannot be detected + TEI running: Related nodes can be retrieved via vector search (KIK-420)

## Proactive Suggestions (KIK-435)

After skill execution, suggest the next action based on accumulated knowledge.

### Auto-Integration (KIK-465)

`print_context()` and `print_suggestions()` are built into each skill script, so context retrieval and suggestion display happen automatically during skill execution. No need to manually call `get_context.py` or `suggest.py`.

- At the start: `print_context()` automatically retrieves and displays graph context
- At the end: `print_suggestions()` automatically displays proactive suggestions
- 10-second timeout (SIGALRM)
- Graceful degradation when Neo4j is not connected or on error (no output, no crash)

### CLI Wrapper (for manual execution)

```bash
python3 scripts/suggest.py [--symbol <ticker>] [--sector <sector>]
```

- Up to 3 suggestions. urgency: high (red flag) > medium (needs attention) > low (reference)

**Trigger types:**

| Type | Trigger Condition | urgency |
|:---|:---|:---|
| Time | Health check not run for >14 days | medium (>30 days = high) |
| Time | Thesis memo older than >90 days | medium |
| Time | Earnings event within 7 days | high |
| State | Same stock appeared in top screening 3+ times | medium |
| State | Concern memo recorded | medium |
| Context | Research sector matches a held stock | low |
| Context | Keywords match in execution results (earnings, rate hike, EXIT, etc.) | low |
