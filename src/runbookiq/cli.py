"""Command-line interface for RunbookIQ."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from runbookiq import __version__
from runbookiq.kb import RunbookError, load_runbooks
from runbookiq.planner import build_plan
from runbookiq.policy import BLOCKED, CommandPolicy, PolicyError
from runbookiq.search import RunbookIndex

DEFAULT_KB_DIR = Path(__file__).resolve().parent.parent.parent / "knowledge"


def _context(args: argparse.Namespace) -> tuple[list, RunbookIndex, CommandPolicy]:
    runbooks = load_runbooks(Path(args.kb) if args.kb else DEFAULT_KB_DIR)
    return runbooks, RunbookIndex(runbooks), CommandPolicy.from_json(args.policy)


def _plan(args: argparse.Namespace) -> int:
    _, index, policy = _context(args)
    plan = build_plan(args.query, index, policy)
    if plan is None:
        print("No runbook matched that question. Try `runbookiq search` with different words.")
        return 0
    if args.json:
        print(json.dumps(plan.as_dict(), indent=2))
        return 0

    print(f"Runbook : {plan.citation}")
    print(f"Match   : score {plan.score:.2f} via {', '.join(plan.matched) or 'n/a'}")
    print(f"Approval: {'required' if plan.needs_approval else 'not required'}")
    print()
    if not plan.steps:
        print("No executable steps survived the safety policy.")
    for step in plan.steps:
        print(f"{step.order}. [{step.verdict}] {step.title}")
        print(f"   $ {step.command}")
        print(f"   policy: {step.reason}")
    if plan.blocked:
        print()
        print("Blocked by policy (never run these from a plan):")
        for step in plan.blocked:
            print(f" - {step.title}: {step.command}  ({step.reason})")
    print()
    print(f"Source: {plan.runbook.path}")
    return 0


def _search(args: argparse.Namespace) -> int:
    _, index, _ = _context(args)
    hits = index.search(args.query, limit=args.limit)
    if not hits:
        print("no matches")
        return 0
    if args.json:
        print(json.dumps([hit.as_dict() for hit in hits], indent=2))
        return 0
    for hit in hits:
        print(f"{hit.score:6.2f}  {hit.runbook.id:<22} {hit.runbook.title}")
        print(f"        matched: {', '.join(hit.matched)}")
    return 0


def _list(args: argparse.Namespace) -> int:
    runbooks, _, _ = _context(args)
    for runbook in runbooks:
        print(f"{runbook.id:<24} {runbook.system:<12} {len(runbook.steps)} steps  {runbook.title}")
    print(f"\n{len(runbooks)} runbook(s)")
    return 0


def _check(args: argparse.Namespace) -> int:
    policy = CommandPolicy.from_json(args.policy)
    decision = policy.classify(args.command)
    print(f"verdict : {decision.verdict}")
    print(f"reason  : {decision.reason}")
    print(f"rule    : {decision.rule}")
    return 1 if decision.verdict == BLOCKED else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="runbookiq",
        description="Retrieve IT runbooks and gate every suggested command through a safety policy.",
    )
    parser.add_argument("--version", action="version", version=f"runbookiq {__version__}")
    parser.add_argument("--kb", help="directory of runbook markdown files")
    parser.add_argument("--policy", help="path to a command policy JSON file")
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan", help="build a cited, gated step plan for a question")
    plan.add_argument("query")
    plan.add_argument("--json", action="store_true")
    plan.set_defaults(func=_plan)

    search = sub.add_parser("search", help="rank runbooks for a query")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=3)
    search.add_argument("--json", action="store_true")
    search.set_defaults(func=_search)

    listing = sub.add_parser("list", help="list available runbooks")
    listing.set_defaults(func=_list)

    check = sub.add_parser("check", help="classify a single command (exit 1 when blocked)")
    check.add_argument("command")
    check.set_defaults(func=_check)
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except (RunbookError, PolicyError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
