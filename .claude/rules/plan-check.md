# Plan-Check: Investment Decision Multi-Agent Flow (KIK-596)

For statements involving investment decision execution (replacement, purchase, sale, rebalancing, adjustment),
three phases — Plan → Execute → Review — are conducted with multiple agents debating,
and past lessons are automatically applied as constraints.

## Key Principles

**The Plan phase is about "how to investigate (workflow design)," not "what to do (decision-making)."**

- Plan = execution blueprint (what steps and what to analyze)
- Execute = analysis execution (compare multiple patterns and make data-driven decisions)
- Review = verification (constraint satisfaction, quality, and risk checks)

"Should we sell?" and "What should we buy?" are not for the Plan phase to decide. They are derived as results from the Execute analysis.

## Trigger Conditions

Plan-Check is triggered via the following two paths.

### Path 1: Escalation from /plan-execute v2 (Recommended) (KIK-609)

When the `/plan-execute` skill's Orchestrator determines that an investment decision is involved, it automatically executes the Plan Phase (3 agents in parallel: Strategist + Lesson Checker + Devil's Advocate).

The Orchestrator runs the full Plan Phase in the following cases:
- The user's intent involves buying, selling, replacement, rebalancing, or adjustment
- `extract_constraints.py` returns action_type: swap_proposal / new_buy / sell / rebalance / adjust
- An action proposal is generated during Phase 4's autonomous loop

For information queries only, the Plan Phase runs in a lightweight version (Strategist only), and escalates to a full Plan Phase via the autonomous loop when issues are detected.

### Path 2: Direct Trigger (Backward Compatible)

Trigger this flow directly when a statement matches one of the following action types.

| Action Type | Trigger Keywords |
|:---|:---|
| `swap_proposal` | Replace, switch, alternative, swap |
| `new_buy` | Want to buy, entry, want to add |
| `sell` | Want to sell, stop-loss, take profit, sell |
| `rebalance` | Rebalance, allocation adjustment, improve balance |
| `adjust` | Adjust, prescription, fix, improve, advise |

**Cases that do NOT trigger**: Information queries ("show me"), trade recording (past tense "I bought"), screening exploration ("any good stocks?")

## Flow

### Phase 1: Plan (Workflow Design)

**Purpose**: Decide what steps to take, what to analyze, and how to compare. No decision-making.

1. Run `python3 scripts/extract_constraints.py "<user input>"` to get constraints JSON
2. Launch the following 3 agents in parallel to design the **workflow**

#### Strategist

Design the execution workflow. Must include:
- List of analysis steps (what to do, in what order)
- Skills/scripts to use at each step
- **Options to compare** (e.g., 3 patterns: sell / hold / partial sell)
- Success criteria (what constitutes a successful outcome)

