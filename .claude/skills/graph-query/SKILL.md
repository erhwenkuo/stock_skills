---
name: graph-query
description: Natural language queries to the knowledge graph. Search past reports, screenings, trades, research, and market context.
argument-hint: "Natural language query (e.g., What was the last report on Toyota?)"
allowed-tools: Bash(python3 *)
---

# Graph Query Skill

Search past data accumulated in the knowledge graph (Neo4j) using natural language.

## Execution Command

```bash
python3 .claude/skills/graph-query/scripts/run_query.py "natural language query"
```

## Natural Language Routing

For natural language → skill selection, see [.claude/rules/intent-routing.md](../../rules/intent-routing.md).

## Output

Results are displayed in Markdown format. If no data is found, a message is shown.
If Neo4j is not connected, displays "No data found."

## Knowledge Integration Rules (KIK-466)

When displaying graph query results, integrate with conversation context:

- If query results contain held stocks, add a "Currently holding" marker
- For past report search results, prompt: "To check the latest data, /stock-report is recommended"
