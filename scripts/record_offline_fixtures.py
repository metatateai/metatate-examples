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
PINNED_EVALUATED_AT = "2026-07-30T00:00:00.000Z"


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
                k: (
                    PINNED_PUBLISHED_AT
                    if k == "published_at" and isinstance(v, str)
                    else PINNED_EVALUATED_AT
                    if k == "evaluated_at" and isinstance(v, str)
                    else swap(v)
                )
                for k, v in value.items()
            }
        return value

    return [swap(recording) for recording in recordings]


# Tables the canonical case set requires. Derived from CASES, not hand-listed,
# so a new case that references a new table cannot slip past the gate.
def _required_tables() -> set[str]:
    found: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if "table" in node and "database" in node:
                found.add(str(node["table"]))
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk([c["arguments"] for c in CASES])
    return found


def _ungoverned_tables() -> set[str]:
    """Tables the pack references in order to demonstrate the ABSENCE of
    published state. Derived from the case set so the list cannot drift."""
    found: set[str] = set()
    for case in CASES:
        if "ungoverned" not in str(case["id"]):
            continue
        asset_ref = case["arguments"].get("asset")
        if isinstance(asset_ref, dict) and "table" in asset_ref:
            found.add(str(asset_ref["table"]))
    return found


def preflight(client: "MetatateCloudClient") -> None:
    """FAIL CLOSED before recording anything.

    Recording against a workspace that does not serve the full estate produces
    a partial fixture set that still *looks* like a recording — the first run
    of this pack died on `asset_not_found` two-thirds of the way through, after
    having already written files. Worse, a workspace could be selected by a
    misleading slug: the tenant named `acmecloud-demo` serves only 5 of the 11
    tables the cases need. So the gate checks the ESTATE, never the name.
    """
    answer = client.call_tool("discover_context", {})
    state = answer.get("state")
    if state != "answered":
        raise SystemExit(f"preflight FAILED: discover_context state={state!r}, expected 'answered' (is a publication current?)")
    assets = answer.get("assets") or []
    # The asset shape nests the ref: {"ref": {database, schema, table, column}}.
    # Reading a flat "table" key yields None for every asset and makes the gate
    # report the ENTIRE estate as missing — a false alarm that looks exactly
    # like a wrong workspace.
    served = {
        str((a.get("ref") or {}).get("table"))
        for a in assets
        if isinstance(a, dict) and isinstance(a.get("ref"), dict)
    }
    required = _required_tables()
    # Some tables are referenced precisely BECAUSE they are ungoverned (the
    # pack demonstrates not_enough_published_state). Those must NOT be required
    # to appear in discover_context — and their absence is itself the point.
    intentionally_ungoverned = _ungoverned_tables()
    missing = sorted(required - served - intentionally_ungoverned)
    unexpectedly_governed = sorted(intentionally_ungoverned & served)
    if unexpectedly_governed:
        raise SystemExit(
            "preflight FAILED: tables the pack demonstrates as UNGOVERNED are "
            f"being served: {unexpectedly_governed}. The ungoverned-state cases "
            "would silently stop demonstrating anything."
        )
    if missing:
        raise SystemExit(
            "preflight FAILED: the configured workspace does not serve the full estate.\n"
            f"  required by CASES ({len(required)}): {sorted(required)}\n"
            f"  missing ({len(missing)}): {missing}\n"
            "  Refusing to record a partial fixture set."
        )
    print(f"preflight OK: workspace serves all {len(required)} required tables under a current publication")


def main() -> int:
    client = MetatateCloudClient()
    preflight(client)
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
