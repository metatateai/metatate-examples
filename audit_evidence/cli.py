#!/usr/bin/env python3
"""Command-line entry point for the audit evidence packet example."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from audit_evidence.evidence import collect_evidence, print_packet, render_markdown


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Assemble a Metatate audit evidence packet.")
    parser.add_argument(
        "--output",
        default=str(Path(tempfile.gettempdir()) / "metatate-evidence-packet.json"),
        help="Path for the machine-readable packet JSON.",
    )
    parser.add_argument(
        "--markdown",
        default=str(Path(tempfile.gettempdir()) / "metatate-evidence-packet.md"),
        help="Path for the audit-ready markdown packet.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    packet = collect_evidence()
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(packet.to_dict(), indent=2) + "\n", encoding="utf-8")
    Path(args.markdown).parent.mkdir(parents=True, exist_ok=True)
    Path(args.markdown).write_text(render_markdown(packet), encoding="utf-8")
    print_packet(packet)
    print(f"Wrote evidence packet to {args.output}")
    print(f"Wrote audit-ready markdown to {args.markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
