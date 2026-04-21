---
name: watchlist
description: Watchlist management. Add, remove, and list stocks.
argument-hint: "[show|add|remove|list] [name] [symbols...]  e.g.: show my-list, add my-list 7203.T AAPL"
allowed-tools: Bash(python3 *)
---

# Watchlist Management Skill

Parse $ARGUMENTS and execute the following command.

```bash
python3 /Users/kikuchihiroyuki/stock-skills/.claude/skills/watchlist/scripts/manage_watchlist.py $ARGUMENTS
```

Display the result as-is.

## Knowledge Integration Rules (KIK-466)

When `get_context.py` output is available, integrate with watchlist operations:

- **add**: If the stock being added has a past history (screening appearances, report history), append a summary
- **list**: Supplement each stock's latest status (freshness label, most recent action) from context
