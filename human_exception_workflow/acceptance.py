#!/usr/bin/env python3
"""Acceptance check for the human-in-the-loop exception workflow example."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common import get_client  # noqa: E402
from human_exception_workflow import run_workflow  # noqa: E402


def main() -> None:
    run = run_workflow(get_client())
    items = {item.request_id: item for item in run.items}

    assert run.total == 3, run
    assert run.ready_without_exception == 1, run
    assert run.resumed_with_controls == 1, run
    assert run.blocked_by_policy == 1, run
    assert run.pending_review == 0, run
    assert run.requires_changes == 0, run
    assert run.rejected_by_reviewer == 0, run

    safe = items["req-001"]
    assert safe.decision == "pass", safe
    assert safe.status == "ready_without_exception", safe
    assert safe.evidence_id, safe
    assert safe.review is None, safe
    assert safe.resume_payload is None, safe

    conditional = items["req-002"]
    assert conditional.decision == "conditional", conditional
    assert conditional.status == "resumed_with_controls", conditional
    assert conditional.evidence_id, conditional
    assert conditional.review is not None, conditional
    assert conditional.review.decision == "approve", conditional
    assert conditional.resume_payload, conditional
    assert conditional.resume_payload["action"] == "resume_controlled_workflow", conditional
    for attestation in ("approval_recorded", "anonymization_before_transfer"):
        assert attestation in conditional.review.controls_attested, conditional

    blocked = items["req-003"]
    assert blocked.decision == "deny", blocked
    assert blocked.status == "blocked_by_policy", blocked
    assert blocked.evidence_id, blocked
    assert blocked.review is None, blocked
    assert blocked.resume_payload is None, blocked

    print(json.dumps(run.to_dict(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
