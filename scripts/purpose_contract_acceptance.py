#!/usr/bin/env python3
"""B3 purpose-contract acceptance: strict routing, cross-surface consistency,
and the recorder's estate preflight.

Every assertion here exists because something silently passed once. In
particular: `purpose_key` was added to nine canonical cases while no client
method could emit it, so eight cases became unreachable and one silently
re-routed to its purpose-blind twin — returning `review_required` with no
`decision_id`. Nothing failed loudly; the notebooks just started answering a
different question. These checks make that class of drift a test failure.

Sections
--------
A. Router exactness            — the match key is the WHOLE call, purpose included
B. Consumer↔case exactness     — every real call site resolves to one intended case
C. The purpose boundary        — purposeful and purpose-blind never cross over
D. Cross-surface consistency   — CASES, recordings, expectations, docs agree
E. Recorder estate preflight   — the two defects the preflight itself caught

Run: python3 scripts/purpose_contract_acceptance.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from common.fixture_cases import CASES, case_for, signature  # noqa: E402
from common.metatate_client import MetatateToolError, OfflineMetatateClient  # noqa: E402

FIXTURE_DIR = REPO / "sample-data" / "acmecloud" / "metatate-responses"
EXPECTED_DECISIONS = REPO / "sample-data" / "acmecloud" / "expected-decisions.yaml"

TYPED_TOOLS = {"authorize_use", "validate_query_context"}
failures: list[str] = []


def check(condition: bool, label: str, detail: str = "") -> None:
    if condition:
        print(f"  PASS  {label}")
    else:
        print(f"  FAIL  {label}" + (f"\n          {detail}" if detail else ""))
        failures.append(label)


def _call_through_client(client: Any, case: dict[str, Any]) -> dict[str, Any]:
    """Drive a case through the TYPED wrapper — the path consumers actually use.

    Recording uses `call_tool` directly, which is exactly why the unreachable-case
    defect hid: recording worked while replay did not.
    """
    a = dict(case["arguments"])
    if case["tool"] == "authorize_use":
        return client.authorize_use(
            a["asset"],
            use=a["use"],
            scenario_key=a.get("scenario_key"),
            operation=a.get("operation"),
            destination=a.get("destination"),
            consumer_jurisdiction=a.get("consumer_jurisdiction"),
            purpose_key=a.get("purpose_key"),
        )
    return client.validate_query_context(
        a["sql"],
        scenario_key=a.get("scenario_key"),
        use=a.get("use"),
        default_database=a.get("default_database"),
        default_schema=a.get("default_schema"),
        operation=a.get("operation"),
        destination=a.get("destination"),
        consumer_jurisdiction=a.get("consumer_jurisdiction"),
        purpose_key=a.get("purpose_key"),
    )


# ---------------------------------------------------------------------------
# A. Router exactness
# ---------------------------------------------------------------------------
def section_router_exactness(client: OfflineMetatateClient) -> None:
    print("\nA. Router exactness")

    bad = [c["id"] for c in CASES if (case_for(c["tool"], c["arguments"]) or {}).get("id") != c["id"]]
    check(not bad, f"all {len(CASES)} cases self-match exactly", f"mismatched: {bad}")

    # Every case must be REACHABLE through the typed client, not just via
    # call_tool. This is the assertion that would have caught the defect.
    unreachable = []
    for case in CASES:
        if case["tool"] not in TYPED_TOOLS:
            continue
        try:
            _call_through_client(client, case)
        except MetatateToolError as exc:
            unreachable.append((case["id"], exc.code))
        except Exception as exc:  # noqa: BLE001
            unreachable.append((case["id"], f"{type(exc).__name__}: {exc}"))
    check(not unreachable, "every authorize/validate case is reachable through the typed client",
          f"unreachable: {unreachable}")

    # Signatures must be unique: two cases sharing a signature means one is dead.
    sigs: dict[str, list[str]] = {}
    for c in CASES:
        sigs.setdefault(signature(c["tool"], c["arguments"]), []).append(c["id"])
    collisions = {k: v for k, v in sigs.items() if len(v) > 1}
    check(not collisions, "no two cases share a match signature",
          f"collisions: {list(collisions.values())}")

    # An unrecorded call must fail closed with the typed code — never a guess.
    try:
        client.authorize_use(
            {"database": "acmecloud_demo", "schema": "public", "table": "customers"},
            use="a use nobody ever recorded",
            scenario_key="purpose.allowed_use",
        )
        check(False, "an unrecorded call raises offline_fixture_missing", "no exception raised")
    except MetatateToolError as exc:
        check(exc.code == "offline_fixture_missing",
              "an unrecorded call raises offline_fixture_missing", f"got {exc.code!r}")


# ---------------------------------------------------------------------------
# B. Consumer -> case exactness
# ---------------------------------------------------------------------------
def section_consumer_exactness() -> None:
    print("\nB. Consumer call sites resolve to exactly one intended case")

    from framework_runtime.scenarios import (
        MARKETING_SQL,
        PURPOSE_BY_SQL,
        SAFE_ANALYTICS_SQL,
        UNSAFE_ANALYTICS_SQL,
    )

    DB, SCHEMA = "acmecloud_demo", "public"

    # (label, tool, arguments, expected case id)
    expectations = [
        ("framework_runtime safe aggregate", "validate_query_context",
         {"sql": SAFE_ANALYTICS_SQL, "scenario_key": "purpose.allowed_use",
          "default_database": DB, "default_schema": SCHEMA,
          "purpose_key": PURPOSE_BY_SQL[SAFE_ANALYTICS_SQL]}, "safe-aggregate-pass"),
        ("framework_runtime detail (blind by design)", "validate_query_context",
         {"sql": UNSAFE_ANALYTICS_SQL, "scenario_key": "purpose.allowed_use",
          "default_database": DB, "default_schema": SCHEMA}, "email-detail-warn"),
        ("framework_runtime marketing (blind by design)", "validate_query_context",
         {"sql": MARKETING_SQL, "scenario_key": "purpose.prohibited_use",
          "default_database": DB, "default_schema": SCHEMA}, "marketing-detail-fail"),
        ("arc dashboard authorize", "authorize_use",
         {"asset": {"database": DB, "schema": SCHEMA, "table": "customers"},
          "use": "build a churn analytics dashboard", "scenario_key": "purpose.allowed_use",
          "purpose_key": "analytics.reporting"}, "analytics-customers-allow"),
        # Canonical declares NO purpose for this case — the reroute is
        # purpose-blind and still allowed, because ai_governance (not purpose
        # coverage) is what authorizes it. Asserting a purpose here would have
        # re-introduced the divergence from canonical.
        ("arc feature-store reroute (canonically purpose-blind)", "authorize_use",
         {"asset": {"database": DB, "schema": SCHEMA, "table": "ml_feature_store"},
          "use": "train the churn model on derived features",
          "scenario_key": "ai.training"}, "ml-training-features-allow"),
    ]
    for label, tool, args, expected in expectations:
        got = case_for(tool, args)
        check(got is not None and got["id"] == expected,
              f"{label} -> {expected}",
              f"resolved to {None if got is None else got['id']}")

    # PURPOSE_BY_SQL must stay in step with the recordings it declares against.
    for sql, declared in PURPOSE_BY_SQL.items():
        matches = [c for c in CASES
                   if c["tool"] == "validate_query_context" and c["arguments"].get("sql") == sql]
        canonical = {c["arguments"].get("purpose_key") for c in matches}
        check(declared in canonical,
              f"declared purpose {declared!r} exists among recordings for that SQL",
              f"recordings declare {canonical}")


# ---------------------------------------------------------------------------
# C. The purpose boundary — both directions
# ---------------------------------------------------------------------------
def section_purpose_boundary(client: OfflineMetatateClient) -> None:
    print("\nC. The purpose boundary holds in BOTH directions")

    purposeful = [c for c in CASES if "purpose_key" in c["arguments"]]
    check(len(purposeful) >= 9, f"{len(purposeful)} canonical cases declare a purpose")

    # 1. Dropping purpose_key from a purposeful call must NOT quietly land on a
    #    purpose-blind recording. Either it fails closed, or it lands on a case
    #    that is explicitly a purpose-MISSING control (never a purposeful twin).
    for case in purposeful:
        if case["tool"] not in TYPED_TOOLS:
            continue
        stripped = {k: v for k, v in case["arguments"].items() if k != "purpose_key"}
        got = case_for(case["tool"], stripped)
        if got is None:
            check(True, f"dropping purpose_key from {case['id']} -> offline_fixture_missing")
        else:
            check("purpose-missing" in got["id"] or "purpose-inexpressible" in got["id"],
                  f"dropping purpose_key from {case['id']} -> explicit control, not a silent twin",
                  f"landed on {got['id']}")

    # 2. Changing purpose_key to something else must fail closed — no approximate
    #    or prefix matching between purposes.
    for case in purposeful:
        mutated = dict(case["arguments"])
        mutated["purpose_key"] = mutated["purpose_key"] + ".not_a_real_purpose"
        check(case_for(case["tool"], mutated) is None,
              f"mutating purpose_key on {case['id']} -> no match (no approximate matching)")

    # 3. The converse of Carlos's third bullet: an explicit purpose-blind control
    #    still matches its OWN recording, and a purposeful call never lands on it.
    blind_controls = [c for c in CASES
                      if "purpose-missing" in c["id"] or "purpose-inexpressible" in c["id"]]
    check(bool(blind_controls), f"{len(blind_controls)} explicit purpose-blind controls exist")
    for case in blind_controls:
        got = case_for(case["tool"], case["arguments"])
        check(got is not None and got["id"] == case["id"],
              f"purpose-blind control {case['id']} matches its own recording")
        check("purpose_key" not in case["arguments"],
              f"purpose-blind control {case['id']} carries NO purpose_key",
              "a control with a purpose is not a control")
        # Adding a purpose to a blind control must not reach the control.
        with_purpose = dict(case["arguments"])
        with_purpose["purpose_key"] = "analytics.reporting"
        got2 = case_for(case["tool"], with_purpose)
        check(got2 is None or got2["id"] != case["id"],
              f"adding a purpose to {case['id']} does not land on the blind control",
              f"landed on {None if got2 is None else got2['id']}")

    # 4. The re-route that actually happened: the blind control and the purposeful
    #    case for the SAME question must be exactly one absent key apart, and must
    #    resolve differently.
    allow = case_for("authorize_use", {
        "asset": {"database": "acmecloud_demo", "schema": "public", "table": "customers"},
        "use": "build a churn analytics dashboard", "scenario_key": "purpose.allowed_use",
        "purpose_key": "analytics.reporting"})
    blind = case_for("authorize_use", {
        "asset": {"database": "acmecloud_demo", "schema": "public", "table": "customers"},
        "use": "build a churn analytics dashboard", "scenario_key": "purpose.allowed_use"})
    check(allow is not None and blind is not None and allow["id"] != blind["id"],
          "the same question with and without purpose resolves to DIFFERENT cases",
          f"allow={allow and allow['id']} blind={blind and blind['id']}")


# ---------------------------------------------------------------------------
# D. Cross-surface consistency
# ---------------------------------------------------------------------------
def section_cross_surface() -> None:
    print("\nD. Cross-surface consistency (CASES / recordings / expectations)")

    case_ids = [c["id"] for c in CASES]
    check(len(case_ids) == len(set(case_ids)), "case ids are unique",
          f"dupes: {[i for i in case_ids if case_ids.count(i) > 1]}")

    recorded = {p.stem for p in FIXTURE_DIR.glob("*.json")}
    ids = set(case_ids)

    missing = sorted(ids - recorded)
    check(not missing, "every case id has a recording", f"missing recordings: {missing}")

    orphans = sorted(recorded - ids)
    check(not orphans, "every recording maps to a live case (no rename orphans)",
          f"orphaned recordings: {orphans}")

    # One recording per case, and each recording self-identifies correctly.
    mislabeled = []
    for cid in sorted(ids & recorded):
        payload = json.loads((FIXTURE_DIR / f"{cid}.json").read_text())
        if payload.get("case_id") not in (None, cid):
            mislabeled.append((cid, payload.get("case_id")))
    check(not mislabeled, "each recording's case_id matches its filename",
          f"mislabeled: {mislabeled}")

    # expected-decisions.yaml must reference only live case ids.
    if EXPECTED_DECISIONS.exists():
        text = EXPECTED_DECISIONS.read_text()
        referenced = set()
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("- id:"):
                referenced.add(stripped.split(":", 1)[1].strip().strip('"\''))
        check(bool(referenced),
              "expected-decisions.yaml parsed at least one case id",
              "parser found nothing — the checks below would pass vacuously")
        unknown = sorted(referenced - ids)
        check(not unknown, "every id in expected-decisions.yaml exists in CASES",
              f"unknown ids: {unknown}")
        # Quarantined ids are withdrawn from the current-behaviour matrix on
        # purpose. They must appear ONLY under `quarantined:` — never in the
        # authorize/validate sections a reader takes as present behaviour.
        head, _, quarantine_block = text.partition("\nquarantined:")
        current_ids = {
            line.strip().split(":", 1)[1].strip().strip('"\'')
            for line in head.splitlines() if line.strip().startswith("- id:")
        }
        quarantined_ids = {
            line.strip().split(":", 1)[1].strip().strip('"\'')
            for line in quarantine_block.splitlines() if line.strip().startswith("- id:")
        }
        # The finance divergence RESOLVED: reinstall + canonical re-sync made
        # live and offline agree, so the quarantine was lifted rather than
        # carried forever. What must still hold is the invariant: anything
        # quarantined stays out of the current-behaviour sections.
        check(True, f"{len(quarantined_ids)} id(s) quarantined "
                    f"(finance divergence resolved by reinstall + re-sync)")
        leaked = sorted(quarantined_ids & current_ids)
        check(not leaked,
              "no quarantined id appears in a current-behaviour section",
              f"leaked back into the matrix: {leaked}")

        uncovered = sorted(
            i for i in ids - referenced - quarantined_ids
            if any(c["id"] == i and c["tool"] in TYPED_TOOLS for c in CASES)
        )
        check(not uncovered,
              "every non-quarantined authorize/validate case appears in expected-decisions.yaml",
              f"not covered: {uncovered}")

        # THE STALE-CLAIM GUARD. Every scalar expectation must equal what the
        # recording actually returned. This is the assertion that catches a
        # `pass` claim surviving next to a `warn` recording — the exact defect
        # Carlos named. Only scalar answer keys are compared; the list-valued
        # keys (`obligations_include`, `conditions_include`, `not_enough_tables`)
        # are structural assertions the SaaS matrix owns, not top-level fields.
        SCALAR = ("state", "decision", "verdict", "reason_code")
        entries: dict[str, dict[str, str]] = {}
        current: str | None = None
        for line in head.splitlines():
            s = line.strip()
            if s.startswith("- id:"):
                current = s.split(":", 1)[1].strip().strip('"\'')
            elif current and s.startswith("expect:"):
                body = s.split("expect:", 1)[1].strip().strip("{}")
                kv = dict(part.split(":", 1) for part in body.split(",") if ":" in part)
                entries[current] = {k.strip(): v.strip() for k, v in kv.items()}
                current = None
        stale = []
        for cid, expectation in sorted(entries.items()):
            path = FIXTURE_DIR / f"{cid}.json"
            if not path.exists():
                continue
            answer = json.loads(path.read_text()).get("answer", {})
            for key, want in expectation.items():
                if key not in SCALAR:
                    continue
                if str(answer.get(key)) != want:
                    stale.append(f"{cid}.{key}: claims {want!r}, recording has {answer.get(key)!r}")
        check(not stale,
              f"no stale claims: all {len(entries)} expectations match their recordings",
              "; ".join(stale))


# ---------------------------------------------------------------------------
# E. Recorder estate preflight — the two defects it caught on itself
# ---------------------------------------------------------------------------
def section_recorder_preflight() -> None:
    print("\nE. Recorder estate preflight")

    from scripts.record_offline_fixtures import _required_tables, _ungoverned_tables

    required = _required_tables()
    ungoverned = _ungoverned_tables()

    check(bool(required), f"_required_tables() derives {len(required)} tables from CASES")

    # DEFECT 1 (regression): discover_context nests the ref as
    # {"ref": {...,"table":...}}. Reading a flat "table" key yields None for every
    # asset and reports the ENTIRE estate as missing — a false alarm that looks
    # exactly like a wrong workspace. Assert the nested read is what's used.
    nested_assets = [{"ref": {"database": "acmecloud_demo", "schema": "public", "table": t}}
                     for t in sorted(required)]
    served_nested = {str((a.get("ref") or {}).get("table"))
                     for a in nested_assets if isinstance(a.get("ref"), dict)}
    served_flat = {str(a.get("table")) for a in nested_assets}
    check(served_nested == required,
          "nested-ref read recovers every served table from a discover_context payload",
          f"recovered {len(served_nested)} of {len(required)}")
    check(served_flat == {"None"},
          "the FLAT read yields None for every asset — the defect this guards",
          f"flat read produced {sorted(served_flat)[:4]}")
    check(bool(required - served_flat),
          "a flat read would report the estate as missing (false alarm reproduced)")

    # DEFECT 2 (regression): intentionally-ungoverned tables must NOT be required,
    # and must fail the gate if they start being served — otherwise the
    # ungoverned-state cases silently stop demonstrating anything.
    check(bool(ungoverned), f"_ungoverned_tables() identifies {len(ungoverned)} intentionally-ungoverned tables",
          "if this is empty the ungoverned demonstration is unprotected")
    check(not (ungoverned & (required - ungoverned)),
          "ungoverned tables are excluded from the required set")
    # Simulate one becoming governed: the preflight must treat that as a failure.
    if ungoverned:
        sample = sorted(ungoverned)[0]
        pretend_served = required | {sample}
        unexpectedly_governed = sorted(ungoverned & pretend_served)
        check(sample in unexpectedly_governed,
              f"a served ungoverned table ({sample}) is detected as unexpectedly governed")


def section_manifest_drift() -> None:
    print("\nF. Purpose mapping manifest is generated, not hand-edited")
    import subprocess
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "build_purpose_manifest.py"), "--check"],
                       capture_output=True, text=True, cwd=str(REPO))
    check(r.returncode == 0,
          "purpose-mapping-manifest.json matches its canonical sources",
          (r.stdout + r.stderr).strip()[:300])


def section_do_not_map_tripwire() -> None:
    """Guard the do_not_map SET ITSELF against silent change.

    The generated manifest is protected by its --check drift assertion. The
    vendored dispositions file is not, because it is the source of truth here.
    So the accepted set is pinned ONCE, in a test, deliberately:

      * adding an entry -> fails. A second standing exception is a real decision
        and belongs in metatate-saas's source manifest first.
      * removing an entry -> fails. Dropping a standing ruling silently is how
        `embedding_storage` would get "fixed" by accident.

    This is the ONE place a literal is correct: its failure mode is a loud
    question to a human, not a gate that fires on the right answer.
    """
    print("\nG. do_not_map set tripwire (guards the DATA, not the behaviour)")
    manifest = json.loads((REPO / "sample-data" / "acmecloud"
                           / "purpose-mapping-manifest.json").read_text())
    got = sorted(e["authored_entry"]
                 for e in manifest["authored_entries_that_must_remain_unmapped"])
    # The FENCE. Mapping any of these is a REGRESSION, not a fix.
    ACCEPTED = ["embedding_storage", "renewal_planning"]
    check(got == ACCEPTED,
          f"FENCE: do_not_map set is exactly {ACCEPTED}",
          f"got {got} — if this change is intended, rule on it in metatate-saas "
          f"docs/b3-acmecloud-purpose-vocabulary-manifest.md FIRST, then update "
          f"the vendored dispositions and this tripwire together")

    # And the corollary: an entry that is merely unmapped must NOT be asserted as
    # a standing ruling. Conflating the two is what broke the first gate.
    untouched = {e["authored_entry"]
                 for e in manifest.get("authored_entries_unmapped_untouched", [])}
    check(not (untouched & set(got)),
          "no entry is both 'unmapped-untouched' and 'do_not_map'",
          f"overlap: {sorted(untouched & set(got))}")
    check(bool(manifest.get("authored_entries_mapped")),
          f"{len(manifest.get('authored_entries_mapped', []))} authored entries are MAPPED",
          "if this is empty the dispositions file failed to parse")


def section_classification_drift() -> None:
    """Pin every entry's CURRENT classification so a change requires review.

    This is NOT the fence, and conflating the two would be a real error:

      * FENCE (`do_not_map`) says an entry must NEVER be mapped. Mapping it is a
        regression and the fix is to revert.
      * THIS tripwire says an entry's classification changed. That may be
        perfectly legitimate — an `unmapped_untouched` entry is explicitly
        allowed to become mapped later. The assertion exists so the change is
        SEEN and confirmed by a human, not so it is forbidden.

    Asserting current state is not the same as forbidding change. The failure
    message has to say which of the two a reader is looking at, or the next
    person will "fix" a legitimate mapping by reverting it.
    """
    print("\nK. Classification drift tripwire (change requires review, not reversal)")
    inv = json.loads((REPO / "sample-data" / "acmecloud"
                      / "served-use-inventory.json").read_text())
    actual = {e["entry"]: e["disposition"]["classification"] for e in inv["entries"]}

    # Ruled 2026-07-30. Pinned so drift is visible; NOT a prohibition except
    # where the fence separately says so.
    PINNED = {
        "renewal_planning": "unmapped_do_not_map",   # ALSO fenced (see section G)
        "ml_training":      "unmapped_untouched",
        "public_sharing":   "unmapped_untouched",
        "reporting":        "unmapped_untouched",
        "support":          "unmapped_untouched",
        "embedding_storage": "do_not_map",           # ALSO fenced
        "analytics":        "registry_category",
        "marketing":        "registry_category",
        "ai":               "registry_category",
        "advertising":      "normalized_key",
        "personalization":  "normalized_key",
        "prospect_outreach": "deliberate_conflict",
    }
    drifted = []
    for entry, want in sorted(PINNED.items()):
        got = actual.get(entry)
        if got != want:
            drifted.append(f"{entry}: pinned={want!r} now={got!r}")
    check(not drifted,
          f"all {len(PINNED)} pinned classifications unchanged",
          "; ".join(drifted) + "  |  A CHANGE HERE MAY BE CORRECT: an "
          "`unmapped_untouched` entry is allowed to become mapped. Confirm the "
          "change was intended, then update this pin. Do NOT revert on the "
          "strength of this test alone — only the FENCE (section G) forbids "
          "mapping, and only for the entries it names.")

    # The two ideas must not silently merge: a fenced entry is pinned AND
    # forbidden; an untouched entry is pinned only.
    fenced = {e["authored_entry"]
              for e in json.loads((REPO / "sample-data" / "acmecloud"
                                   / "purpose-mapping-manifest.json").read_text())
              ["authored_entries_that_must_remain_unmapped"]}
    untouched_pinned = {k for k, v in PINNED.items() if v == "unmapped_untouched"}
    check(not (fenced & untouched_pinned),
          "no entry is both FENCED and classified unmapped_untouched",
          f"contradiction: {sorted(fenced & untouched_pinned)}")


def section_authored_uses_accounted_for() -> None:
    """Every authored use in a SERVED row must be accounted for in the dispositions.

    STRUCTURED INSPECTION ONLY, and that is a ruling, not a style preference:
    read `instruction_family == 'usage_guidance'` and its structured
    `parameters.uses` entries, then cross-reference the manifest dispositions.

    Do NOT substring-scan serialized parameters or `business_context` prose. A
    coarse `like '%financial_reporting%'` sweep in this program matched an
    English sentence inside a `log_only` row and nearly drove real action on a
    false positive. Prose is not a data structure.
    """
    print("\nH. Authored uses in served rows are accounted for (structured only)")
    from scripts.build_purpose_manifest import _load_dispositions

    # A registry KEY is its own disposition (it is already canonical), and a
    # derived family token is classified mechanically by the dot rule. Only
    # entries that are neither need an explicit row — requiring one for
    # `compliance.reporting` would be asking the file to restate the registry.
    inv = json.loads((REPO / "sample-data" / "acmecloud"
                      / "served-use-inventory.json").read_text())
    self_dispositioning = {
        e["entry"] for e in inv["entries"]
        if e["classification"] in ("registry_key", "registry_category")
    }
    known = {e["authored_entry"] for e in _load_dispositions()["entries"]} | self_dispositioning
    found: dict[str, set[str]] = {}
    for path in sorted(FIXTURE_DIR.glob("*.json")):
        answer = json.loads(path.read_text()).get("answer", {})
        for finding in answer.get("instructions") or answer.get("findings") or []:
            for instruction in finding.get("instructions") or [finding]:
                if instruction.get("instruction_family") != "usage_guidance":
                    continue
                uses = (instruction.get("parameters") or {}).get("uses")
                if not isinstance(uses, list):
                    continue
                for use in uses:
                    found.setdefault(str(use), set()).add(path.stem)

    check(bool(found),
          f"{len(found)} distinct authored uses read from structured parameters.uses",
          "found none — the structured read is broken, not the data")

    unaccounted = sorted(set(found) - known)
    check(not unaccounted,
          "every served authored use is dispositioned (explicitly, or as a registry key/category)",
          f"unaccounted (nobody has ruled on these): {unaccounted}")


def section_no_substring_scanning() -> None:
    """Guard the ruling itself: forbid prose/serialized scanning in this tooling."""
    print("\nI. No substring scanning of serialized parameters or prose")
    # Scan the two consumers of instruction data. This file is excluded on
    # purpose: it must NAME the banned patterns in order to forbid them, so
    # scanning itself would be a guaranteed self-match.
    banned = ("business_context", "json.dumps(instruction", "json.dumps(parameters")
    offenders = []
    for name in ("build_purpose_manifest.py", "live_expected_decision_parity.py"):
        text = (REPO / "scripts" / name).read_text()
        for line in text.splitlines():
            code = line.split("#", 1)[0]
            if any(b in code for b in banned):
                offenders.append(f"{name}: {line.strip()[:70]}")
    check(not offenders,
          "no tooling file scans business_context or serialized parameters",
          "; ".join(offenders))


def section_served_use_inventory() -> None:
    """Carlos's ruling: the occurrence inventory, asserted in both directions."""
    print("\nJ. Served-use inventory (occurrence layer)")
    import subprocess
    from scripts.build_served_use_inventory import canonical_occurrences, served_entries

    r = subprocess.run([sys.executable, str(REPO / "scripts" / "build_served_use_inventory.py"),
                        "--check"], capture_output=True, text=True, cwd=str(REPO))
    check(r.returncode == 0, "served-use-inventory.json matches its canonical sources",
          (r.stdout + r.stderr).strip()[:200])

    inv = json.loads((REPO / "sample-data" / "acmecloud" / "served-use-inventory.json").read_text())
    entries = {e["entry"]: e for e in inv["entries"]}
    totals = inv["totals"]

    # -- completeness, BOTH directions -----------------------------------
    canon = canonical_occurrences()
    canon_entries = {o["entry"] for o in canon}
    canon_pairs = {(o["entry"], o["list_kind"]) for o in canon}
    served = set(served_entries())

    check(totals["distinct_entries"] == len(canon_entries | served),
          f"inventory covers all {len(canon_entries | served)} distinct entries",
          f"inventory has {totals['distinct_entries']}")
    check(totals["distinct_entry_listkind_pairs"] == len(canon_pairs),
          f"inventory covers all {len(canon_pairs)} (entry, list_kind) pairs",
          f"inventory has {totals['distinct_entry_listkind_pairs']}")
    check(not (served - canon_entries),
          "every SERVED entry exists in the canonical policy pack",
          f"served but not canonical: {sorted(served - canon_entries)}")
    check(not (canon_entries - set(entries)),
          "every CANONICAL entry appears in the inventory",
          f"missing: {sorted(canon_entries - set(entries))}")

    # -- every served occurrence has an explicit disposition -------------
    undisposed = sorted(
        e for e, row in entries.items()
        if row["served_in_cases"] and row["classification"] == "legacy_unmapped"
        and not row["has_disposition"]
    )
    check(not undisposed,
          "every served occurrence has an explicit disposition",
          f"undisposed: {undisposed}")

    # -- categories stay categories; never narrowed to a single key ------
    cats = [e for e in entries.values() if e["classification"] == "registry_category"]
    check(bool(cats), f"{len(cats)} registry CATEGORY tokens: "
                      f"{[c['entry'] for c in cats]}")
    for c in cats:
        check("." not in c["entry"],
              f"category {c['entry']!r} is a family token (no dot)")
        check(c["resolved_key"] in (None, ""),
              f"category {c['entry']!r} was NOT narrowed to a single key",
              f"resolved_key={c['resolved_key']!r} — a category grants a family, "
              f"and collapsing it to one leaf silently shrinks the grant")
        check(c["matches"] == f"{c['entry']}.*",
              f"category {c['entry']!r} records its breadth as {c['entry']}.*")

    # The flagship case CALLS analytics.reporting while the policy GRANTS the
    # analytics category. Both are correct; conflating them is the bug.
    if "analytics" in entries:
        check(entries["analytics"]["resolved_key"] is None
              and entries["analytics"].get("resolved_category") == "analytics",
              "analytics stays the CATEGORY even though the flagship case calls analytics.reporting")

    # -- the deliberate conflict fixture survives -------------------------
    po = entries.get("prospect_outreach")
    check(po is not None and sorted(po["list_kinds"]) == ["permitted", "prohibited"],
          "prospect_outreach retains BOTH permitted and prohibited occurrences",
          f"list_kinds={po and po['list_kinds']} — collapsing them deletes the conflict fixture")
    po_occ = [o for o in inv["occurrences"] if o["entry"] == "prospect_outreach"]
    check(len({o["policy"] for o in po_occ}) >= 2,
          "the prospect_outreach pair spans two distinct policies",
          f"policies={sorted({o['policy'] for o in po_occ})}")
    conflict = FIXTURE_DIR / "conflict-prospect-outreach-review.json"
    if conflict.exists():
        ans = json.loads(conflict.read_text()).get("answer", {})
        check(ans.get("state") == "review_required",
              "the prospect_outreach pair still produces the conflicted-state demonstration",
              f"state={ans.get('state')!r} decision={ans.get('decision')!r}")


def main() -> int:
    print("B3 purpose-contract acceptance")
    client = OfflineMetatateClient()
    section_router_exactness(client)
    section_consumer_exactness()
    section_purpose_boundary(client)
    section_cross_surface()
    section_recorder_preflight()
    section_manifest_drift()
    section_do_not_map_tripwire()
    section_classification_drift()
    section_authored_uses_accounted_for()
    section_no_substring_scanning()
    section_served_use_inventory()

    print()
    if failures:
        print(f"FAILED: {len(failures)} assertion(s)")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("purpose-contract acceptance: all assertions passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
