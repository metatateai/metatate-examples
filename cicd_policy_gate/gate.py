#!/usr/bin/env python3
"""Reusable CI/CD policy gate for Metatate examples.

The gate intentionally depends only on the shared examples client. In offline
mode it reads committed fixtures. In live mode every decision goes through the
Metatate Cloud workspace MCP endpoint.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from common import get_client


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHANGESET_PATH = ROOT / "cicd_policy_gate" / "changes" / "pull_request_042.json"

ALLOW_DECISIONS = {"ALLOW", "APPROVE", "APPROVED"}
CONDITIONAL_DECISIONS = {"CONDITIONAL", "REVIEW", "WARN", "WARNING"}
DENY_DECISIONS = {"DENY", "BLOCK", "BLOCKED", "REJECT"}


GateChange = dict[str, Any]


@dataclass(frozen=True)
class GateResult:
    change_id: str
    kind: str
    source_path: str | None
    description: str
    decision: str
    gate: str
    evidence_id: str | None
    reason_codes: list[str]
    required_controls: list[str]
    action: str
    rationale: str


@dataclass(frozen=True)
class GateSummary:
    change_set_id: str
    description: str
    total: int
    passed: int
    needs_controls: int
    failed: int
    needs_review: int
    strict: bool
    fail_on_controls: bool
    release_allowed: bool
    results: list[GateResult]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["results"] = [asdict(result) for result in self.results]
        return payload


def load_changes(path: str | Path = DEFAULT_CHANGESET_PATH) -> dict[str, Any]:
    """Load a JSON change set.

    The public fixture uses an object with metadata plus a `changes` array, but
    the loader also accepts a raw array so teams can generate it from their own
    pipeline tooling.
    """

    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if isinstance(payload, list):
        return {
            "change_set_id": "ad-hoc",
            "description": "Ad hoc change set",
            "changes": payload,
        }
    if not isinstance(payload, dict) or not isinstance(payload.get("changes"), list):
        raise ValueError("Change set must be a JSON object with a changes array, or a raw JSON array.")
    return payload


def evaluate_changes(
    client: Any,
    change_set: dict[str, Any],
    *,
    strict: bool = False,
    fail_on_controls: bool = False,
) -> GateSummary:
    results = [evaluate_change(client, change) for change in change_set["changes"]]
    passed = sum(1 for result in results if result.gate == "pass")
    controls = sum(1 for result in results if result.gate == "needs_controls")
    failed = sum(1 for result in results if result.gate == "fail")
    review = sum(1 for result in results if result.gate == "needs_review")
    release_allowed = failed == 0 and review == 0 and (not fail_on_controls or controls == 0)

    return GateSummary(
        change_set_id=str(change_set.get("change_set_id") or "ad-hoc"),
        description=str(change_set.get("description") or ""),
        total=len(results),
        passed=passed,
        needs_controls=controls,
        failed=failed,
        needs_review=review,
        strict=strict,
        fail_on_controls=fail_on_controls,
        release_allowed=release_allowed,
        results=results,
    )


def evaluate_change(client: Any, change: GateChange) -> GateResult:
    kind = str(change.get("kind") or "").strip()
    if kind in {"sql_model", "migration_sql", "ad_hoc_sql"}:
        response = _validate_sql_change(client, change)
    elif kind in {"export_job", "ai_training_job", "tool_use", "data_job"}:
        response = _authorize_use_change(client, change)
    else:
        raise ValueError(f"Unsupported change kind {kind!r} for {change.get('change_id')}")

    decision = _decision_label(response)
    gate = _gate_for_decision(decision)

    return GateResult(
        change_id=str(change.get("change_id") or "unknown"),
        kind=kind,
        source_path=change.get("source_path"),
        description=str(change.get("description") or ""),
        decision=decision,
        gate=gate,
        evidence_id=_evidence_id(response),
        reason_codes=_reason_codes(response),
        required_controls=[] if decision in ALLOW_DECISIONS else _required_controls(response),
        action=_action_for_decision(decision, response),
        rationale=_rationale(response),
    )


def print_summary(summary: GateSummary) -> None:
    print(f"Change set: {summary.change_set_id}")
    if summary.description:
        print(summary.description)
    print("")
    print("Gate summary")
    print(f"  pass: {summary.passed}")
    print(f"  needs_controls: {summary.needs_controls}")
    print(f"  fail: {summary.failed}")
    print(f"  needs_review: {summary.needs_review}")
    print("")

    for result in summary.results:
        evidence = f" evidence={result.evidence_id}" if result.evidence_id else ""
        print(f"{result.change_id}: {result.gate} ({result.decision}){evidence}")
        if result.source_path:
            print(f"  source: {result.source_path}")
        if result.rationale:
            print(f"  rationale: {result.rationale}")
        if result.action:
            print(f"  action: {result.action}")
        if result.required_controls:
            print(f"  controls: {'; '.join(result.required_controls)}")

    if summary.strict:
        print("")
        print(f"Release allowed: {str(summary.release_allowed).lower()}")


def _validate_sql_change(client: Any, change: GateChange) -> dict[str, Any]:
    sql = change.get("sql")
    if not sql:
        raise ValueError(f"{change.get('change_id')} is a SQL change but does not include sql.")
    return client.validate_query_context(
        sql,
        operation=change.get("operation") or "read",
        intended_use=change.get("intended_use") or "analytics",
        actor_role=change.get("actor_role"),
        destination_system=change.get("destination_system"),
        destination_jurisdiction=change.get("destination_jurisdiction"),
        consumer_jurisdiction=change.get("consumer_jurisdiction"),
    )


def _authorize_use_change(client: Any, change: GateChange) -> dict[str, Any]:
    table_name = change.get("table_name")
    if not table_name:
        raise ValueError(f"{change.get('change_id')} requires table_name.")
    return client.authorize_use(
        table_name,
        operation=change.get("operation") or "read",
        intended_use=change.get("intended_use") or "analytics",
        actor_role=change.get("actor_role"),
        columns=change.get("columns"),
        destination=change.get("destination"),
        destination_system=change.get("destination_system"),
        destination_jurisdiction=change.get("destination_jurisdiction"),
        consumer_jurisdiction=change.get("consumer_jurisdiction"),
        raw_request_text=change.get("description"),
        context={"source_path": change.get("source_path"), "change_id": change.get("change_id")},
    )


def _decision_label(response: dict[str, Any]) -> str:
    data = response.get("data", {})
    decision = data.get("decision")
    if isinstance(decision, dict):
        return str(decision.get("decision") or decision.get("overall_decision") or "UNKNOWN").upper()
    return str(decision or data.get("overall_decision") or "UNKNOWN").upper()


def _gate_for_decision(decision: str) -> str:
    if decision in ALLOW_DECISIONS:
        return "pass"
    if decision in CONDITIONAL_DECISIONS:
        return "needs_controls"
    if decision in DENY_DECISIONS:
        return "fail"
    return "needs_review"


def _evidence_id(response: dict[str, Any]) -> str | None:
    data = response.get("data", {})
    return data.get("validation_id") or data.get("decision_id") or response.get("request_id")


def _reason_codes(response: dict[str, Any]) -> list[str]:
    data = response.get("data", {})
    decision = data.get("decision")
    if isinstance(decision, dict):
        return [str(code) for code in decision.get("reason_codes") or []]
    return [str(code) for code in data.get("reason_codes") or []]


def _required_controls(response: dict[str, Any]) -> list[str]:
    data = response.get("data", {})
    controls: list[str] = []
    for key in ("conditions", "obligations", "required_controls"):
        values = data.get(key) or []
        if isinstance(values, str):
            controls.append(values)
        else:
            controls.extend(_control_text(value) for value in values)

    return _unique(controls)


def _action_for_decision(decision: str, response: dict[str, Any]) -> str:
    if decision in ALLOW_DECISIONS:
        return "Proceed and record the Metatate evidence ID with the workflow."
    return _agent_action_message(response)


def _agent_action_message(response: dict[str, Any]) -> str:
    action = response.get("data", {}).get("agent_action")
    if isinstance(action, dict):
        return str(action.get("message") or action.get("safe_next_step") or action.get("suggested_next_tool") or "")
    return ""


def _rationale(response: dict[str, Any]) -> str:
    data = response.get("data", {})
    decision = data.get("decision")
    if isinstance(decision, dict):
        return str(decision.get("rationale") or data.get("summary") or "")
    return str(data.get("rationale") or data.get("summary") or "")


def _unique(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        normalized = value.strip()
        if normalized and normalized not in seen:
            result.append(normalized)
            seen.add(normalized)
    return result


def _control_text(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return str(value)


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Metatate CI/CD policy gate.")
    parser.add_argument(
        "--changes",
        default=str(DEFAULT_CHANGESET_PATH),
        help="Path to a JSON change set. Defaults to the AcmeCloud PR fixture.",
    )
    parser.add_argument(
        "--output",
        help="Optional path for the machine-readable JSON gate report.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        default=_env_flag("METATATE_CI_GATE_STRICT"),
        help="Return a non-zero exit code when the release is not allowed.",
    )
    parser.add_argument(
        "--fail-on-controls",
        action="store_true",
        default=_env_flag("METATATE_CI_GATE_FAIL_ON_CONTROLS"),
        help="Treat conditional decisions as blocking in strict mode.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    change_set = load_changes(args.changes)
    summary = evaluate_changes(
        get_client(),
        change_set,
        strict=args.strict,
        fail_on_controls=args.fail_on_controls,
    )

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary.to_dict(), indent=2) + "\n", encoding="utf-8")

    print_summary(summary)
    if args.strict and not summary.release_allowed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
