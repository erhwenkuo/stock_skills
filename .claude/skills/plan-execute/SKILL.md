---
name: plan-execute
description: Plan Mode — Orchestrator oversees workflow design, execution, autonomous loop, and review. Activated when told "in plan mode."
user_invocable: true
---

# Plan-Execute Skill v2 (KIK-609)

The Orchestrator leads a 7-agent team to carry out workflow design → execution → autonomous loop → review.

## Trigger

Phrases such as "in plan mode," "plan it," "make a plan," "execute in plan mode," etc.

## Agent Configuration (7 agents)

| Agent | Type | Role | Participation |
|:---|:---|:---|:---|
| **Orchestrator** | Parent + Facilitator | Plan formulation, execution instructions, result evaluation, autonomous loop judgment, review integration | Always |
| **Context Analyst** | Execution support | Pre-analyzes historical context of financial markets + macro environment as a unit (leverages LLM knowledge) | On investment decisions |
| **Strategist** | Plan | Workflow design. Designs options from 4 perspectives: Growth / Value / Macro / Contrarian | Always |
| **Lesson Checker** | Plan | Checks whether past lessons (constraints) are reflected in the workflow | Always |
| **Devil's Advocate** | Plan | Points out blind spots, biases, oversights, and contrarian perspectives | Always |
| **Quantitative Reviewer** | Review | Quantitative checks + Gate Keeper function (numerical consistency, tax costs, currency allocation, lot size, constraint satisfaction, confirmation that all steps were executed) | Always |
| **Qualitative + Risk Reviewer** | Review | Qualitative checks (thesis alignment, respecting conviction, catalysts) + risk (geopolitical, macro, market overheating, PF structure, stock-specific) | Always |

### Orchestrator Rules

- **Quantitative basis requirement**: When rejecting an agent's input, always provide quantitative justification. "Feels small" or "impact is limited" are prohibited. Show PF ratios and comparisons against thresholds as numbers.
- **Autonomous progression**: Phase transitions proceed without user confirmation. Confirmation is only required for action execution approval in Phase 6.
- **Progress display**: Display a one-line progress update to the user at the start of each Phase:
  ```
  [1/6] Retrieving context...
  [2/6] Designing workflow...
  [3/6] Executing analysis...
  [4/6] Evaluating results (autonomous loop)...
  [5/6] Reviewing...
  [6/6] Generating final report...
  ```

## Execution Flow

### Phase 1: Pre-Plan

1. Run `python3 scripts/get_context.py "<user input>"` to retrieve graph context
2. Run `python3 scripts/extract_constraints.py "<user input>"` to get lesson constraints (when an investment decision is possible)
3. Reference user assumptions from `config/user_profile.yaml` (use defaults if file does not exist)
4. If an investment decision is involved → have **Context Analyst** retrieve historical context of financial markets
5. **Recent event scan**: Pre-check earnings dates and catalysts for held stocks via WebSearch or yfinance. If any stock has earnings within 7 days, instruct Phase 2 Strategist to "design workflow considering earnings timing."
6. **Individual context retrieval for target stocks**: In addition to the full PF query, run `get_context.py` for each stock likely to be an action target to retrieve past memos, theses, and lessons.

#### Context Analyst Perspectives

| Category | Examples |
|:---|:---|
| Market cycle | "Fed rate hikes in 2022 caused growth stocks -30%"; "15 months after hike pause: +15%" |
| Theme history | "AI theme started in 2023, bubble concerns in 2024, re-evaluated on real demand in 2025" |
| Bubble patterns | "Dot-com bubble (2000) P/E >100 vs. current AI semiconductor P/E >100" |
| Geopolitical precedents | "2018 US-China trade war: AMZN -20%"; "2022 Russia-Ukraine: energy surge" |
| F&G history | "Average correction after F&G >80 sustained for 1 month: -8%, recovery 45 days" |
| Rate cycle | "Between rate hike pause and first cut, equities historically perform well" |

### Phase 2: Plan (3 agents in parallel)

Launch Strategist + Lesson Checker + Devil's Advocate in parallel.

#### Strategist's 4 Perspectives

The Strategist designs the workflow from 4 perspectives (not separate agents — one agent with 4 perspectives):

- **Growth perspective**: EPS growth rate, theme early-stage signals, Forward PER
- **Value perspective**: P/E, P/B, undervaluation score, dividend yield
- **Macro perspective**: Rate cycle, F&G, sector rotation
- **Contrarian perspective**: Is the analysis being swept along by consensus? Any oversights?

#### Strategist's Additional Required Perspectives

- **Cash-equivalent inventory**: For MMFs and short-term bond ETFs (SHV, etc.) in the PF, consider "continue holding (secure yield) vs. liquidate (improve flexibility)." Especially important in cash-preservation strategies.
- **ETF action candidates**: ETFs like GLDM/JEPI/SHV are also considered as action targets (even if health check shows "no issues," they can be sell candidates if not needed strategically).
- **Role classification of all PF holdings**: Classify as risk assets / safe assets / cash equivalents and explicitly state "reason to hold" for stocks not targeted for action.

