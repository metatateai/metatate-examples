"""Shared Metatate decision scenarios for framework runtime acceptance.

The framework-specific scripts import this module, wrap the callables in their
own tool runtime, and then assert that Metatate decisions change the outcome.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from common import get_client


TABLE_NAME = "ACMECLOUD_DEMO.PUBLIC.CUSTOMERS"

UNSAFE_ANALYTICS_SQL = (
    "SELECT customer_id, email, arr "
    "FROM ACMECLOUD_DEMO.PUBLIC.CUSTOMERS "
    "WHERE region = 'EU'"
)

SAFE_ANALYTICS_SQL = (
    "SELECT region, account_status, SUM(arr) AS arr "
    "FROM ACMECLOUD_DEMO.PUBLIC.CUSTOMERS "
    "WHERE account_status = 'active' "
    "GROUP BY region, account_status"
)

MARKETING_SQL = (
    "SELECT customer_name, email "
    "FROM ACMECLOUD_DEMO.PUBLIC.CUSTOMERS "
    "WHERE account_status = 'active'"
)


class RecordingMetatateClient:
    """Wrap the examples client and record validation calls."""

    def __init__(self, client: Any | None = None) -> None:
        self.client = client or get_client()
        self.calls: list[dict[str, Any]] = []

    def validate_query_context(self, sql: str, **params: Any) -> dict[str, Any]:
        self.calls.append({"sql": sql, "params": deepcopy(params)})
        return self.client.validate_query_context(sql, **params)


def validate_sql_for_agent(
    client: RecordingMetatateClient,
    sql_text: str,
    intended_use: str = "analytics",
    operation: str = "read",
    actor_role: str = "DATA_ANALYST",
) -> dict[str, Any]:
    """Validate SQL through Metatate and return the agent-facing decision."""

    validation = client.validate_query_context(
        sql_text,
        operation=operation,
        intended_use=intended_use,
        actor_role=actor_role,
    )
    decision = _decision_label(validation)
    action = _agent_action(validation)

    status = "approved"
    final_sql: str | None = sql_text
    if decision == "DENY":
        status = "blocked"
        final_sql = None
    elif decision != "ALLOW":
        status = "revised"
        final_sql = SAFE_ANALYTICS_SQL

    return {
        "table_name": TABLE_NAME,
        "decision": decision,
        "status": status,
        "action_type": action.get("type"),
        "message": action.get("message"),
        "validation_id": validation.get("data", {}).get("validation_id"),
        "reason_codes": _reason_codes(validation),
        "original_sql": sql_text,
        "final_sql": final_sql,
    }


def retrieval_prompt_to_sql(prompt: str) -> tuple[str, str]:
    """Small deterministic planner used by retrieval framework tests."""

    normalized = prompt.lower()
    if "marketing" in normalized or "email campaign" in normalized:
        return MARKETING_SQL, "marketing"
    if "email" in normalized or "identify" in normalized:
        return UNSAFE_ANALYTICS_SQL, "analytics"
    return SAFE_ANALYTICS_SQL, "analytics"


def assert_guard_behavior(results: dict[str, dict[str, Any]], call_count: int) -> None:
    """Assert the core behavior every framework runtime must prove."""

    assert call_count >= 3, f"expected at least three Metatate calls, got {call_count}"

    safe = results["safe"]
    assert safe["decision"] == "ALLOW", safe
    assert safe["status"] == "approved", safe
    assert safe["final_sql"] == SAFE_ANALYTICS_SQL, safe

    unsafe = results["unsafe"]
    assert unsafe["decision"] in {"CONDITIONAL", "REVIEW", "WARN"}, unsafe
    assert unsafe["status"] == "revised", unsafe
    assert unsafe["final_sql"] == SAFE_ANALYTICS_SQL, unsafe
    assert "EMAIL" not in unsafe["final_sql"].upper(), unsafe

    blocked = results["blocked"]
    assert blocked["decision"] == "DENY", blocked
    assert blocked["status"] == "blocked", blocked
    assert blocked["final_sql"] is None, blocked


def _decision_label(response: dict[str, Any]) -> str:
    data = response.get("data", {})
    decision = data.get("decision")
    if isinstance(decision, dict):
        return str(decision.get("decision") or decision.get("overall_decision") or "UNKNOWN").upper()
    return str(decision or data.get("overall_decision") or "UNKNOWN").upper()


def _agent_action(response: dict[str, Any]) -> dict[str, Any]:
    action = response.get("data", {}).get("agent_action")
    if isinstance(action, dict):
        return action
    return {}


def _reason_codes(response: dict[str, Any]) -> list[str]:
    data = response.get("data", {})
    decision = data.get("decision")
    if isinstance(decision, dict):
        return list(decision.get("reason_codes") or [])
    return list(data.get("reason_codes") or [])
