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


ALLOW_DECISIONS = {"ALLOW", "APPROVE", "APPROVED"}
CONDITIONAL_DECISIONS = {"CONDITIONAL", "REVIEW", "WARN", "WARNING"}
DENY_DECISIONS = {"DENY", "BLOCK", "BLOCKED", "REJECT"}

SAFE_ANALYTICS_SQL = (
    "SELECT region, account_status, SUM(arr) AS arr "
    "FROM ACMECLOUD_DEMO.PUBLIC.CUSTOMERS "
    "WHERE account_status = 'active' "
    "GROUP BY region, account_status"
)

DEFAULT_REQUESTS: list[dict[str, Any]] = [
    {
        "request_id": "req-001",
        "kind": "query",
        "title": "Publish aggregate ARR dashboard",
        "description": "Release an aggregate analytics query for active customer ARR.",
        "sql": SAFE_ANALYTICS_SQL,
        "operation": "read",
        "intended_use": "analytics",
        "actor_role": "DATA_ANALYST",
        "owner": "Revenue Operations",
    },
    {
        "request_id": "req-002",
        "kind": "authorization",
        "title": "Export customer fields to Salesforce",
        "description": "Sync customer fields to Salesforce for account operations.",
        "table_name": "ACMECLOUD_DEMO.PUBLIC.CUSTOMERS",
        "operation": "export",
        "intended_use": "external_sharing",
        "actor_role": "DATA_ENGINEER",
        "columns": ["CUSTOMER_ID", "CUSTOMER_NAME", "EMAIL", "ACCOUNT_STATUS"],
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
        "description": "Train a support assistant on raw ticket text and linked customer identifiers.",
        "table_name": "ACMECLOUD_DEMO.PUBLIC.SUPPORT_TICKETS",
        "operation": "train",
        "intended_use": "ml_training",
        "actor_role": "ML_ENGINEER",
        "columns": ["TICKET_TEXT", "PRIORITY", "CUSTOMER_ID"],
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
    data = response.get("data", {})
    required_controls = _required_controls(data)
    required_attestations = list(request.get("required_attestations") or [])

    return {
        "packet_id": f"exception-{request['request_id']}",
        "request_id": request["request_id"],
        "title": request["title"],
        "description": request.get("description"),
        "owner": request.get("owner"),
        "decision": decision,
        "evidence_id": _evidence_id(response),
        "source": request.get("table_name") or _first_table(data) or "SQL query",
        "destination": request.get("destination") or _destination(data),
        "consumer_jurisdiction": request.get("consumer_jurisdiction") or data.get("consumer_jurisdiction"),
        "required_controls": required_controls,
        "required_attestations": required_attestations,
        "obligations": _obligations(data),
        "rationale": _rationale(data),
        "reviewer_note": _reviewer_note(data, decision),
        "reviewer_queue": request.get("reviewer_queue") if decision in CONDITIONAL_DECISIONS else None,
        "policy_response_status": response.get("status"),
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
            operation=request.get("operation") or "read",
            intended_use=request.get("intended_use") or "analytics",
            actor_role=request.get("actor_role"),
        )
    if kind == "authorization":
        return client.authorize_use(
            request["table_name"],
            operation=request.get("operation") or "read",
            intended_use=request.get("intended_use") or "analytics",
            actor_role=request.get("actor_role"),
            columns=request.get("columns"),
            destination=request.get("destination"),
            consumer_jurisdiction=request.get("consumer_jurisdiction"),
            raw_request_text=request.get("description"),
            context={"request_id": request.get("request_id"), "owner": request.get("owner")},
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


def _decision_label(response: dict[str, Any]) -> str:
    data = response.get("data", {})
    decision = data.get("decision")
    if isinstance(decision, dict):
        return str(decision.get("decision") or decision.get("overall_decision") or "UNKNOWN").upper()
    return str(decision or data.get("overall_decision") or "UNKNOWN").upper()


def _evidence_id(response: dict[str, Any]) -> str | None:
    data = response.get("data", {})
    return data.get("decision_id") or data.get("validation_id") or response.get("request_id")


def _required_controls(data: dict[str, Any]) -> list[str]:
    controls = []
    for key in ("conditions", "required_controls"):
        values = data.get(key) or []
        if isinstance(values, str):
            controls.append(values)
        else:
            controls.extend(_stringify(value) for value in values)
    return _unique(controls)


def _obligations(data: dict[str, Any]) -> list[str]:
    values = data.get("obligations") or []
    if isinstance(values, str):
        return [values]
    return _unique([_stringify(value) for value in values])


def _rationale(data: dict[str, Any]) -> str:
    decision = data.get("decision")
    if isinstance(decision, dict):
        return str(decision.get("rationale") or data.get("summary") or "")
    return str(data.get("rationale") or data.get("summary") or "")


def _agent_action_message(data: dict[str, Any]) -> str:
    action = data.get("agent_action")
    if isinstance(action, dict):
        return str(action.get("message") or action.get("safe_next_step") or action.get("suggested_next_tool") or "")
    return ""


def _reviewer_note(data: dict[str, Any], decision: str) -> str:
    if decision in ALLOW_DECISIONS:
        return "No exception required. Proceed and record the Metatate evidence ID with the workflow."

    message = _agent_action_message(data)
    if message and message != "explain_why":
        return message

    if decision in CONDITIONAL_DECISIONS:
        return "Human review is required before the workflow can resume."
    if decision in DENY_DECISIONS:
        return "Do not resume this workflow. Change the request or deployed policy before retrying."
    return "Route this request to the policy owner for review."


def _first_table(data: dict[str, Any]) -> str | None:
    tables = data.get("tables_accessed") or []
    if tables:
        return str(tables[0])
    return data.get("table_name")


def _destination(data: dict[str, Any]) -> dict[str, Any] | None:
    destination = data.get("destination")
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
