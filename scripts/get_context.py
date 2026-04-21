#!/usr/bin/env python3
"""CLI wrapper for auto graph context injection (KIK-411).

Usage:
    python3 scripts/get_context.py "How is 7203.T?"
    python3 scripts/get_context.py "What's the situation with Toyota?"
    python3 scripts/get_context.py "Is the portfolio okay?"
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.data.context.auto_context import get_context  # noqa: E402


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/get_context.py <user_input>")
        sys.exit(1)

    user_input = " ".join(sys.argv[1:])
    result = get_context(user_input)

    if result:
        print(result["context_markdown"])
    else:
        print("No context")


if __name__ == "__main__":
    main()
