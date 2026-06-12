#!/usr/bin/env python3
"""Acceptance check for the CI/CD policy gate example."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cicd_policy_gate.gate import evaluate_changes, load_changes  # noqa: E402
from common import get_client  # noqa: E402


EXPECTED_GATES = {
    "chg-001": "pass",
    "chg-002": "needs_controls",
    "chg-003": "fail",
    "chg-004": "needs_controls",
    "chg-005": "fail",
}


def main() -> None:
    summary = evaluate_changes(get_client(), load_changes(), strict=True)
    results = {result.change_id: result for result in summary.results}

    assert summary.total == 5, summary
    assert summary.passed == 1, summary
    assert summary.needs_controls == 2, summary
    assert summary.failed == 2, summary
    assert summary.needs_review == 0, summary
    assert summary.release_allowed is False, summary
    assert set(results) == set(EXPECTED_GATES), results

    for change_id, expected_gate in EXPECTED_GATES.items():
        result = results[change_id]
        assert result.gate == expected_gate, result
        assert result.decision in {"ALLOW", "CONDITIONAL", "DENY"}, result
        assert result.evidence_id, result
        if expected_gate == "fail":
            assert result.action, result
        if expected_gate == "needs_controls":
            assert result.action or result.required_controls, result

    print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
