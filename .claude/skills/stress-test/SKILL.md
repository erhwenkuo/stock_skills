---
name: stress-test
description: "Portfolio stress test. Receives a list of holdings and identifies portfolio weaknesses through shock sensitivity, scenario analysis, and causal chain analysis."
argument-hint: "[symbol list] [--scenario SCENARIO]  e.g.: 7203.T,AAPL,D05.SI --scenario triple-meltdown"
allowed-tools: Bash(python3 *)
---

# Portfolio Stress Test Skill

Parse $ARGUMENTS to determine the portfolio symbol list and scenario, then run the following command.

## Execution Command

```bash
python3 /Users/kikuchihiroyuki/stock-skills/.claude/skills/stress-test/scripts/run_stress_test.py --portfolio <symbols> [--scenario <scenario>] [--weights <weights>]
```

## Natural Language Routing

For natural language → skill selection, see [.claude/rules/intent-routing.md](../../rules/intent-routing.md).

## Argument Parsing Rules

### portfolio (symbol list — required)
Extract a comma-separated symbol list from user input. Convert space-separated input to comma-separated.

| User Input Example | --portfolio Value |
|:-------------|:-------------|
| `7203.T,AAPL,D05.SI` | `7203.T,AAPL,D05.SI` |
| `7203.T AAPL D05.SI` | `7203.T,AAPL,D05.SI` |
| `Toyota Apple` | Convert to corresponding tickers first |

### weights (holding ratios — optional)
Comma-separated ratio list matching the number of symbols. Defaults to equal weights (1/N per symbol).

| User Input Example | --weights Value |
|:-------------|:------------|
| `0.5,0.3,0.2` | `0.5,0.3,0.2` |
| `50%,30%,20%` | `0.5,0.3,0.2` (convert percentages to decimals) |
| omitted | Equal weight 1/N per symbol |

## Scenario List

| Scenario | Description |
|:--------|:-----|
| triple-meltdown | Equities, FX, and bonds fall simultaneously. Stress across all asset classes |
| usd-jpy-surge | Sharp JPY depreciation. Rising import costs; overseas assets appreciate in JPY terms |
| us-recession | US economic downturn. Global demand contraction, risk-off |
| boj-rate-hike | Rising Japanese interest rates. Banks up, growth stocks and REITs down |
| us-china-conflict | Escalating trade friction. Supply chain disruption; hit to semiconductors and manufacturing |
| inflation-resurgence | Rising prices again. Real purchasing power declines; rate hike expectations |
| tech-crash | NASDAQ -30%. AI expectations collapse; tech stocks hit hard, flight to quality |
| jpy-appreciation | USD/JPY -20 yen. Foreign asset JPY-denominated values fall; hit to exporters |
| custom | User-specified scenario interpreted from natural language |

## Output Format (10-Step Pipeline)

Present results in the following structured steps.

### Step 1: Portfolio Overview
- Symbol list (symbol, name, sector, weight)
- Total market cap (estimated)

### Step 2: Concentration Analysis
- Sector HHI / Region HHI / Currency HHI
- Identify highest concentration axis
- Risk level judgment (diversified / somewhat concentrated / dangerously concentrated)

### Step 3: Shock Sensitivity Scores
- Assessment of each stock's beta, financial health, and valuation resilience
- Per-symbol shock sensitivity score (0–100)

### Step 4: Scenario Definition
- Applied scenario name and description
- Macro variable changes (assumed movements in interest rates, FX, equities)

### Step 5: Per-Symbol Impact Estimates
- Estimated loss rate per symbol
- Application of concentration multiplier
- Portfolio-weighted impact

### Step 6: Portfolio-Wide Impact
- Estimated portfolio-wide loss rate
- Largest loss contributor

### Step 6b: Correlation Analysis (KIK-352)
- Cross-symbol correlation matrix (Pearson correlation, 1-year daily returns)
- High-correlation pairs detection (|r| >= 0.7)
- Factor decomposition: regress each symbol against macro variables (USD/JPY, Nikkei 225, S&P 500, crude oil, US 10-year yield)
- **LLM interpretation**: For residual correlations not explained by factor regression, use domain knowledge to infer causes (e.g., supply chain dependencies, shared customer base). Clearly separate "confirmed factors (statistical)" from "inferred factors (estimated)"

### Step 6c: VaR (Historical Data-Based Risk Metrics) (KIK-352)
- Calculate portfolio weighted returns from 1-year daily return history
- 95% VaR / 99% VaR (daily and monthly)
- Explain the difference from the scenario analysis (tail risk) in the stress test

### Step 7: Causal Chain Analysis
- Explanation of cascading effects when the scenario occurs
- Cross-sector propagation paths

### Step 8: Overall Assessment + Recommended Actions (KIK-352)
- Specific risk mitigation proposals (rule-based auto-generated + Claude supplement)
- Recommendations integrating concentration, correlation, VaR, and stress test results
- Hedge candidates (symbols and sectors)
- **LLM supplement**: In addition to rule-based recommendations, Claude should suggest sectors not in the portfolio and propose diversification targets informed by qualitative correlation causes

## Execution Examples

```bash
# Basic stress test (scenario auto-detected)
python3 .../run_stress_test.py --portfolio 7203.T,AAPL,D05.SI

# Triple meltdown scenario
python3 .../run_stress_test.py --portfolio 7203.T,9984.T,6758.T --scenario triple-meltdown

# With weight specification
python3 .../run_stress_test.py --portfolio 7203.T,AAPL,D05.SI --weights 0.5,0.3,0.2

# Custom scenario
python3 .../run_stress_test.py --portfolio 7203.T,AAPL --scenario "semiconductor supply chain collapse"
```

## Knowledge Integration Rules (KIK-466)

When `get_context.py` output contains the following, integrate with stress test results:

- **Previous stress test (StressTest)**: Compare with previous scenario and result. "Previous tech crash scenario: -18% → Current: -15% (improved: lower tech weighting)"
- **Concern notes**: If a flagged symbol takes heavy damage in the stress test, "concern note matches → consider countermeasures"
- **Investment notes**: Reference hedge strategy notes if available. "Previous lesson note: insufficient JPY hedge → still weak in USD surge scenario"
