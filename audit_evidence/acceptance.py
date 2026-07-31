#!/usr/bin/env python3
"""Acceptance checks for the audit evidence packet."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common import get_client  # noqa: E402
from audit_evidence import collect_evidence, render_markdown  # noqa: E402


def main() -> int:
    client = get_client()
    packet = collect_evidence(client)

    assert packet.total == 6, f"expected 6 entries, got {packet.total}"
    assert packet.publication_id, "packet must carry publication provenance"

    # Entries keep DEFAULT_QUESTIONS order: dashboard, export, fine-tune,
    # reroute, legacy corner, monitored mask.
    dash, export, deny, reroute, legacy, review = packet.entries
    assert dash.decision == "allow" and dash.explanation_current is True

    assert export.decision == "conditional"
    assert set(export.conditions) == {"approval_required", "anonymize_first"}
    assert export.explanation_current is True

    assert deny.asset == "acmecloud_demo.public.support_tickets"
    assert deny.decision == "deny" and deny.explanation_current is True
    assert reroute.asset == "acmecloud_demo.public.ml_feature_store"
    assert reroute.decision == "allow" and reroute.explanation_current is True

    assert legacy.state == "not_enough_published_state"
    assert legacy.reason_code == "no_published_instruction_state"
    assert review.asset == "acmecloud_demo.public.employees.full_name"
    assert review.state == "review_required"

    # Every answered decision is explained and CURRENT; both corners honest.
    assert packet.explained == 4 and packet.current == 4
    assert packet.honest_corners == 2

    # Every answered entry cites a policy by display name + version.
    for entry in packet.entries:
        if entry.state == "answered":
            assert entry.policy and entry.policy_version, f"{entry.asset} missing citation"
            assert entry.evidence_id, f"{entry.asset} missing evidence id"

    markdown = render_markdown(packet)
    for marker in (
        "# Metatate evidence packet",
        "## Decisions",
        "## Honest corners",
        "## Ledger",
        "4/4 explained",
        "Explain chain: current = true",
        "refused to guess",
    ):
        assert marker in markdown, f"packet markdown missing {marker!r}"

    # The public client exposes every current server explanation surface.
    # Keep these as two independent source calls: a validation_id is not a
    # decision_id, and an authorization_id is the durable call receipt rather
    # than the serving-row decision cited by that call.
    authorization = client.authorize_use(
        {"database": "acmecloud_demo", "schema": "public", "table": "customers"},
        use="build a churn analytics dashboard",
        scenario_key="purpose.allowed_use",
        purpose_key="analytics.reporting",
    )
    authorization_explain = client.explain_why(
        authorization_id=authorization["authorization_id"]
    )
    assert authorization_explain["kind"] == "authorization"
    assert (
        authorization_explain["authorization_id"]
        == authorization["authorization_id"]
    )

    validation = client.validate_query_context(
        "SELECT region, SUM(arr) FROM customers GROUP BY region",
        scenario_key="purpose.allowed_use",
        default_database="acmecloud_demo",
        default_schema="public",
        purpose_key="analytics.reporting",
    )
    validation_explain = client.explain_why(validation_id=validation["validation_id"])
    assert validation_explain["kind"] == "validation"
    assert validation_explain["validation_id"] == validation["validation_id"]

    print("audit evidence packet acceptance passed")
    print(
        f"  {packet.total} decisions, {packet.current}/{packet.explained} explained+current, "
        f"{packet.honest_corners} honest corners, publication {packet.publication_id}"
    )
    print("  explanation union: decision + authorization + validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
