---
name: stock-report
description: Detailed report for individual stocks and ETFs. Generates a financial analysis report from a ticker symbol. Individual stocks show valuation, undervaluation score, and shareholder return rate. ETFs show expense ratio, AUM, and fund size.
argument-hint: "[ticker]  e.g.: 7203.T, AAPL, D05.SI"
allowed-tools: Bash(python3 *)
---

# Individual Stock Report Skill

Extract the ticker symbol from $ARGUMENTS and run the following command.

```bash
python3 /Users/kikuchihiroyuki/stock-skills/.claude/skills/stock-report/scripts/generate_report.py $ARGUMENTS
```

## Output Contents

- **Sector & Industry**
- **Price Information**: Current price, market cap
- **Valuation**: P/E, P/B, dividend yield, ROE, ROA, earnings growth rate
- **Undervaluation Score**: 0-100 score + judgment (undervalued/slightly undervalued/fair/overvalued)
- **Shareholder Returns** (KIK-375): Dividend yield + buyback yield = **total shareholder return rate**
- **Contrarian Signals** (KIK-504/533): Contrarian score (0-100) + grade (A/B/C/D) + 3-axis breakdown (technical/valuation/fundamental divergence)
- **Industry Context** (KIK-433, when Neo4j connected): Auto-display tailwinds and risks from recent industry research in the same sector

### ETF Auto-Detection (KIK-469)

Automatically detects ETFs (quoteType=ETF) and outputs an ETF-specific report instead of the individual stock report:

- **Fund Overview**: Category, fund family, AUM (net assets), expense ratio
- **Expense Ratio Assessment**: Ultra-low cost (<=0.1%) / Low cost (<=0.5%) / Slightly high (<=1.0%) / High cost (>1.0%)
- **Performance**: Current price, dividend yield, beta, 52-week range
- **Fund Size**: Large ($10B+) / Mid ($1B+) / Small ($100M+) / Micro (<$100M)

Display the result as-is.

## Knowledge Integration Rules (KIK-466)

When `get_context.py` output contains the following, integrate with the report result:

- **Screening appearance count**: "Top 3 screenings in a row → repeatedly noticed stock"
- **Purchase history (BOUGHT)**: If currently held: "As a held stock: unrealized gain +12%, thesis alignment is good"
- **Past reports**: Diff from previous figures. "P/E: 12.3→8.5 (improved), ROE: 15%→12% (declined)"
- **Investment notes**: Incorporate concerns and thesis into the report. "Concern note: inventory risk → latest quarter shows inventory reduction confirmed"
- **Research history**: Reference key points from the previous research and highlight changes

### Prompting to Record Analysis Conclusions

When the response includes specific investment opinions for valuation/undervaluation/value-trap assessments:
> 💡 Would you like to record this analysis as an investment note?
