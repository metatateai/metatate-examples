#!/usr/bin/env python3
"""Reusable CI/CD policy gate for Metatate examples — native typed answers.

The gate depends only on the shared examples client. In offline mode it
replays recorded Metatate Cloud answers; in live mode every decision goes
through your workspace's MCP endpoint. Change sets carry canonical
`scenario_key`s (the same vocabulary the server speaks) — the gate is the
worked example of mapping CI metadata onto the decision layer and turning
typed answers (`state`, `decision`/`verdict`, `conditions`, `obligations`)
into pass / needs_controls / fail gates with reviewable reason codes.
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

SQL_KINDS = {"sql_model", "migration_sql", "ad_hoc_sql"}
USE_KINDS = {"export_job", "ai_training_job", "tool_use", "data_job"}

PASS_DECISIONS = {"allow", "log_only", "retain"}
CONTROL_DECISIONS = {"conditional", "mask_full", "mask_partial"}

DENY_SCENARIO_CODES = {
    "purpose.prohibited_use": "PROHIBITED_USE",
    "ai.training": "AI_TRAINING_BLOCKED",
    "residency.cross_border_transfer": "TRANSFER_DENIED",
}
CONDITION_CODES = {
    "approval_required": "APPROVAL_REQUIRED",
    "anonymize_first": "ANONYMIZATION_REQUIRED",
    "role_restricted": "ROLE_RESTRICTED",
    "ai_restriction": "AI_RESTRICTION",
}


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
    if kind in SQL_KINDS:
        answer = _validate_sql_change(client, change)
        decision, gate = _gate_for_validation(answer)
        evidence = _publication_id(answer)
        reason_codes = _validation_reason_codes(answer)
        controls = _validation_controls(answer)
        rationale = _validation_rationale(answer)
    elif kind in USE_KINDS:
        answer = _authorize_use_change(client, change)
        decision, gate = _gate_for_authorization(answer)
        evidence = answer.get("decision_id") or _publication_id(answer)
        reason_codes = _authorization_reason_codes(answer)
        controls = _authorization_controls(answer)
        rationale = str(answer.get("reason") or "")
    else:
        raise ValueError(f"Unsupported change kind {kind!r} for {change.get('change_id')}")

    return GateResult(
        change_id=str(change.get("change_id") or "unknown"),
        kind=kind,
        source_path=change.get("source_path"),
        description=str(change.get("description") or ""),
        decision=decision,
        gate=gate,
        evidence_id=evidence,
        reason_codes=reason_codes,
        required_controls=[] if gate == "pass" else controls,
        action=_action(gate, answer),
        rationale=rationale,
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
        if result.reason_codes:
            print(f"  reason_codes: {', '.join(result.reason_codes)}")

    if summary.strict:
        print("")
        print(f"Release allowed: {str(summary.release_allowed).lower()}")


# ---------------------------------------------------------------------------
# Tool calls (native argument shapes)
# ---------------------------------------------------------------------------


def _validate_sql_change(client: Any, change: GateChange) -> dict[str, Any]:
    sql = change.get("sql")
    if not sql:
        raise ValueError(f"{change.get('change_id')} is a SQL change but does not include sql.")
    return client.validate_query_context(
        sql,
        scenario_key=change.get("scenario_key"),
        use=change.get("use"),
        default_database=change.get("default_database"),
        default_schema=change.get("default_schema"),
        operation=change.get("operation"),
        destination=change.get("destination"),
        consumer_jurisdiction=change.get("consumer_jurisdiction"),
    )


def _authorize_use_change(client: Any, change: GateChange) -> dict[str, Any]:
    asset = change.get("asset")
    if not isinstance(asset, dict):
        raise ValueError(f"{change.get('change_id')} requires an asset reference.")
    return client.authorize_use(
        asset,
        use=str(change.get("use") or change.get("description") or ""),
        scenario_key=change.get("scenario_key"),
        operation=change.get("operation"),
        destination=change.get("destination"),
        consumer_jurisdiction=change.get("consumer_jurisdiction"),
    )


# ---------------------------------------------------------------------------
# Typed answer -> gate
# ---------------------------------------------------------------------------


def _gate_for_validation(answer: dict[str, Any]) -> tuple[str, str]:
    state = str(answer.get("state") or "")
    if state != "answered":
        return state or "unknown", "needs_review"
    verdict = str(answer.get("verdict") or "")
    gate = {"pass": "pass", "warn": "needs_controls", "fail": "fail"}.get(verdict, "needs_review")
    return verdict or "unknown", gate


def _gate_for_authorization(answer: dict[str, Any]) -> tuple[str, str]:
    state = str(answer.get("state") or "")
    if state != "answered":
        return state or "unknown", "needs_review"
    decision = str(answer.get("decision") or "")
    if decision in PASS_DECISIONS:
        return decision, "pass"
    if decision in CONTROL_DECISIONS:
        return decision, "needs_controls"
    if decision == "deny":
        return decision, "fail"
    return decision or "unknown", "needs_review"


def _validation_findings(answer: dict[str, Any]) -> list[dict[str, Any]]:
    findings = answer.get("findings")
    return [f for f in findings if isinstance(f, dict)] if isinstance(findings, list) else []


def _validation_reason_codes(answer: dict[str, Any]) -> list[str]:
    codes: list[str] = []
    for finding in _validation_findings(answer):
        if finding.get("status") == "not_enough_published_state":
            _append(codes, "NO_PUBLISHED_STATE")
            continue
        for instruction in finding.get("instructions") or []:
            decision = instruction.get("decision")
            scenario = str(instruction.get("scenario_key") or "")
            if decision == "deny":
                _append(codes, DENY_SCENARIO_CODES.get(scenario, "USE_DENIED"))
            elif decision in {"mask_full", "mask_partial"}:
                _append(codes, "MASKING_REQUIRED")
    if not codes and str(answer.get("verdict")) == "pass":
        codes.append("NO_RESTRICTED_USE_DETECTED")
    return codes


def _validation_controls(answer: dict[str, Any]) -> list[str]:
    controls: list[str] = []
    for finding in _validation_findings(answer):
        for instruction in finding.get("instructions") or []:
            if instruction.get("decision") in {"mask_full", "mask_partial"}:
                scope = instruction.get("scope") or {}
                column = scope.get("column") or "the flagged columns"
                _append(controls, f"Mask or drop {column} before shipping this query.")
    return controls


def _validation_rationale(answer: dict[str, Any]) -> str:
    worst = ""
    for finding in _validation_findings(answer):
        for instruction in finding.get("instructions") or []:
            reason = str(instruction.get("decision_reason") or "")
            if instruction.get("decision") == "deny":
                return reason
            if not worst and instruction.get("decision") in {"mask_full", "mask_partial"}:
                worst = reason
    return worst


def _authorization_reason_codes(answer: dict[str, Any]) -> list[str]:
    codes: list[str] = []
    decision = str(answer.get("decision") or "")
    scenario = str(answer.get("scenario_key") or "")
    if decision == "deny":
        _append(codes, DENY_SCENARIO_CODES.get(scenario, "USE_DENIED"))
    if decision == "conditional" and scenario == "residency.cross_border_transfer":
        _append(codes, "TRANSFER_CONDITIONAL")
    for condition in answer.get("conditions") or []:
        code = CONDITION_CODES.get(str(condition.get("kind") or ""))
        if code:
            _append(codes, code)
    if any(o.get("type") == "mask" for o in answer.get("obligations") or []):
        _append(codes, "MASKING_REQUIRED")
    if not codes and decision in PASS_DECISIONS:
        codes.append("PERMITTED_USE")
    return codes


def _authorization_controls(answer: dict[str, Any]) -> list[str]:
    controls: list[str] = []
    for condition in answer.get("conditions") or []:
        requirement = str(condition.get("requirement") or "").strip()
        if requirement:
            _append(controls, requirement)
    for obligation in answer.get("obligations") or []:
        if obligation.get("type") == "mask":
            method = f" ({obligation['method']})" if obligation.get("method") else ""
            _append(controls, f"Mask {obligation.get('target')}{method}.")
    return controls


def _action(gate: str, answer: dict[str, Any]) -> str:
    next_actions = answer.get("next_actions")
    if isinstance(next_actions, list) and next_actions:
        return str(next_actions[0])
    if gate == "pass":
        return "Proceed and record the Metatate evidence ID with the workflow."
    if gate == "needs_controls":
        return "Satisfy the stated conditions/obligations, then re-run the gate."
    if gate == "fail":
        return "Block the change; published policy prohibits this use."
    return "Route to governance review — the published state cannot answer this."


def _publication_id(answer: dict[str, Any]) -> str | None:
    publication = answer.get("publication")
    if isinstance(publication, dict):
        value = publication.get("publication_id")
        return str(value) if value else None
    return None


def _append(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


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
