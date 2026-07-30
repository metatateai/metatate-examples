#!/usr/bin/env python3
"""Generate the machine-readable B3 purpose mapping manifest.

The manifest is LOAD-BEARING, not documentary: `scripts/live_expected_decision_parity.py`
reads it to decide what the live MCP must return. So it is GENERATED from the
canonical sources (`common/fixture_cases.py` + the recorded live answers) rather
than hand-written, which is what makes it complete instead of a summary.

Regenerate with:  python3 scripts/build_purpose_manifest.py
Check for drift:  python3 scripts/build_purpose_manifest.py --check
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from common.fixture_cases import CASES  # noqa: E402

FIXTURE_DIR = REPO / "sample-data" / "acmecloud" / "metatate-responses"
MANIFEST = REPO / "sample-data" / "acmecloud" / "purpose-mapping-manifest.json"

# NO HAND-LISTED SET LIVES HERE.
#
# "Which authored entries may never resolve" is DATA, read from the vendored
# dispositions file (itself a copy of the source manifest on metatate-saas). An
# earlier revision of this generator hard-coded four entries as inexpressible;
# two of them (`retrieval_context`, `customer_360_reporting`) had already been
# deliberately MAPPED by #374, so a gate built on that list would have failed on
# correct canonical state. The list is gone. If you are about to add one back,
# add it to the source manifest instead.
DISPOSITIONS = REPO / "sample-data" / "acmecloud" / "purpose-vocabulary-dispositions.yaml"


def _load_dispositions() -> dict[str, Any]:
    """Read the vendored dispositions without requiring PyYAML.

    The file is deliberately flat (`key: value`, list items under `entries:` /
    `prohibition_bite_checks:`) so the pack keeps working with only the stdlib —
    `requirements.txt` does not ship a YAML parser and this must run in the
    minimal offline CI image.
    """
    entries: list[dict[str, Any]] = []
    bite: list[dict[str, Any]] = []
    section = None
    current: dict[str, Any] | None = None
    for raw in DISPOSITIONS.read_text().splitlines():
        line = raw.split(" #")[0].rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("entries:"):
            section, current = entries, None
            continue
        if line.startswith("prohibition_bite_checks:"):
            section, current = bite, None
            continue
        if section is None:
            continue
        stripped = line.strip()
        if stripped.startswith("- "):
            current = {}
            section.append(current)
            stripped = stripped[2:]
        if current is None or ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        key, value = key.strip(), value.strip()
        if value in (">-", ">", "|"):
            value = ""  # folded scalar; rationale text is not machine-consumed
        if value == "null":
            parsed: Any = None
        elif value in ("true", "false"):
            parsed = value == "true"
        else:
            parsed = value
        if key in current and isinstance(current[key], str) and not value:
            continue
        current[key] = parsed
    return {"entries": entries, "prohibition_bite_checks": bite}


EXPECTED_DECISIONS = REPO / "sample-data" / "acmecloud" / "expected-decisions.yaml"


def _quarantined_ids() -> set[str]:
    """Read the quarantine set from the DATA, never from a literal here.

    This function exists because the literal it replaces caused a real defect:
    the quarantine was lifted in expected-decisions.yaml when the finance
    divergence resolved, but a frozen `QUARANTINED = {...}` set in this file kept
    marking both cases quarantined. The live parity gate then SKIPPED them while
    the PR body said they were restored — a release gate contradicting its own
    PR. Exactly the hand-listed-set failure this pack keeps finding elsewhere.
    """
    if not EXPECTED_DECISIONS.exists():
        return set()
    text = EXPECTED_DECISIONS.read_text()
    _, marker, tail = text.partition("\nquarantined:")
    if not marker:
        return set()
    ids: set[str] = set()
    for line in tail.splitlines():
        stripped = line.strip()
        if stripped.startswith("- id:"):
            ids.add(stripped.split(":", 1)[1].strip().strip("\"'"))
        elif stripped and not stripped.startswith(("-", "#")) and not line.startswith(" "):
            break  # left the quarantined block
    return ids

SCALARS = ("state", "decision", "verdict", "reason_code")


def _projection(case_id: str) -> dict[str, Any] | None:
    path = FIXTURE_DIR / f"{case_id}.json"
    if not path.exists():
        return None
    answer = json.loads(path.read_text()).get("answer", {})
    out = {k: answer.get(k) for k in SCALARS if answer.get(k) is not None}
    families: list[str] = []
    usage_guidance = 0
    for finding in answer.get("instructions") or answer.get("findings") or []:
        for instruction in finding.get("instructions") or [finding]:
            family = instruction.get("instruction_family") or instruction.get("family")
            if family:
                families.append(str(family))
                if family == "usage_guidance":
                    usage_guidance += 1
    evaluated = answer.get("evaluated_purpose")
    if isinstance(evaluated, dict):
        evaluated = evaluated.get("purpose_key")
    out["evaluated_purpose"] = evaluated
    out["citing_families"] = sorted(set(families))
    out["usage_guidance_rows_cited"] = usage_guidance
    out["has_decision_id"] = bool(answer.get("decision_id"))
    return out


def build() -> dict[str, Any]:
    by_case = {c["id"]: c for c in CASES}
    quarantined = _quarantined_ids()
    entries: list[dict[str, Any]] = []

    for case in CASES:
        if case["tool"] not in {"authorize_use", "validate_query_context"}:
            continue
        cid = case["id"]
        declared = case["arguments"].get("purpose_key")
        projection = _projection(cid)
        if projection is None:
            continue

        if declared is not None:
            kind = "purposeful"
        elif "purpose-inexpressible" in cid:
            kind = "inexpressible"
        elif "purpose-missing" in cid:
            kind = "purpose_missing_control"
        else:
            kind = "purpose_blind"

        entries.append({
            "case_id": cid,
            "tool": case["tool"],
            "kind": kind,
            "declared_purpose_key": declared,
            "quarantined": cid in quarantined,
            "expected_offline_projection": projection,
        })

    dispositions = _load_dispositions()
    disposition_entries = dispositions["entries"]

    # Derived, never listed: only entries the DATA marks do_not_map may be
    # asserted as "must remain unmapped".
    must_remain_unmapped = [
        {
            "authored_entry": e["authored_entry"],
            "must_remain_unmapped": True,
            "policy": e.get("policy"),
            "list": e.get("list"),
        }
        for e in disposition_entries
        if e.get("do_not_map") is True
    ]

    # Everything else, recorded so the manifest is COMPLETE rather than a summary.
    # An entry is DISPOSITIONED if it resolves to a key OR carries an explicit
    # kind (category token, normalized key, deliberate conflict). Only entries
    # with neither are genuinely untouched.
    #
    # Categories must never appear as "may become mapped": `analytics` is a
    # deliberate category-wide grant, and inviting a future reader to "map" it
    # would invite narrowing it to one leaf — silently shrinking the grant.
    DISPOSITIONED_KINDS = {"registry_category", "normalized_key", "deliberate_conflict"}
    mapped = [
        {"authored_entry": e["authored_entry"], "resolved_key": e.get("resolved_key"),
         "resolved_category": e.get("resolved_category"),
         "matches": e.get("matches"),
         "kind": e.get("kind") or ("registry_key" if e.get("resolved_key") else None),
         "resolved_kind": e.get("resolved_kind", "purpose_key"),
         "policy": e.get("policy"), "list": e.get("list")}
        for e in disposition_entries
        if e.get("resolved_key") not in (None, "") or e.get("kind") in DISPOSITIONED_KINDS
    ]
    unmapped_untouched = [
        {"authored_entry": e["authored_entry"], "list": e.get("list"),
         "may_become_mapped": True}
        for e in disposition_entries
        if e.get("resolved_key") in (None, "")
        and e.get("do_not_map") is not True
        and e.get("kind") not in DISPOSITIONED_KINDS
    ]

    bite_checks = []
    for check in dispositions["prohibition_bite_checks"]:
        cid = check.get("case_id")
        proj = _projection(cid) if cid else None
        bite_checks.append({
            "case_id": cid,
            "covers_authored_entry": check.get("covers"),
            "expected_projection": {
                k: (proj or {}).get(k) for k in ("state", "decision", "reason_code")
                if proj and proj.get(k) is not None
            },
        })

    return {
        "_comment": (
            "GENERATED by scripts/build_purpose_manifest.py — do not hand-edit. "
            "Load-bearing: scripts/live_expected_decision_parity.py reads this to "
            "decide what the live MCP must return."
        ),
        "_scope": (
            "This manifest states the OFFLINE projection per case and the standing "
            "ruling on authored entries that must remain unmapped. It is not a "
            "statement about detection frequency; see the parity check's own scope note."
        ),
        "_dispositions_source": (
            "sample-data/acmecloud/purpose-vocabulary-dispositions.yaml (vendored from "
            "metatate-saas docs/b3-acmecloud-purpose-vocabulary-manifest.md @ 19a3fdd)"
        ),
        "purposeful_and_blind_cases": entries,
        "authored_entries_mapped": mapped,
        "authored_entries_unmapped_untouched": unmapped_untouched,
        "authored_entries_that_must_remain_unmapped": must_remain_unmapped,
        "prohibition_bite_checks": bite_checks,
    }


def main() -> int:
    manifest = build()
    rendered = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    if "--check" in sys.argv:
        if not MANIFEST.exists():
            print(f"MISSING: {MANIFEST}")
            return 1
        if MANIFEST.read_text() != rendered:
            print("DRIFT: purpose-mapping-manifest.json does not match its canonical sources.")
            print("Regenerate with: python3 scripts/build_purpose_manifest.py")
            return 1
        n = len(manifest["purposeful_and_blind_cases"])
        m = len(manifest["authored_entries_that_must_remain_unmapped"])
        print(f"manifest matches canonical sources ({n} cases, "
              f"{len(manifest['authored_entries_mapped'])} mapped, "
              f"{len(manifest['authored_entries_unmapped_untouched'])} unmapped-untouched, "
              f"{m} do-not-map)")
        return 0
    MANIFEST.write_text(rendered)
    print(f"wrote {MANIFEST.relative_to(REPO)}")
    print(f"  cases: {len(manifest['purposeful_and_blind_cases'])}")
    print(f"  mapped: {len(manifest['authored_entries_mapped'])}")
    print(f"  unmapped-untouched: {len(manifest['authored_entries_unmapped_untouched'])}")
    print(f"  DO-NOT-MAP (standing ruling): "
          f"{[e['authored_entry'] for e in manifest['authored_entries_that_must_remain_unmapped']]}")
    print(f"  prohibition bite checks: {len(manifest['prohibition_bite_checks'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
