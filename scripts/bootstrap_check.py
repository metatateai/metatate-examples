#!/usr/bin/env python3
"""Coverage delta for YOUR estate — run before and after the starter pack.

Live-only and estate-agnostic: discovers what the current publication
governs, then asks the baseline question ("can we use this for analytics?")
of every governed table and reports the typed answer per asset. Run it once
against a freshly-connected workspace (expect honest not-enough answers, or
nothing discovered at all), publish the starter policies
(`starter-policies/`), then run it again and watch the delta.

Note: each row is one `authorize_use` call against your workspace (it counts
toward the plan's MCP-call quota, like any governed question).
"""

from __future__ import annotations

import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common import get_client  # noqa: E402


def main() -> int:
    if os.getenv("METATATE_EXAMPLES_MODE", "offline").strip().lower() != "live":
        print(
            "bootstrap_check surveys YOUR estate — it only makes sense live.\n"
            "Export METATATE_EXAMPLES_MODE=live, METATATE_MCP_URL and your token\n"
            "(docs/live-mode-saas.md), then rerun."
        )
        return 2

    client = get_client()
    discovery = client.discover_context()
    tables = [
        entry["ref"]
        for entry in discovery.get("assets") or []
        if not entry.get("ref", {}).get("column")
    ]
    publication = discovery.get("publication") or {}
    print(f"publication: {publication.get('publication_id')} ({publication.get('published_at')})")
    print(f"governed tables discovered: {len(tables)}\n")
    if not tables:
        print("Nothing governed yet — publish the starter pack and rerun.")
        return 0

    states: Counter[str] = Counter()
    for ref in tables:
        answer = client.authorize_use(
            ref,
            use="baseline governance coverage check: analytics on this table",
            scenario_key="purpose.allowed_use",
        )
        state = str(answer.get("state"))
        label = answer.get("decision") or answer.get("reason_code") or state
        states[state] += 1
        path = ".".join(str(ref.get(k)) for k in ("database", "schema", "table"))
        print(f"  {path:60s} {state:28s} {label}")

    print("\ncoverage summary:")
    for state, count in sorted(states.items()):
        print(f"  {state}: {count}/{len(tables)}")
    answered = states.get("answered", 0)
    print(
        f"\n{answered}/{len(tables)} tables answer the baseline question from "
        "published policy. Publish the starter pack (or your own policies) and "
        "rerun to watch not-enough answers turn into typed decisions."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