**Required analysis perspectives** (must be included in the workflow):
- Sector, region, and currency diversification (existing)
- **Large/mid/small-cap balance** (how the portfolio's size composition changes after addition)
- **Risk asset / safe asset balance** (changes in Beta and volatility)
- **Portfolio-wide risk-return profile** (Before/After what-if comparison)
- **Portfolio overheating/oversold assessment**:
  - Portfolio weighted average RSI (>70 = overheated, <30 = oversold)
  - Percentage of portfolio that RSI>70 stocks represent (overheating concentration)
  - Unrealized gain concentration (is profit skewed to one stock?)
  - Alignment with F&G score (is the market overheating while the portfolio is too?)
- **Expected value of "do nothing" option** (all actions must exceed this)

**Note**: Do not include decisions like "should sell" or "should buy." Design analysis steps like "compare the sell and hold patterns."

#### Lesson Checker

Check whether constraint conditions (output of extract_constraints.py) are incorporated into the workflow:
- Whether each constraint's expected_action is included in a workflow step
- If any constraints are missing, indicate steps to add to the workflow
- Verdict: PASS (all constraints reflected) / FAIL (missing)

#### Devil's Advocate

Point out blind spots in the workflow:
- Options that should be considered but are not included
- Perspectives that should be analyzed but are missing (e.g., hold option comparison is absent)
- Workflow bias (is the step design conclusion-driven?)
- **Are portfolio balance perspectives missing?**:
  - Will it become overly large-cap or small-cap heavy?
  - Will it become too defensive or too growth-oriented?
  - Is the change in Beta/volatility considered?
  - Is tax cost (approximately 20% capital gains tax) calculated?
  - Is the timing relative to earnings considered?
- **Is the portfolio's overheated/oversold state considered?**:
  - Is a buy-add proposal made even though portfolio weighted average RSI is overheated (>70)?
  - Is the risk of unrealized gains concentrated in 1-2 stocks considered?
  - Is the reversal risk considered when both market (F&G) and portfolio overheating are aligned?
- **Theme momentum risk**: When adding to a trending theme with F&G >80, flag the theme bubble collapse risk (KIK-605)
- **Theme fading risk**: If the trend score for a theme in the portfolio has been declining, verify whether continued holding is appropriate (KIK-605)
- **Sector relative PER risk**: If a stock's PER is more than 2x the sector median, flag overvaluation risk (KIK-605)

3. Integrate results from the 3 agents and finalize the workflow
4. If Lesson Checker returns FAIL → revise the workflow (up to 2 times)

**Example Plan Phase output**:
```
Step 1: Health check + forecast review for 7751.T
Step 2: Compare 3 patterns by expected value: sell / hold / partial sell (50 shares)
Step 3: If selling → screen in 3 regions (JP/SG/HK)
Step 4: Calculate currency allocation impact for each candidate (constraint: USD ≤60%)
Step 5: Confirm lot cost × price is within budget
Step 6: What-if simulation (top 3 candidates)
Step 7: Create comparison table of all patterns and derive recommendation
```

### Phase 2: Execute (Analysis Execution)

Execute each step according to the workflow designed in the Plan Phase.

**Typical execution content (by action type)**:

| Action Type | Typical Steps |
|:---|:---|
| swap_proposal | health → sell/hold comparison → screen-stocks (3+ regions) → currency allocation calculation → what-if |
| new_buy | get_context → stock-report → currency allocation calculation → what-if |
| sell | get_context → health → sell/hold comparison → what-if |
| rebalance | health → analyze → rebalance |
| adjust | health → adjust |

If constraints specify "search in at least 3 regions," screening must be run in 3+ regions.

**Execute output**: Comparison table of analysis results + data-driven recommendation (this is where decision-making is derived for the first time)

### Phase 3: Review (Verification)

1. Launch the following 3 agents in parallel

#### Constraint Checker

Final confirmation that constraint conditions are satisfied:
- Whether each constraint's expected_action was executed
- Whether there are any constraint violations in the output
- Verdict: PASS / FAIL (with reason for return)

#### Quality Checker

Verify output quality and logical consistency:
- Numerical consistency (what-if fund balance, HHI changes, etc.)
- Whether the logical basis for recommendations is explicitly stated
- Compliance with portfolio.md rules (what-if required before swap, lot cost limits, etc.)
- **Size balance verification**: Is the post-addition portfolio balanced across large/mid/small cap?
- **Risk-return verification**: Is the post-addition portfolio weighted average Beta overly defensive (<0.5) or aggressive (>1.0)?
- **Overheated/oversold verification**: Is a buy-add proposed with portfolio weighted average RSI in overheated territory (>70), or a sell proposed with it in oversold territory (<30)?
- **Tax cost verification**: If realizing gains, is the after-tax actual return calculated?

#### Risk Checker

Final check for overlooked risks:
- Currency concentration risk (USD ratio >60%, etc.)
- Sector/region concentration risk
- **Size concentration risk** (small-cap ratio >25% or large-cap ratio >80%)
- **Volatility risk** (if added stock's Beta >2.0, impact on overall portfolio)
- Liquidity risk (lot cost vs total portfolio value)
- Market risk (just before earnings, geopolitical events, etc.)
- **Overheating risk**: Portfolio weighted average RSI >70 or RSI>70 stocks representing >30% of portfolio — proceed with caution on additional purchases
- **Unrealized gain concentration risk**: If gains are concentrated in one stock representing >50% of total portfolio profit, issue a warning

2. Consolidate results
3. If any Checker returns FAIL → return to Phase 1 (with return reason)
4. All PASS → present final output to user

## Return Rules

- Maximum returns: 2 times
- On the 3rd attempt, output with WARN (to prevent infinite loops)
- On return: include FAIL reason + relevant constraint and add to Phase 1 input

## Constraint Extraction Command

```bash
# JSON format (for agent input)
python3 scripts/extract_constraints.py "<user input>"

# Markdown format (human-readable)
python3 scripts/extract_constraints.py "<user input>" --format markdown
```