The Orchestrator integrates results from the 3 agents and revises the workflow if Lesson Checker returns FAIL (up to 2 times).

### Phase 3: Execute

Execute skills/scripts sequentially according to the plan.

### Phase 4: Result Evaluation + Autonomous Loop

The Orchestrator evaluates execution results and autonomously performs additional execution and plan revisions as needed.

| Evaluation Result | Action |
|:---|:---|
| No issues | Proceed to Phase 5 (Review) |
| Information gap detected | Run additional scripts pinpoint → return to Phase 4 |
| New fact revealed (earnings date, etc.) | Revise plan → return to Phase 3 |
| Action candidate detected | Auto-run what-if and generate numerical proposal → return to Phase 4 |

#### Autonomous Loop Examples

**Example 1: Earnings date discovered**
Phase 3 runs health → Phase 4 reveals "NFLX earnings are today"
→ Orchestrator: "Remove NFLX take-profit from plan" → return to Phase 3 and re-execute with revised plan

**Example 2: Unrealized gain concentration detected**
Phase 3 runs health → Phase 4 detects "AMZN unrealized gains 68% concentrated"
→ Orchestrator: auto-runs what-if --remove "AMZN:5" and "AMZN:7" → generates comparison table → proceed to Phase 5

**Example 3: Theme gap detected**
Phase 3 runs health → Phase 4 detects "AI theme only, all other themes at 0%"
→ Orchestrator: adds theme-specific candidate screening → proceed to Phase 5

#### Autonomous Loop Limits
- Additional execution / plan revision: up to 2 times
- On the 3rd attempt, cut off and proceed to Phase 5

#### Autonomous Research Rules (strictly observed)

- When a new fact is detected (earnings result, surge/plunge, news) → **immediately research via WebSearch**. Do not ask the user "Should I check this?"
- Do not ask the user whether to collect information or conduct additional analysis
- Only ask the user for confirmation in Phase 6 (final summary) to obtain approval for action execution
- Phase 1→2→3→4→5→6 proceeds autonomously without user confirmation
- Users retain the right to interrupt (say "stop" at any time)

#### Information Collection Priority

| Priority | Method | Time | Use Case |
|:---|:---|:---|:---|
| 1st | WebSearch | Seconds | Immediate confirmation of earnings results, news, breaking news |
| 2nd | yfinance | Seconds | Stock prices, financial data, earnings date retrieval |
| 3rd | run_research.py | 30-60s | Deep research via Grok API (only when detail is needed) |

### Phase 5: Review (2 agents in parallel)

Launch Quantitative Reviewer + Qualitative/Risk Reviewer in parallel.

#### Quantitative Reviewer Checklist (including Gate Keeper function)

| Check | Verdict |
|:---|:---|
| Were all Orchestrator steps executed? | PASS/FAIL |
| Is there an action proposal when an issue is detected? | PASS/FAIL |
| Does the proposal include share count, amount, and tax cost? | PASS/FAIL |
| Are lot sizes correct? (Japan: 100 shares, SGX: 100 shares, etc.) | PASS/FAIL |
| Does currency allocation stay within 60% limit? | PASS/FAIL |
| Are user_profile assumptions referenced? | PASS/FAIL |
| Numerical consistency (what-if fund balance, HHI changes, etc.)? | PASS/FAIL |
| Is tax cost calculation accurate (including purchase FX rate)? | PASS/FAIL |

#### Qualitative + Risk Reviewer Perspectives

**Qualitative checks:**
- Thesis alignment (is the take-profit reason based on thesis breakdown, or purely technical?)
- Respecting lesson/conviction (is the analysis rejecting a stock the user bought with conviction based on numbers alone?)
- Catalyst verification (have earnings dates, catalysts, and theme trends been confirmed?)
- Theme validity (does the recommended theme align with the market environment?)

**Risk checks:**
- Geopolitical risk (US-China tensions, Taiwan conflict, Middle East situation, sanctions → supply chain impact on PF stocks)
- Macro risk (interest rates, FX, inflation, recession probability)
- Market risk (F&G overheating, VIX spike, earnings season)
- PF structural risk (currency concentration, sector concentration, theme concentration, unrealized gain concentration)
- Stock-specific risk (liquidity, regulation, country risk)

#### Handling Review FAIL
- FAIL → Orchestrator identifies deficiencies and re-executes **only the deficient parts** (not a full redo)
- Example: Quantitative FAIL (tax cost not reflected), Qualitative PASS → add only tax cost calculation → re-review Quantitative only

### Phase 6: Final Summary

All PASS → Orchestrator presents the final report in the following 8-section structure.

#### Required 8 Sections

