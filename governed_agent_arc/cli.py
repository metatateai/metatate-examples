#!/usr/bin/env python3
"""Command-line entry point for the governed agent arc example."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from governed_agent_arc.arc import print_transcript, run_arc
from governed_agent_arc.planner import get_planner


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Metatate governed agent arc example.")
    parser.add_argument(
        "--output",
        default=str(Path(tempfile.gettempdir()) / "metatate-governed-agent-arc-report.json"),
        help="Path for the machine-readable arc report.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = run_arc(planner=get_planner())
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
    print_transcript(report)
    print(f"Wrote governed agent arc report to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
