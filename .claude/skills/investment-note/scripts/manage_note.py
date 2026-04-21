#!/usr/bin/env python3
"""Entry point for the investment-note skill (KIK-408, KIK-429)."""

import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

from scripts.common import print_suggestions
from src.data.note_manager import save_note, load_notes, delete_note


def cmd_save(args):
    """Save a note."""
    # KIK-473: journal type does not require --symbol or --category
    if args.type != "journal" and not args.symbol and not args.category:
        print("Error: Either --symbol or --category is required.")
        sys.exit(1)
    if not args.content:
        print("Error: --content is required.")
        sys.exit(1)

    # KIK-534: lesson-specific fields
    extra = {}
    if args.type == "lesson":
        if getattr(args, "trigger", None):
            extra["trigger"] = args.trigger
        if getattr(args, "expected_action", None):
            extra["expected_action"] = args.expected_action

    note = save_note(
        symbol=args.symbol or None,
        note_type=args.type,
        content=args.content,
        source=args.source,
        category=args.category,
        **extra,
    )

    label = note.get("symbol") or note.get("category", "general")
    print(f"Note saved: {note['id']}")
    print(f"  Target: {label} / Type: {note['type']} / Category: {note.get('category', '-')}")
    print(f"  Content: {note['content']}")
    # KIK-534: show lesson-specific fields
    if note.get("trigger"):
        print(f"  Trigger: {note['trigger']}")
    if note.get("expected_action"):
        print(f"  Next action: {note['expected_action']}")
    # KIK-570: Show conflict warnings
    conflicts = note.get("_conflicts", [])
    if conflicts:
        print()
        for c in conflicts:
            ex = c.get("existing_lesson", {})
            sim = c.get("similarity", 0)
            ctype = c.get("conflict_type", "similar")
            detail = c.get("conflict_detail", "")
            ex_content = (ex.get("content") or "")[:50]
            label = "⚠️ Contradiction candidate" if ctype == "contradicting_action" else "📝 Similar lesson"
            print(f"  {label} (similarity: {sim:.2f}): {detail or ex_content}")
    # KIK-473: show detected symbols for journal notes
    detected = note.get("detected_symbols", [])
    if detected:
        print(f"  Detected symbols: {', '.join(detected)}")
    print_suggestions(
        symbol=args.symbol or "",
        context_summary=f"Note saved: {args.type} {label}",
    )


def cmd_list(args):
    """List notes."""
    notes = load_notes(symbol=args.symbol, note_type=args.type, category=args.category)

    if not notes:
        if args.symbol:
            print(f"No notes found for {args.symbol}.")
        elif args.category:
            print(f"No notes found for category '{args.category}'.")
        else:
            print("No notes found.")
        return

    label_parts = []
    if args.symbol:
        label_parts.append(args.symbol)
    if args.category:
        label_parts.append(f"category={args.category}")
    if args.type:
        label_parts.append(args.type)
    label = " / ".join(label_parts) if label_parts else "All"

    print(f"## Investment Notes ({label}: {len(notes)} entries)\n")
    print("| Date | Target | Category | Type | Content |")
    print("|:-----|:-----|:---------|:-------|:-----|")
    for n in notes:
        content = n.get("content", "")
        short = content[:50] + "..." if len(content) > 50 else content
        short = short.replace("|", "\\|").replace("\n", " ")
        target = n.get("symbol") or n.get("category", "-")
        # KIK-473: show detected symbols for journal notes without explicit symbol
        if n.get("type") == "journal" and not n.get("symbol") and n.get("detected_symbols"):
            target = ", ".join(n["detected_symbols"])
        cat = n.get("category", "-")
        print(f"| {n.get('date', '-')} | {target} | {cat} | {n.get('type', '-')} | {short} |")

    print(f"\nTotal: {len(notes)} entries")


def cmd_delete(args):
    """Delete a note by ID."""
    if not args.id:
        print("Error: --id is required.")
        sys.exit(1)

    if delete_note(args.id):
        print(f"Note deleted: {args.id}")
    else:
        print(f"Note not found: {args.id}")


def main():
    parser = argparse.ArgumentParser(description="Investment note management")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # save
    p_save = subparsers.add_parser("save", help="Save a note")
    p_save.add_argument("--symbol", default=None, help="Ticker symbol (e.g., 7203.T)")
    p_save.add_argument("--category", default=None,
                        choices=["portfolio", "market", "general"],
                        help="Category (used when --symbol is not specified)")
    p_save.add_argument(
        "--type", default="observation",
        choices=["thesis", "observation", "concern", "review", "target", "lesson", "journal", "exit-rule"],
        help="Note type",
    )
    p_save.add_argument("--content", required=True, help="Note content")
    p_save.add_argument("--source", default="manual", help="Source (e.g., manual, health-check)")
    p_save.add_argument("--trigger", default=None, help="Trigger for lesson notes (only valid when type=lesson, KIK-534)")
    p_save.add_argument("--expected-action", default=None, help="Expected next action (only valid when type=lesson, KIK-534)")
    p_save.set_defaults(func=cmd_save)

    # list
    p_list = subparsers.add_parser("list", help="List notes")
    p_list.add_argument("--symbol", default=None, help="Filter by symbol")
    p_list.add_argument("--category", default=None,
                        choices=["stock", "portfolio", "market", "general"],
                        help="Filter by category")
    p_list.add_argument("--type", default=None, help="Filter by type")
    p_list.set_defaults(func=cmd_list)

    # delete
    p_delete = subparsers.add_parser("delete", help="Delete a note")
    p_delete.add_argument("--id", required=True, help="Note ID")
    p_delete.set_defaults(func=cmd_delete)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
