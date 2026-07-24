#!/usr/bin/env python3
"""Render a Metatate policy-gate JSON report as a markdown verdict table.

Used by the composite GitHub Action for the job step summary and the PR
comment; usable standalone for any CI system that renders markdown.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

GATE_ICONS = {"pass": "✅", "needs_controls": "🟡", "fail": "❌", "needs_review": "🔎"}
GATE_SEVERITY = ["fail", "needs_review", "needs_controls", "pass"]


def worst_gate(report: dict[str, Any]) -> str:
    gates = {str(result.get("gate")) for result in report.get("results") or []}
    for gate in GATE_SEVERITY:
        if gate in gates:
            return gate
    return "pass"


def render(report: dict[str, Any]) -> str:
    lines = [
        "### Metatate policy gate",
        "",
        f"**Change set:** `{report.get('change_set_id')}` — "
        f"{report.get('passed', 0)} pass · {report.get('needs_controls', 0)} needs_controls · "
        f"{report.get('failed', 0)} fail · {report.get('needs_review', 0)} needs_review — "
        f"release allowed: **{str(report.get('release_allowed')).lower()}**",
        "",
        "| Change | Kind | Gate | Decision | Reason codes | Evidence |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for result in report.get("results") or []:
        gate = str(result.get("gate"))
        icon = GATE_ICONS.get(gate, "")
        codes = ", ".join(result.get("reason_codes") or []) or "—"
        evidence = result.get("evidence_id") or "—"
        lines.append(
            f"| `{result.get('change_id')}` | {result.get('kind')} | {icon} {gate} "
            f"| {result.get('decision')} | {codes} | `{evidence}` |"
        )
    controls = [
        (result.get("change_id"), control)
        for result in report.get("results") or []
        for control in result.get("required_controls") or []
    ]
    if controls:
        lines += ["", "**Required controls**", ""]
        lines += [f"- `{change_id}`: {control}" for change_id, control in controls]
    lines += [
        "",
        "_Advisory verdicts served from the workspace's current publication; "
        "every row carries a Metatate evidence id._",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render a gate report as markdown.")
    parser.add_argument("--report", required=True, help="Path to the gate JSON report.")
    parser.add_argument("--output", help="Optional output path (defaults to stdout).")
    args = parser.parse_args(argv)

    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    markdown = render(report)
    if args.output:
        Path(args.output).write_text(markdown, encoding="utf-8")
    else:
        sys.stdout.write(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
