#!/usr/bin/env python3
"""Acceptance checks for the governed agent arc.

Mode-agnostic (the live workflow runs it too): every assertion is about the
TYPED decision path, not fixture internals. Deterministic by construction —
the ScriptedPlanner is passed explicitly, so no environment variable can put
an LLM in the loop here.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common import get_client  # noqa: E402
from framework_runtime.scenarios import SAFE_ANALYTICS_SQL, UNSAFE_ANALYTICS_SQL  # noqa: E402
from governed_agent_arc.arc import ArcRecordingClient, run_arc  # noqa: E402
from governed_agent_arc.planner import ScriptedPlanner  # noqa: E402

EXPECTED_SEQUENCE = [
    ("inspect_governance_rules", "answered"),
    ("authorize_use", "allow"),
    ("validate_query_context", "warn"),
    ("validate_query_context", "pass"),
    ("authorize_use", "conditional"),
    ("authorize_use", "deny"),
    ("authorize_use", "allow"),
    ("explain_why", "current"),
    ("explain_why", "current"),
    ("explain_why", "current"),
    ("explain_why", "current"),
]


def main() -> int:
    recording = ArcRecordingClient(get_client())
    report = run_arc(recording, ScriptedPlanner())

    # 1. The exact ordered decision sequence — the arc's spine.
    sequence = [(call["tool"], call["label"]) for call in recording.calls]
    assert sequence == EXPECTED_SEQUENCE, f"decision sequence diverged: {sequence}"
    assert report.metatate_calls == len(EXPECTED_SEQUENCE)

    # 2. Self-revision: warned draft, revised once, passing minimized SQL.
    assert report.draft_sql == UNSAFE_ANALYTICS_SQL
    assert report.final_sql == SAFE_ANALYTICS_SQL
    assert report.revision_count == 1
    assert report.dashboard_status == "validated"
    assert "email" not in (report.final_sql or "").lower()

    # 3. Conditional export -> packet -> resumed with attested controls.
    packet = report.exception_packet or {}
    assert report.export_status == "resumed_with_controls"
    assert packet.get("required_attestations") == [
        "approval_recorded",
        "anonymization_before_transfer",
    ]
    assert packet.get("reviewer_queue") == "privacy-review"
    resume = report.resume_payload or {}
    assert resume.get("action") == "resume_controlled_workflow"
    assert resume.get("controls_attested") == [
        "approval_recorded",
        "anonymization_before_transfer",
    ]

    # 4. Deny -> reroute to the governed alternative (never a workaround).
    assert report.rerouted is True
    assert report.training_status == "rerouted_to_governed_alternative"

    # 5. The explain chain: every collected decision id resolves and is current.
    assert len(report.explanations) == 4
    for explanation in report.explanations:
        assert explanation["current"] is True
        assert explanation["decision_id"]

    # 6. Every recorded call carries evidence (decision id or publication id).
    for call in recording.calls:
        assert call.get("evidence_id"), f"call without evidence: {call}"

    print("governed agent arc acceptance passed")
    print(
        f"  sequence: {' -> '.join(label for _tool, label in sequence)}"
    )
    print(
        f"  dashboard={report.dashboard_status} export={report.export_status} "
        f"training={report.training_status} explains=4/4 current"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