1. **Executive Summary** (1-2 line conclusion)
2. **PF Current Scorecard** (one table: total value / number of stocks / P/L ratio / F&G / VIX / USD ratio)
3. **Required Actions** (in priority order; each action includes share count, amount, tax cost, and exit strategy)
4. **Candidate Stock List** (presented even if "not buying now." Includes minimum investment, theme, region, P/E)
5. **Comparison with "Do Nothing"** (expected value of each action vs. expected value of hold)
6. **Risk Map** (3 levels: high/medium/low. Geopolitical / macro / market / PF structure / stock-specific)
7. **Unresolved Items** (items flagged with WARN in Review)
8. **Next Checkpoint** (what to check and when)

## Inter-Phase Output Schema

Each Phase passes the following required fields to the next Phase:

| Phase | Required Output |
|:---|:---|
| Phase 1 | context, constraints[], user_profile, upcoming_events[] |
| Phase 2 | workflow_steps[], lesson_check: PASS/FAIL, devils_advocate_concerns[] |
| Phase 3 | health_results, screening_candidates[], what_if_results[], market_data |
| Phase 4 | revised_plan?, additional_findings[], action_proposals[], autonomous_research[] |
| Phase 5 | quantitative: PASS/FAIL + reasons[], qualitative: PASS/FAIL + reasons[] |
| Phase 6 | Required 8-section report |

### Retry Rules

| Phase | Max Count | On Exceeding |
|:---|:---|:---|
| Phase 2 Lesson Checker FAIL | 2 times | Continue with WARN |
| Phase 4 Autonomous Loop | 2 times | Proceed to Phase 5 |
| Phase 5 Review FAIL | 2 times | Output with WARN |

3rd FAIL is cut off: "⚠️ The following items are unresolved but results are presented"

## Issue Detection → Auto-Proposal Triggers (applied in Phase 4)

| Detection | Auto-Proposal |
|:---|:---|
| Unrealized gains concentrated in 1 stock at >50% of PF unrealized gains | Specific partial take-profit plan (share count, sale proceeds, estimated tax cost) |
| RSI >70 + dead cross occurring simultaneously | Specific take-profit review plan (how many shares to sell, net after-tax proceeds) |
| Shareholder return rate declining for 3+ consecutive years | Specific sell plan (full sell or replacement candidate screening) |
| EXIT judgment in health check | Sell + screen 3 replacement candidates in same sector/theme |
| Theme gap | Present top 3 candidates by theme (with minimum investment amount) |
| F&G >80 + new buy-add proposal | Attach "market overheating" warning. Present comparison with cash-preservation strategy |

## Proposal Constraints

- Lot size validation: Japan stocks in 100-share lots, SGX in 100-share lots
- Currency allocation check: USD 60% cap. Warn if replacement is USD-denominated
- user_profile.yaml: Auto-calculate fees and tax costs (use defaults if file does not exist)
- F&G >80: Attach "market overheating" warning to new buy-add proposals

### Required Elements for Each Proposal

All action proposals must include the following together:
- **Exit strategy**: Stop-loss line / take-profit target / review conditions
- **Re-entry criteria**: Conditions for buying back after take-profit (if applicable)
- **Time limit**: "Review if no change within N weeks"
- **Candidate stock list**: Reinvestment candidates after sale (present even when "not buying now")

Candidate stock list must include:
- Top 3–5 candidates derived by reverse-engineering PF gaps (region, theme, currency)
- Each candidate's minimum investment, theme, region, P/E, dividend yield
- Improvement effect on PF (currency allocation change, regional diversification improvement)
- When cash preservation is recommended: re-entry trigger conditions (F&G, RSI, VIX, etc.)

## Escalation Criteria

Convene Context Analyst and run the full 3-agent parallel Plan Phase when any of the following apply:
- User's intent involves buying, selling, replacement, rebalancing, or adjustment
- `extract_constraints.py` returns action_type: swap_proposal / new_buy / sell / rebalance / adjust
- The plan contains what-if / adjust / rebalance commands
- An action proposal is generated during Phase 4's autonomous loop

For information queries only (snapshot, analyze, health, etc.), Context Analyst is not needed and Plan Phase can run in lightweight mode (Strategist only).

## Available Skills / Scripts

| Skill | Script | Purpose |
|:---|:---|:---|
| screen-stocks | run_screen.py | Screening |
| stock-report | generate_report.py | Individual stock report |
| stock-portfolio | run_portfolio.py | PF management (snapshot/analyze/health/forecast/what-if/adjust/rebalance/simulate/review) |
| stress-test | run_stress_test.py | Stress test |
| market-research | run_research.py | Market / industry / stock research |
| watchlist | manage_watchlist.py | Watchlist |
| investment-note | manage_note.py | Investment memos |
| graph-query | run_graph_query.py | Knowledge graph search |
| — | market_dashboard.py | Market conditions dashboard |
| — | get_context.py | Graph context retrieval |
| — | extract_constraints.py | Lesson constraint extraction |
