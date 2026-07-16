#!/usr/bin/env python3
"""Human-in-the-loop exception workflow for Metatate examples.

The workflow is deterministic and local, but every policy decision comes from
Metatate. Offline mode uses fixtures. Live mode calls the Metatate Cloud
MCP server through the shared examples client.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from common import get_client


# Native typed-answer vocabulary: authorize decisions and validate verdicts.
ALLOW_DECISIONS = {"allow", "log_only", "retain", "pass"}
CONDITIONAL_DECISIONS = {"conditional", "mask_full", "mask_partial", "warn"}
DENY_DECISIONS = {"deny", "fail"}

SAFE_ANALYTICS_SQL = "SELECT region, SUM(arr) FROM customers GROUP BY region"

DEFAULT_REQUESTS: list[dict[str, Any]] = [
    {
        "request_id": "req-001",
        "kind": "query",
        "title": "Publish aggregate ARR dashboard",
        "description": "Release an aggregate analytics query for customer ARR by region.",
        "sql": SAFE_ANALYTICS_SQL,
        "scenario_key": "purpose.allowed_use",
        "default_database": "acmecloud_demo",
        "default_schema": "public",
        "owner": "Revenue Operations",
    },
    {
        "request_id": "req-002",
        "kind": "authorization",
        "title": "Export customer fields to Salesforce",
        "description": "Sync customer fields to Salesforce for account operations.",
        "asset": {"database": "acmecloud_demo", "schema": "public", "table": "customers"},
        "use": "sync approved customer fields to the CRM",
        "scenario_key": "residency.cross_border_transfer",
        "operation": "export",
        "destination": {"system": "SALESFORCE", "jurisdiction": "US"},
        "consumer_jurisdiction": "EU",
        "owner": "Revenue Operations",
        "reviewer_queue": "privacy-review",
        "required_attestations": ["approval_recorded", "anonymization_before_transfer"],
    },
    {
        "request_id": "req-003",
        "kind": "authorization",
        "title": "Fine-tune support assistant on raw tickets",
        "description": "Train a support assistant on raw ticket text.",
        "asset": {"database": "acmecloud_demo", "schema": "public", "table": "support_tickets"},
        "use": "fine-tune a support assistant on ticket text",
        "scenario_key": "ai.training",
        "owner": "Support Operations",
        "reviewer_queue": "ai-governance",
    },
]

DEFAULT_REVIEWS: dict[str, dict[str, Any]] = {
    "req-002": {
        "review_id": "review-req-002",
        "reviewer": "privacy-review@example.com",
        "decision": "approve",
        "comments": "Approved for Salesforce only after anonymization and evidence recording.",
        "controls_attested": ["approval_recorded", "anonymization_before_transfer"],
    }
}


@dataclass(frozen=True)
class ReviewDecision:
    review_id: str
    reviewer: str
    decision: str
    comments: str
    controls_attested: list[str]


@dataclass(frozen=True)
class ExceptionWorkflowItem:
    request_id: str
    title: str
    kind: str
    decision: str
    status: str
    evidence_id: str | None
    reviewer_queue: str | None
    packet: dict[str, Any]
    review: ReviewDecision | None
    resume_payload: dict[str, Any] | None


@dataclass(frozen=True)
class ExceptionWorkflowRun:
    total: int
    ready_without_exception: int
    pending_review: int
    resumed_with_controls: int
    requires_changes: int
    rejected_by_reviewer: int
    blocked_by_policy: int
    needs_policy_review: int
    items: list[ExceptionWorkflowItem]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["items"] = [
            {
                **asdict(item),
                "review": asdict(item.review) if item.review else None,
            }
            for item in self.items
        ]
        return payload


def run_workflow(
    client: Any | None = None,
    requests: list[dict[str, Any]] | None = None,
    reviews: dict[str, dict[str, Any]] | None = None,
) -> ExceptionWorkflowRun:
    client = client or get_client()
    if requests is None:
        requests = DEFAULT_REQUESTS
    if reviews is None:
        reviews = DEFAULT_REVIEWS

    items = []
    for request in requests:
        item = evaluate_request(client, request)
        review_payload = reviews.get(item.request_id)
        if review_payload:
            item = apply_review(item, ReviewDecision(**review_payload))
        items.append(item)

    return ExceptionWorkflowRun(
        total=len(items),
        ready_without_exception=sum(1 for item in items if item.status == "ready_without_exception"),
        pending_review=sum(1 for item in items if item.status == "pending_human_review"),
        resumed_with_controls=sum(1 for item in items if item.status == "resumed_with_controls"),
        requires_changes=sum(1 for item in items if item.status == "requires_changes"),
        rejected_by_reviewer=sum(1 for item in items if item.status == "rejected_by_reviewer"),
        blocked_by_policy=sum(1 for item in items if item.status == "blocked_by_policy"),
        needs_policy_review=sum(1 for item in items if item.status == "needs_policy_review"),
        items=items,
    )


def evaluate_request(client: Any, request: dict[str, Any]) -> ExceptionWorkflowItem:
    response = _call_metatate(client, request)
    decision = _decision_label(response)
    packet = build_exception_packet(request, response, decision)
    status = _initial_status(decision)

    return ExceptionWorkflowItem(
        request_id=str(request["request_id"]),
        title=str(request["title"]),
        kind=str(request["kind"]),
        decision=decision,
        status=status,
        evidence_id=packet.get("evidence_id"),
        reviewer_queue=packet.get("reviewer_queue"),
        packet=packet,
        review=None,
        resume_payload=None,
    )


def build_exception_packet(
    request: dict[str, Any],
    response: dict[str, Any],
    decision: str,
) -> dict[str, Any]:
    required_controls = _required_controls(response)
    required_attestations = list(request.get("required_attestations") or [])

    return {
        "packet_id": f"exception-{request['request_id']}",
        "request_id": request["request_id"],
        "title": request["title"],
        "description": request.get("description"),
        "owner": request.get("owner"),
        "decision": decision,
        "evidence_id": _evidence_id(response),
        "source": _first_table(response) or "SQL query",
        "destination": request.get("destination") or _destination(response),
        "consumer_jurisdiction": request.get("consumer_jurisdiction"),
        "required_controls": required_controls,
        "required_attestations": required_attestations,
        "obligations": _obligations(response),
        "rationale": _rationale(response),
        "reviewer_note": _reviewer_note(response, decision),
        "reviewer_queue": request.get("reviewer_queue") if decision in CONDITIONAL_DECISIONS else None,
        "policy_response_state": response.get("state"),
    }


def apply_review(item: ExceptionWorkflowItem, review: ReviewDecision) -> ExceptionWorkflowItem:
    if item.status != "pending_human_review":
        return ExceptionWorkflowItem(
            **{
                **asdict(item),
                "review": review,
                "resume_payload": None,
            }
        )

    normalized = review.decision.strip().lower()
    if normalized == "reject":
        return _replace_item(item, status="rejected_by_reviewer", review=review, resume_payload=None)

    if normalized != "approve":
        return _replace_item(item, status="requires_changes", review=review, resume_payload=None)

    missing = _missing_attestations(item.packet, review)
    if missing:
        payload = {"missing_attestations": missing, "message": "Reviewer approval is incomplete."}
        return _replace_item(item, status="requires_changes", review=review, resume_payload=payload)

    return _replace_item(
        item,
        status="resumed_with_controls",
        review=review,
        resume_payload=_resume_payload(item, review),
    )


def print_summary(run: ExceptionWorkflowRun) -> None:
    print("Human-in-the-loop exception workflow")
    print(f"  ready_without_exception: {run.ready_without_exception}")
    print(f"  resumed_with_controls: {run.resumed_with_controls}")
    print(f"  pending_review: {run.pending_review}")
    print(f"  requires_changes: {run.requires_changes}")
    print(f"  rejected_by_reviewer: {run.rejected_by_reviewer}")
    print(f"  blocked_by_policy: {run.blocked_by_policy}")
    print(f"  needs_policy_review: {run.needs_policy_review}")
    print("")

    for item in run.items:
        evidence = f" evidence={item.evidence_id}" if item.evidence_id else ""
        print(f"{item.request_id}: {item.status} ({item.decision}){evidence}")
        if item.packet.get("reviewer_queue"):
            print(f"  queue: {item.packet['reviewer_queue']}")
        if item.packet.get("rationale"):
            print(f"  rationale: {item.packet['rationale']}")
        if item.review:
            print(f"  reviewer: {item.review.reviewer} -> {item.review.decision}")
        if item.resume_payload:
            print(f"  resume: {item.resume_payload.get('action') or item.resume_payload.get('message')}")


def _call_metatate(client: Any, request: dict[str, Any]) -> dict[str, Any]:
    kind = request.get("kind")
    if kind == "query":
        return client.validate_query_context(
            request["sql"],
            scenario_key=request.get("scenario_key"),
            use=request.get("use"),
            default_database=request.get("default_database"),
            default_schema=request.get("default_schema"),
            operation=request.get("operation"),
            destination=request.get("destination"),
            consumer_jurisdiction=request.get("consumer_jurisdiction"),
        )
    if kind == "authorization":
        return client.authorize_use(
            request["asset"],
            use=str(request.get("use") or request.get("description") or ""),
            scenario_key=request.get("scenario_key"),
            operation=request.get("operation"),
            destination=request.get("destination"),
            consumer_jurisdiction=request.get("consumer_jurisdiction"),
        )
    raise ValueError(f"Unsupported request kind {kind!r}")


def _initial_status(decision: str) -> str:
    if decision in ALLOW_DECISIONS:
        return "ready_without_exception"
    if decision in CONDITIONAL_DECISIONS:
        return "pending_human_review"
    if decision in DENY_DECISIONS:
        return "blocked_by_policy"
    return "needs_policy_review"


def _replace_item(
    item: ExceptionWorkflowItem,
    *,
    status: str,
    review: ReviewDecision | None,
    resume_payload: dict[str, Any] | None,
) -> ExceptionWorkflowItem:
    return ExceptionWorkflowItem(
        request_id=item.request_id,
        title=item.title,
        kind=item.kind,
        decision=item.decision,
        status=status,
        evidence_id=item.evidence_id,
        reviewer_queue=item.reviewer_queue,
        packet=item.packet,
        review=review,
        resume_payload=resume_payload,
    )


def _resume_payload(item: ExceptionWorkflowItem, review: ReviewDecision) -> dict[str, Any]:
    return {
        "action": "resume_controlled_workflow",
        "request_id": item.request_id,
        "evidence_id": item.evidence_id,
        "review_id": review.review_id,
        "controls_attested": review.controls_attested,
        "destination": item.packet.get("destination"),
        "execution_note": "Resume only for the reviewed destination and with the attested controls applied.",
    }


def _missing_attestations(packet: dict[str, Any], review: ReviewDecision) -> list[str]:
    required = set(packet.get("required_attestations") or [])
    attested = set(review.controls_attested or [])
    return sorted(required.difference(attested))


def _decision_label(answer: dict[str, Any]) -> str:
    state = str(answer.get("state") or "")
    if state and state != "answered":
        # review_required / not_enough_published_state route to policy review.
        return state
    return str(answer.get("decision") or answer.get("verdict") or "unknown")


def _evidence_id(answer: dict[str, Any]) -> str | None:
    decision_id = answer.get("decision_id")
    if isinstance(decision_id, str):
        return decision_id
    publication = answer.get("publication")
    if isinstance(publication, dict) and isinstance(publication.get("publication_id"), str):
        return str(publication["publication_id"])
    return None


def _required_controls(answer: dict[str, Any]) -> list[str]:
    controls = []
    for condition in answer.get("conditions") or []:
        if isinstance(condition, dict):
            requirement = str(condition.get("requirement") or "").strip()
            controls.append(requirement or _stringify(condition))
        else:
            controls.append(_stringify(condition))
    return _unique(controls)


def _obligations(answer: dict[str, Any]) -> list[str]:
    rendered: list[str] = []
    for obligation in answer.get("obligations") or []:
        if isinstance(obligation, dict) and obligation.get("type") == "mask":
            method = f" ({obligation['method']})" if obligation.get("method") else ""
            rendered.append(f"Mask {obligation.get('target')}{method}.")
        else:
            rendered.append(_stringify(obligation))
    return _unique(rendered)


def _rationale(answer: dict[str, Any]) -> str:
    reason = str(answer.get("reason") or "")
    if reason:
        return reason
    for finding in answer.get("findings") or []:
        for instruction in finding.get("instructions") or []:
            if instruction.get("decision") in {"deny", "mask_full", "mask_partial"}:
                return str(instruction.get("decision_reason") or "")
    return ""


def _agent_action_message(answer: dict[str, Any]) -> str:
    next_actions = answer.get("next_actions")
    if isinstance(next_actions, list) and next_actions:
        return str(next_actions[0])
    return ""


def _reviewer_note(answer: dict[str, Any], decision: str) -> str:
    if decision in ALLOW_DECISIONS:
        return "No exception required. Proceed and record the Metatate evidence ID with the workflow."

    message = _agent_action_message(answer)
    if message and message != "explain_why":
        return message

    if decision in CONDITIONAL_DECISIONS:
        return "Human review is required before the workflow can resume."
    if decision in DENY_DECISIONS:
        return "Do not resume this workflow. Change the request or deployed policy before retrying."
    return "Route this request to the policy owner for review."


def _first_table(answer: dict[str, Any]) -> str | None:
    for finding in answer.get("findings") or []:
        ref = finding.get("ref")
        if isinstance(ref, dict):
            return ".".join(
                str(ref.get(part) or "") for part in ("database", "schema", "table")
            )
    asset = answer.get("asset")
    if isinstance(asset, dict):
        return ".".join(str(asset.get(part) or "") for part in ("database", "schema", "table"))
    return None


def _destination(answer: dict[str, Any]) -> dict[str, Any] | None:
    destination = answer.get("destination")
    if isinstance(destination, dict):
        return destination
    return None


def _unique(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        normalized = value.strip()
        if normalized and normalized not in seen:
            result.append(normalized)
            seen.add(normalized)
    return result


def _stringify(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return str(value)
