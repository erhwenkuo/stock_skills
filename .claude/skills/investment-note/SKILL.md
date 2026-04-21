---
name: investment-note
description: Investment note management. Record, retrieve, and delete investment theses, concerns, and lessons.
argument-hint: "[save|list|delete] [--symbol SYMBOL] [--category CATEGORY] [--type TYPE] [--content TEXT] [--id NOTE_ID]"
allowed-tools: Bash(python3 *)
---

# Investment Note Management Skill

Parse $ARGUMENTS and execute the following commands.

## Execution Command

```bash
python3 /Users/kikuchihiroyuki/stock-skills/.claude/skills/investment-note/scripts/manage_note.py $ARGUMENTS
```

Display the result as-is.

## Command Reference

### save — Save a note

```bash
# Stock note (standard)
python3 .../manage_note.py save --symbol 7203.T --type thesis --content "EV adoption increases parts demand"

# Portfolio-wide note (KIK-429: symbol made optional)
python3 .../manage_note.py save --category portfolio --type review --content "Reduced sector overweight"

# Market note
python3 .../manage_note.py save --category market --type observation --content "BOJ rate hike speculation"
```

Either `--symbol` or `--category` is required (except for `journal` type). When `--symbol` is specified, category is automatically set to `stock`.

```bash
# Investment journal / free memo (KIK-473: symbol/category not required)
python3 .../manage_note.py save --type journal --content "NVDA surged. Felt the strength of AI demand"
# → Auto-detects ticker symbols (NVDA) in the body and links to Neo4j
```

### list — List notes

```bash
python3 .../manage_note.py list [--symbol 7203.T] [--type concern] [--category portfolio]
```

### delete — Delete a note

```bash
python3 .../manage_note.py delete --id note_2025-02-17_7203_T_abc12345
```

## Note Types

| Type | Meaning | Usage Example |
|:---|:---|:---|
| thesis | Investment thesis | "EV adoption increases parts demand" |
| observation | Observation | "Appeared in top 3 screenings in a row" |
| concern | Concern | "China market slowdown risk" |
| review | Review | "3-month hold, thesis on track" |
| target | Target / exit | "Take profit at P/E 15" |
| lesson | Lesson learned | "It was a value trap" |
| journal | Investment journal / free memo | "NVDA surged. Felt AI demand" (KIK-473: symbol/category not required, auto-detects tickers from body) |

## Categories (KIK-429)

| Category | Meaning | Usage |
|:---|:---|:---|
| stock | Individual stock note | Auto-set when `--symbol` is specified |
| portfolio | Portfolio-wide note | `--category portfolio` (PF review, rebalancing rationale, etc.) |
| market | Market note | `--category market` (macro trends, interest rates, etc.) |
| general | General note | `--category general` (uncategorized, default) |

## Natural Language Routing

For natural language → skill selection, see [.claude/rules/intent-routing.md](../../rules/intent-routing.md).

## Knowledge Integration Rules (KIK-466)

When `get_context.py` output is available, integrate with note operations:

- **save**: Reference the latest status of the target stock (latest report, health check results) to enrich the note context
- **list**: When displaying the note list, append the current holding status (holding/sold/watching) of each target stock
