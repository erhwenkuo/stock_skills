"""CLI framework for skill scripts (KIK-518).

Provides ``BaseSkillCommand`` — a thin base class that encapsulates the
common lifecycle shared by all skill scripts:

    1. sys.path setup (project root)
    2. print_context()  — graph context retrieval
    3. run()            — skill-specific logic (subclass override)
    4. print_suggestions() — proactive suggestions

Subclasses override ``configure_parser()`` and ``run()`` only.

Example
-------
::

    class ReportCommand(BaseSkillCommand):
        name = "stock-report"
        description = "Stock report generation"

        def configure_parser(self, parser):
            parser.add_argument("symbol", help="Ticker symbol")

        def context_input(self, args):
            return f"report {args.symbol}"

        def run(self, args):
            print(f"Report for {args.symbol}")

        def suggestion_kwargs(self, args):
            return {"symbol": args.symbol, "context_summary": f"Report generated: {args.symbol}"}

    if __name__ == "__main__":
        ReportCommand().execute()
"""

from __future__ import annotations

import argparse
import os
import sys
from abc import ABC, abstractmethod
from typing import Any


def _ensure_project_root(script_file: str, depth: int = 4) -> str:
    """Add project root to sys.path if needed.

    Parameters
    ----------
    script_file : str
        ``__file__`` of the calling script.
    depth : int
        Directory levels from *script_file* to project root.
        4 for ``.claude/skills/*/scripts/*.py``, 2 for ``scripts/*.py``.

    Returns
    -------
    str
        Absolute path to the project root.
    """
    from pathlib import Path

    root = str(Path(script_file).resolve().parents[depth - 1])
    if root not in sys.path:
        sys.path.insert(0, root)
    return root


class BaseSkillCommand(ABC):
    """Base class for skill CLI entry points.

    Lifecycle:
        1. ``configure_parser()`` — add arguments to argparse
        2. ``context_input()``    — build the string for ``print_context()``
        3. ``run()``              — execute the skill logic
        4. ``suggestion_kwargs()``— build kwargs for ``print_suggestions()``

    Attributes
    ----------
    name : str
        Skill name (used in ``--help``). Subclass should set this.
    description : str
        One-line description for argparse.
    script_depth : int
        Directory depth from script to project root (default 4).
    """

    name: str = "skill"
    description: str = ""
    script_depth: int = 4

    # ------------------------------------------------------------------
    # Hooks for subclasses
    # ------------------------------------------------------------------

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        """Add arguments to *parser*. Override in subclass."""

    def context_input(self, args: argparse.Namespace) -> str:
        """Return the string passed to ``print_context()``.

        Return an empty string to skip context retrieval.
        """
        return ""

    @abstractmethod
    def run(self, args: argparse.Namespace) -> None:
        """Execute the skill logic. Must be overridden."""

    def suggestion_kwargs(self, args: argparse.Namespace) -> dict[str, Any]:
        """Return kwargs passed to ``print_suggestions()``.

        Override to supply ``symbol``, ``sector``, ``context_summary``, etc.
        """
        return {}

    # ------------------------------------------------------------------
    # Execution engine
    # ------------------------------------------------------------------

    def execute(self, argv: list[str] | None = None, *, script_file: str | None = None) -> None:
        """Parse arguments and run the full lifecycle.

        Parameters
        ----------
        argv : list[str] | None
            Command-line arguments (default: ``sys.argv[1:]``).
        script_file : str | None
            ``__file__`` of the calling script for path setup.
            When *None*, path setup is skipped (useful in tests).
        """
        # Step 0: path setup
        if script_file is not None:
            _ensure_project_root(script_file, depth=self.script_depth)

        # Step 1: parse arguments
        parser = argparse.ArgumentParser(
            prog=self.name,
            description=self.description,
        )
        self.configure_parser(parser)
        args = parser.parse_args(argv)

        # Step 2: context retrieval
        ctx_input = self.context_input(args)
        if ctx_input:
            try:
                from scripts.common import print_context

                print_context(ctx_input)
            except Exception:
                pass  # graceful degradation

        # Step 3: run
        self.run(args)

        # Step 4: proactive suggestions
        sug_kwargs = self.suggestion_kwargs(args)
        if sug_kwargs or ctx_input:
            try:
                from scripts.common import print_suggestions

                print_suggestions(**sug_kwargs)
            except Exception:
                pass  # graceful degradation
