#!/usr/bin/env python3
"""Record the offline fixture set from a live Metatate Cloud workspace.

Replays every case in `common/fixture_cases.py` against the configured live
endpoint (the workspace must serve the AcmeCloud demo publication) and writes
the typed answers to `sample-data/acmecloud/metatate-responses/{case_id}.json`.

The recordings are then NORMALIZED for stable diffs while staying internally
consistent: every uuid is rewritten (in order of first appearance, and
consistently across ALL files — so `decision_id` chaining into the recorded
explain answers still matches) and publication timestamps are pinned.

Usage (local stack example — docs/live-mode-saas.md):

    export METATATE_EXAMPLES_MODE=live
    export METATATE_MCP_URL=http://localhost:3200/mcp
    export METATATE_SAAS_MCP_TOKEN=mtt_...
    python3 scripts/record_offline_fixtures.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common.fixture_cases import CASES  # noqa: E402
from common.saas_client import MetatateCloudClient  # noqa: E402

FIXTURE_DIR = ROOT / "sample-data" / "acmecloud" / "metatate-responses"
UUID_RE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")
PINNED_PUBLISHED_AT = "2026-07-16T00:00:00.000Z"


def resolve_reference(value: Any, recorded: dict[str, dict[str, Any]]) -> Any:
    if isinstance(value, str) and value.startswith("@"):
        source_id, _, field = value[1:].partition(".")
        answer = recorded[source_id]["answer"]
        resolved = answer.get(field)
        if not isinstance(resolved, str):
            raise RuntimeError(f"reference {value} did not resolve to a string")
        return resolved
    if isinstance(value, dict):
        return {k: resolve_reference(v, recorded) for k, v in value.items()}
    return value


def normalize(recordings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    text = json.dumps(recordings, sort_keys=True)
    mapping: dict[str, str] = {}
    blob = json.dumps(recordings)
    for match in UUID_RE.finditer(blob):
        raw = match.group(0)
        if raw not in mapping:
            mapping[raw] = f"accef000-0000-4000-8000-{len(mapping) + 1:012d}"
    del text

    def swap(value: Any) -> Any:
        if isinstance(value, str):
            return UUID_RE.sub(lambda m: mapping.get(m.group(0), m.group(0)), value)
        if isinstance(value, list):
            return [swap(item) for item in value]
        if isinstance(value, dict):
            return {
                k: (PINNED_PUBLISHED_AT if k == "published_at" and isinstance(v, str) else swap(v))
                for k, v in value.items()
            }
        return value

    return [swap(recording) for recording in recordings]


def main() -> int:
    client = MetatateCloudClient()
    recorded: dict[str, dict[str, Any]] = {}
    ordered: list[dict[str, Any]] = []

    for case in CASES:
        arguments = resolve_reference(dict(case["arguments"]), recorded)
        answer = client.call_tool(str(case["tool"]), arguments)
        recording = {
            "case_id": case["id"],
            "tool": case["tool"],
            "arguments": arguments,
            "answer": answer,
        }
        recorded[str(case["id"])] = recording
        ordered.append(recording)
        state = answer.get("state") or "(facts)"
        detail = answer.get("decision") or answer.get("verdict") or ""
        print(f"recorded {case['id']}: {state} {detail}".rstrip())

    normalized = normalize(ordered)

    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    for stale in FIXTURE_DIR.glob("*.json"):
        stale.unlink()
    for recording in normalized:
        path = FIXTURE_DIR / f"{recording['case_id']}.json"
        path.write_text(json.dumps(recording, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"\nwrote {len(normalized)} recordings to {FIXTURE_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
