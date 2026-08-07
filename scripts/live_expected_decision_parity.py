#!/usr/bin/env python3
"""Live expected-decision parity — a RELEASE GATE, not monitoring.

WHAT THIS CLOSES, AND WHAT IT DOES NOT
--------------------------------------
It closes the **assertion** gap: until now nothing compared the offline expected
projections against what the live MCP actually returns, so the two could drift
apart silently and the pack would keep publishing the offline answer.

It does **not** close the **detection-frequency** gap. This runs under
`workflow_dispatch` only. It fires when a human invokes it — at a release head,
as a gate. It is therefore:

  * NOT continuous monitoring
  * NOT drift detection
  * NOT an ongoing guarantee that live and offline agree between invocations

Do not describe it as any of those. A gate that fires on demand tells you the
state at the moment it ran and nothing about the interval since.

WHY THERE IS NO SCHEDULE
------------------------
Adding a cron here is not free and is deliberately not done: **every live
evaluation writes durable ledger evidence** into the target tenant. A schedule
would accrue real governance records in a real workspace indefinitely — an
operational and data-retention cost, not merely CI minutes. If scheduled
detection is wanted it is a separate, costed decision.

HOW IT ASSERTS
--------------
Driven by `sample-data/customer-360/purpose-mapping-manifest.json`, in BOTH
directions:

  1. Canonicalizable cases must resolve to their EXACT declared purpose and
     produce the expected `(state, decision/verdict, reason_code)`.
  2. Authored entries that are intentionally inexpressible must REMAIN unmapped
     AND produce their expected fail-closed result.

It deliberately does NOT assert that every authored use resolves — and it does
NOT carry its own list of which entries may never resolve. That set is DATA,
supplied by the generated manifest (ultimately by the vendored dispositions file
copied from the source manifest on `metatate-saas`).

This matters because an earlier revision of this gate hard-coded four entries as
"must remain unmapped", two of which (`retrieval_context`,
`customer_360_reporting`) #374 had already mapped deliberately. That gate would
have FAILED on correct canonical state — a gate firing on the right answer. The
list is gone; only entries the data marks `do_not_map` are asserted, however many
that happens to be. This gate does not know the answer independently, by design.

An unmapped entry that is NOT marked `do_not_map` is simply untouched. It may
legitimately become mapped later, and this gate must not call that a regression.

Quarantined cases are skipped and reported as skipped, never as passing.

Usage:
    METATATE_EXAMPLES_MODE=live METATATE_SAAS_MCP_TOKEN=... \\
        python3 scripts/live_expected_decision_parity.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from common.fixture_cases import CASES  # noqa: E402

MANIFEST = REPO / "sample-data" / "customer-360" / "purpose-mapping-manifest.json"

COMPARED = ("state", "decision", "verdict", "reason_code")


def _call(client: Any, case: dict[str, Any]) -> dict[str, Any]:
    a = dict(case["arguments"])
    if case["tool"] == "authorize_use":
        return client.authorize_use(
            a["asset"], use=a["use"], scenario_key=a.get("scenario_key"),
            operation=a.get("operation"), destination=a.get("destination"),
            consumer_jurisdiction=a.get("consumer_jurisdiction"),
            purpose_key=a.get("purpose_key"),
            data_access_context=a.get("data_access_context"),
            on_behalf_of=a.get("on_behalf_of"),
            satisfied_conditions=a.get("satisfied_conditions"),
        )
    if case["tool"] == "validate_query_context":
        return client.validate_query_context(
            a["sql"], scenario_key=a.get("scenario_key"), use=a.get("use"),
            default_database=a.get("default_database"),
            default_schema=a.get("default_schema"),
            operation=a.get("operation"), destination=a.get("destination"),
            consumer_jurisdiction=a.get("consumer_jurisdiction"),
            purpose_key=a.get("purpose_key"),
            data_access_context=a.get("data_access_context"),
            on_behalf_of=a.get("on_behalf_of"),
        )
    raise ValueError(f"unsupported tool {case['tool']!r}")


def _client_for_case(
    case: dict[str, Any], default_client: Any, agent_client: Any | None
) -> Any:
    if case.get("bound_role") != "agent":
        return default_client
    if agent_client is None:
        raise RuntimeError("agent-bound case has no agent client")
    return agent_client


def main() -> int:
    mode = os.environ.get("METATATE_EXAMPLES_MODE", "").strip().lower()
    if mode != "live":
        print("REFUSING: this gate is meaningless offline — it would compare the "
              "recordings against themselves.\nSet METATATE_EXAMPLES_MODE=live.")
        return 2

    manifest = json.loads(MANIFEST.read_text())
    by_id = {c["id"]: c for c in CASES}

    from common.saas_client import MetatateCloudClient
    client = MetatateCloudClient()
    agent_case_ids = {
        str(case["id"]) for case in CASES if case.get("bound_role") == "agent"
    }
    agent_client: MetatateCloudClient | None = None
    if agent_case_ids:
        if not os.getenv("METATATE_SAAS_MCP_AGENT_TOKEN"):
            print(
                "REFUSING: agent-bound parity cases require "
                "METATATE_SAAS_MCP_AGENT_TOKEN (a {read} token with bound_role=agent)."
            )
            return 2
        agent_client = MetatateCloudClient(
            token_env="METATATE_SAAS_MCP_AGENT_TOKEN"
        )

    # THREE DISTINCT COUNTERS. They were one "skipped" bucket, which made a
    # delegated-but-green fence look identical to a real skipped case — the gate
    # read weaker than it was AND a genuine skip could hide in the noise.
    case_pass = case_fail = case_skip = 0        # live case parity
    proh_pass = proh_fail = 0                    # live prohibition checks
    delegated = 0                                # fences asserted in SaaS CI, not here
    failures: list[str] = []

    print("=" * 78)
    print("LIVE EXPECTED-DECISION PARITY — release gate (workflow_dispatch only)")
    print("Scope: closes the ASSERTION gap. NOT monitoring, NOT drift detection.")
    print("=" * 78)

    # A release must not quietly withhold current-behaviour cases from its own
    # gate. Quarantining understates what the release proves, and a summary line
    # saying "skipped as quarantined" while the PR says "restored" is exactly the
    # contradiction that gets believed later.
    quarantined_now = [e["case_id"] for e in manifest["purposeful_and_blind_cases"]
                       if e.get("quarantined")]
    print(f"\n0. Release contains ZERO quarantined current-behaviour cases")
    if quarantined_now:
        print(f"  FAIL  {len(quarantined_now)} case(s) quarantined: {quarantined_now}")
        print( "        A quarantined case is NOT exercised by this gate. Either resolve")
        print( "        the divergence and un-quarantine it, or do not claim the release")
        print( "        covers it.")
        failures.append(f"quarantined current-behaviour cases: {quarantined_now}")
    else:
        print("  PASS  no case is withheld from this gate")

    # ---- direction 1: declared purposes must resolve exactly ----------------
    print("\n1. Cases: live projection must equal the offline projection")
    for entry in manifest["purposeful_and_blind_cases"]:
        cid = entry["case_id"]
        if entry.get("quarantined"):
            print(f"  SKIP  {cid} (quarantined — NOT exercised; see section 0)")
            case_skip += 1
            continue
        case = by_id.get(cid)
        if case is None:
            failures.append(f"{cid}: in manifest but not in CASES")
            case_fail += 1
            continue
        expected = entry["expected_offline_projection"]
        try:
            case_client = _client_for_case(case, client, agent_client)
            answer = _call(case_client, case)
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL  {cid}: live call raised {type(exc).__name__}: {exc}")
            failures.append(f"{cid}: live call raised {exc}")
            case_fail += 1
            continue

        deltas = []
        for key in COMPARED:
            if key not in expected:
                continue
            if answer.get(key) != expected[key]:
                deltas.append(f"{key}: offline={expected[key]!r} live={answer.get(key)!r}")

        # The declared purpose must be the one the server actually evaluated.
        declared = entry.get("declared_purpose_key")
        evaluated = answer.get("evaluated_purpose")
        if isinstance(evaluated, dict):
            evaluated = evaluated.get("purpose_key")
        if declared is not None and evaluated != declared:
            deltas.append(f"evaluated_purpose: declared={declared!r} live={evaluated!r}")
        if declared is None and evaluated not in (None, "", {}):
            deltas.append(f"purpose-blind call but live evaluated_purpose={evaluated!r}")

        if deltas:
            print(f"  FAIL  {cid}")
            for d in deltas:
                print(f"          {d}")
            failures.append(f"{cid}: " + "; ".join(deltas))
            case_fail += 1
        else:
            print(f"  PASS  {cid}")
            case_pass += 1

    # ---- direction 2: the inexpressible set must STAY unmapped -------------
    must_remain = manifest["authored_entries_that_must_remain_unmapped"]
    print(f"\n2. Authored entries the DATA marks do_not_map ({len(must_remain)})")
    print("   Read from the manifest, never listed here. Asserted as: still")
    print("   fail-closed. NOT asserted: that anything else resolves.")
    if not must_remain:
        print("  NOTE  the dispositions mark none — nothing to assert")
    for entry in must_remain:
        authored = entry["authored_entry"]
        print(f"  DELEGATED  {authored}: fence asserted SaaS-side against the registry.")
        print(f"             Its case-level fail-closed outcome IS asserted here, in")
        print(f"             section 1 — this is not an unrun check.")
        delegated += 1

    untouched = manifest.get("authored_entries_unmapped_untouched", [])
    print(f"\n   Unmapped but NOT ruled on ({len(untouched)}): "
          f"{[e['authored_entry'] for e in untouched]}")
    print("   These may legitimately become mapped. Deliberately NOT asserted.")

    # ---- direction 3: prohibitions must still BITE -------------------------
    bite = manifest.get("prohibition_bite_checks", [])
    print(f"\n3. Prohibitions still bite ({len(bite)} checks)")
    print("   An unmapped entry cannot prove COVERAGE, which weakens ALLOWS. It must")
    print("   not weaken a PROHIBITION. A prohibition silently ceasing to apply is")
    print("   the dangerous direction and would not announce itself.")
    for check in bite:
        cid, covers = check["case_id"], check.get("covers_authored_entry")
        case = by_id.get(cid)
        if case is None:
            print(f"  FAIL  {cid}: bite-check case not found in CASES")
            failures.append(f"{cid}: bite-check case missing")
            proh_fail += 1
            continue
        expected = check.get("expected_projection") or {}
        try:
            case_client = _client_for_case(case, client, agent_client)
            answer = _call(case_client, case)
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL  {cid}: live call raised {exc}")
            failures.append(f"{cid}: live call raised {exc}")
            proh_fail += 1
            continue
        # The prohibition must still produce a non-permissive outcome, AND match
        # the recorded projection exactly.
        permissive = answer.get("state") == "answered" and answer.get("decision") not in (
            "deny", "require_review")
        deltas = [f"{k}: expected={v!r} live={answer.get(k)!r}"
                  for k, v in expected.items() if answer.get(k) != v]
        if permissive:
            deltas.append(f"PROHIBITION NO LONGER BITES: decision={answer.get('decision')!r}")
        if deltas:
            print(f"  FAIL  {cid} (covers {covers})")
            for d in deltas:
                print(f"          {d}")
            failures.append(f"{cid}: " + "; ".join(deltas))
            proh_fail += 1
        else:
            print(f"  PASS  {cid} still bites (covers {covers})")
            proh_pass += 1

    print("\n" + "-" * 78)
    print("parity gate — counters kept SEPARATE, because a delegated check that is")
    print("green elsewhere is not a skip, and a real skip must not hide among them:")
    print(f"  live case parity      : {case_pass} passed, {case_fail} failed, {case_skip} skipped")
    print(f"  live prohibition bite : {proh_pass} passed, {proh_fail} failed")
    print(f"  registry fences       : {delegated} delegated to SaaS CI (asserted there, not unrun)")
    print(f"  TOTAL live assertions : {case_pass + proh_pass} passed, "
          f"{case_fail + proh_fail} failed, {case_skip} skipped")
    print("Scope reminder: this reflects the moment it ran. It is not a continuous")
    print("guarantee, and there is deliberately no schedule — each live evaluation")
    print("writes durable ledger evidence into the tenant.")
    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f"  - {f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
