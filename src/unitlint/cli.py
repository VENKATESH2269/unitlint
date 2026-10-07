"""Command-line interface for unitlint."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import __version__
from .parser import parse
from .rules import ERROR, INFO, RULES, SEVERITY_RANK, WARNING, Finding, run_rules

COLORS = {ERROR: "31", WARNING: "33", INFO: "36"}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="unitlint",
        description="Lint systemd service unit files and explain how to fix problems.",
        epilog="Exit status: 0 = clean, 1 = findings at or above --fail-on, 2 = usage or I/O error.",
    )
    p.add_argument("paths", nargs="*", help="unit files, directories (scanned for *.service), or - for stdin")
    p.add_argument("--json", action="store_true", help="print machine-readable JSON")
    p.add_argument("--ignore", nargs="+", default=[], metavar="RULE", help="rule ids to skip, e.g. UL010 UL012")
    p.add_argument("--min-severity", choices=[INFO, WARNING, ERROR], default=INFO, help="only show findings at or above this level")
    p.add_argument("--fail-on", choices=[INFO, WARNING, ERROR, "never"], default=ERROR, help="exit 1 when a finding reaches this level (default: error)")
    p.add_argument("--list-rules", action="store_true", help="list all rules and exit")
    p.add_argument("--explain", metavar="RULE", help="explain a rule in detail and exit")
    p.add_argument("--no-color", action="store_true", help="disable coloured output")
    p.add_argument("--version", action="version", version=f"unitlint {__version__}")
    return p


def collect_sources(paths: List[str]) -> Tuple[List[Tuple[str, str]], List[str]]:
    """Return ([(display_name, text)], [error messages])."""
    sources: List[Tuple[str, str]] = []
    errors: List[str] = []
    for raw in paths:
        if raw == "-":
            sources.append(("<stdin>", sys.stdin.read()))
            continue
        path = Path(raw)
        if path.is_dir():
            files = sorted(path.rglob("*.service"))
            if not files:
                errors.append(f"{raw}: no .service files found")
        elif path.is_file():
            files = [path]
        else:
            errors.append(f"{raw}: no such file or directory")
            continue
        for f in files:
            try:
                sources.append((str(f), f.read_text(encoding="utf-8", errors="replace")))
            except OSError as exc:
                errors.append(f"{f}: {exc.strerror or exc}")
    return sources, errors


def render_text(results: Dict[str, List[Finding]], color: bool) -> str:
    def paint(text: str, code: str) -> str:
        return f"\033[{code}m{text}\033[0m" if color else text

    lines: List[str] = []
    counts = {ERROR: 0, WARNING: 0, INFO: 0}
    for name, findings in results.items():
        for f in findings:
            counts[f.severity] += 1
            lines.append(f"{name}:{f.line}: {paint(f.severity, COLORS[f.severity])} {f.rule} {f.message}")
            if f.hint:
                lines.append(f"    fix: {f.hint}")
    total = sum(counts.values())
    if not total:
        lines.append(f"{len(results)} file(s) checked, no problems found.")
    else:
        lines.append("")
        lines.append(
            f"{len(results)} file(s) checked: {counts[ERROR]} error(s), "
            f"{counts[WARNING]} warning(s), {counts[INFO]} suggestion(s)."
        )
    return "\n".join(lines)


def render_json(results: Dict[str, List[Finding]]) -> str:
    payload = {
        "version": __version__,
        "files": [
            {"path": name, "findings": [f.to_dict() for f in findings]}
            for name, findings in results.items()
        ],
    }
    return json.dumps(payload, indent=2)


def list_rules() -> str:
    return "\n".join(f"{r.id}  {r.severity:<8} {r.name}" for r in RULES.values())


def explain(rule_id: str) -> Optional[str]:
    r = RULES.get(rule_id.upper())
    if r is None:
        return None
    return f"{r.id}  {r.name}  [{r.severity}]\n\n{r.explanation}"


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_rules:
        print(list_rules())
        return 0
    if args.explain:
        text = explain(args.explain)
        if text is None:
            print(f"unitlint: unknown rule {args.explain!r} (see --list-rules)", file=sys.stderr)
            return 2
        print(text)
        return 0
    if not args.paths:
        parser.error("give at least one file, directory or - for stdin")

    sources, errors = collect_sources(args.paths)
    for message in errors:
        print(f"unitlint: {message}", file=sys.stderr)

    floor = SEVERITY_RANK[args.min_severity]
    results: Dict[str, List[Finding]] = {}
    for name, text in sources:
        found = run_rules(parse(text, name), tuple(args.ignore))
        results[name] = [f for f in found if SEVERITY_RANK[f.severity] >= floor]

    try:
        if args.json:
            print(render_json(results))
        else:
            print(render_text(results, sys.stdout.isatty() and not args.no_color))
        sys.stdout.flush()
    except BrokenPipeError:
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())

    if errors and not sources:
        return 2
    if args.fail_on != "never":
        threshold = SEVERITY_RANK[args.fail_on]
        if any(SEVERITY_RANK[f.severity] >= threshold for fs in results.values() for f in fs):
            return 1
    return 2 if errors else 0
