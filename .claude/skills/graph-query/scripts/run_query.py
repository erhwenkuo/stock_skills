#!/usr/bin/env python3
"""Entry point for the graph-query skill (KIK-409).

Migrated to BaseSkillCommand (KIK-518).
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

from scripts.cli_framework import BaseSkillCommand


class GraphQueryCommand(BaseSkillCommand):
    name = "graph-query"
    description = "Knowledge graph natural language query"

    def configure_parser(self, parser):
        parser.add_argument(
            "query_words",
            nargs="+",
            help="Natural language query (e.g., What was the last report on 7203.T?)",
        )

    def context_input(self, args):
        # graph-query does not use print_context (it IS the context query)
        return ""

    def run(self, args):
        from src.data.graph_query.nl_query import query

        user_input = " ".join(args.query_words)
        result = query(user_input)

        if result is None:
            print("No data found matching your query.")
            print("\nExample queries:")
            print("  - 'What was the last report on 7203.T?'")
            print("  - 'Stocks that keep coming up as candidates?'")
            print("  - 'AAPL research history'")
            print("  - 'Recent market conditions?'")
            print("  - '7203.T trade history'")
            return

        print(result["formatted"])

    def suggestion_kwargs(self, args):
        user_input = " ".join(args.query_words)
        return {"context_summary": f"Graph query: {user_input[:60]}"}


def main():
    GraphQueryCommand().execute()


if __name__ == "__main__":
    main()
