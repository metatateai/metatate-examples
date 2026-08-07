#!/usr/bin/env python3
"""Generate the served-use OCCURRENCE inventory.

Two layers, deliberately separate — and the separation is load-bearing:

  * VOCABULARY DISPOSITION — keyed by ENTRY (`purpose-vocabulary-dispositions.yaml`).
    What an entry *means*.
  * OCCURRENCE INVENTORY  — keyed by (policy, list_kind, entry). Where each entry
    *appears*.

A single-keyed table cannot represent `prospect_outreach` being permitted in one
policy and prohibited in another: one row would overwrite the other, the
deliberate conflict fixture would disappear from the record, and the demo would
still serve both. So every occurrence row retains policy, list kind, and entry.

Sources, both directions:
  * CANONICAL  — the policy pack's `permittedUses` / `prohibitedUses` lists.
  * LIVE/SERVED — structured `usage_guidance` → `parameters.uses` in the
    recordings. NEVER prose or serialized-parameter scanning: a coarse
    `like '%financial_reporting%'` sweep in this program matched an English
    sentence in a `log_only` row and nearly drove real action.

CATEGORY vs KEY is mechanical, not a lookup table: an entry is a category
reference iff it byte-equals a registry family token, and the namespaces are
disjoint by construction — every key contains a `.`, no family token does
(metatate-saas docs/purpose-registry-product-contract.md:208).

Regenerate:  python3 scripts/build_served_use_inventory.py
Check drift: python3 scripts/build_served_use_inventory.py --check
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.build_purpose_manifest import _load_dispositions  # noqa: E402

POLICY_DIR = REPO / "sample-data" / "customer-360" / "policies"
FIXTURE_DIR = REPO / "sample-data" / "customer-360" / "metatate-responses"
INVENTORY = REPO / "sample-data" / "customer-360" / "served-use-inventory.json"

USES_RE = re.compile(r"(permittedUses|prohibitedUses):\s*\[([^\]]*)\]")


def canonical_occurrences() -> list[dict[str, str]]:
    """(policy, list_kind, entry) straight from the canonical policy pack."""
    rows: list[dict[str, str]] = []
    for path in sorted(POLICY_DIR.glob("*.yaml")):
        for match in USES_RE.finditer(path.read_text()):
            kind = "permitted" if match.group(1) == "permittedUses" else "prohibited"
            for raw in match.group(2).split(","):
                entry = raw.strip().strip("\"'")
                if entry:
                    rows.append({"policy": path.stem, "list_kind": kind, "entry": entry})
    return rows


def served_entries() -> dict[str, list[str]]:
    """entry -> case ids, read ONLY from structured usage_guidance parameters.uses."""
    found: dict[str, set[str]] = {}
    for path in sorted(FIXTURE_DIR.glob("*.json")):
        answer = json.loads(path.read_text()).get("answer", {})
        for finding in answer.get("instructions") or answer.get("findings") or []:
            for instruction in finding.get("instructions") or [finding]:
                if instruction.get("instruction_family") != "usage_guidance":
                    continue
                uses = (instruction.get("parameters") or {}).get("uses")
                if isinstance(uses, list):
                    for use in uses:
                        found.setdefault(str(use), set()).add(path.stem)
    return {k: sorted(v) for k, v in sorted(found.items())}


def build() -> dict[str, Any]:
    dispositions = {e["authored_entry"]: e for e in _load_dispositions()["entries"]}
    occurrences = canonical_occurrences()
    served = served_entries()

    entries = sorted({o["entry"] for o in occurrences} | set(served))

    # Family tokens derived MECHANICALLY from the observed keys, per the
    # disjointness rule: every key contains a dot, no family token does, so the
    # prefix of any dotted key IS a family token. This is why `ai` classifies as
    # a category rather than legacy free text — it byte-equals the family of
    # `ai.inference` / `ai.third_party_export`. Deriving it beats a lookup table,
    # which is exactly the kind of hand-list that has misfired twice here.
    families = {e.split(".", 1)[0] for e in entries if "." in e}
    pairs = sorted({(o["entry"], o["list_kind"]) for o in occurrences})

    per_entry = []
    for entry in entries:
        d = dispositions.get(entry, {})
        is_key = "." in entry
        kind = d.get("kind")
        if not kind:
            if is_key:
                kind = "registry_key"
            elif entry in families:
                kind = "registry_category"     # derived, not looked up
            elif d.get("do_not_map"):
                kind = "do_not_map"
            else:
                kind = "legacy_unmapped"
        cases = served.get(entry, [])
        per_entry.append({
            "entry": entry,
            # ---- DURABLE CONTRACT: what the entry means. Stable; assertions pin this.
            "disposition": {
                "classification": kind,
                "contains_dot": is_key,
                "resolved_key": d.get("resolved_key"),
                "resolved_category": d.get("resolved_category"),
                "matches": d.get("matches") or (f"{entry}.*" if (not is_key and entry in families) else None),
                "derived_family_token": (not is_key) and entry in families,
                "has_explicit_disposition": entry in dispositions,
                "list_kinds": sorted({o["list_kind"] for o in occurrences if o["entry"] == entry}),
                "in_canonical_pack": any(o["entry"] == entry for o in occurrences),
            },
            # ---- DERIVED MEASUREMENT of the CURRENT example set. NOT a contract.
            # Reported, never asserted: adding or removing a legitimate purposeful
            # case moves this number without touching the grant above. Pinning it
            # would make the gate fire on correct evolution of the examples.
            "derived_measurement": {
                "_note": "measurement of the current pack, not a contract",
                "resolves_in_case_count": len(cases),
                "resolves_in_cases": cases,
            },
            # kept flat for existing readers
            "classification": kind,
            "resolved_key": d.get("resolved_key"),
            "resolved_category": d.get("resolved_category"),
            "matches": d.get("matches") or (f"{entry}.*" if (not is_key and entry in families) else None),
            "has_disposition": entry in dispositions,
            "list_kinds": sorted({o["list_kind"] for o in occurrences if o["entry"] == entry}),
            "served_in_cases": cases,
        })

    return {
        "_comment": (
            "GENERATED by scripts/build_served_use_inventory.py — do not hand-edit. "
            "Occurrence layer: keyed by (policy, list_kind, entry) so opposite uses "
            "of one entry cannot collapse."
        ),
        "_sources": {
            "canonical": "sample-data/customer-360/policies/*.yaml permittedUses/prohibitedUses",
            "served": "structured usage_guidance parameters.uses in the recordings",
        },
        "totals": {
            "occurrences": len(occurrences),
            "distinct_entries": len(entries),
            "distinct_entry_listkind_pairs": len(pairs),
        },
        "occurrences": occurrences,
        "entries": per_entry,
    }


def main() -> int:
    inventory = build()
    rendered = json.dumps(inventory, indent=2, sort_keys=True) + "\n"
    if "--check" in sys.argv:
        if not INVENTORY.exists() or INVENTORY.read_text() != rendered:
            print("DRIFT: served-use-inventory.json does not match its canonical sources.")
            print("Regenerate with: python3 scripts/build_served_use_inventory.py")
            return 1
        t = inventory["totals"]
        print(f"inventory matches sources ({t['occurrences']} occurrences, "
              f"{t['distinct_entries']} entries, {t['distinct_entry_listkind_pairs']} pairs)")
        return 0
    INVENTORY.write_text(rendered)
    t = inventory["totals"]
    print(f"wrote {INVENTORY.relative_to(REPO)}")
    print(f"  occurrences: {t['occurrences']}  entries: {t['distinct_entries']}  "
          f"(entry,list_kind) pairs: {t['distinct_entry_listkind_pairs']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
