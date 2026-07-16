"""Shared Metatate decision scenarios for framework runtime acceptance.

The framework-specific scripts import this module, wrap the callables in their
own tool runtime, and then assert that Metatate decisions change the outcome.
Everything speaks the native typed-answer contract: canonical `scenario_key`s
in, `state`/`verdict` out.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from common import get_client


DATABASE = "acmecloud_demo"
SCHEMA = "public"
TABLE_NAME = f"{DATABASE}.{SCHEMA}.customers"

# The three recorded validation cases (sample-data/acmecloud/metatate-responses):
# a safe aggregate (pass), a PII detail read (warn — masked column referenced),
# and a prohibited marketing read (fail).
SAFE_ANALYTICS_SQL = "SELECT region, SUM(arr) FROM customers GROUP BY region"
UNSAFE_ANALYTICS_SQL = "SELECT customer_name, email FROM customers WHERE region = 'EU'"
MARKETING_SQL = "SELECT customer_name, email FROM customers WHERE marketing_consent = 'opted_in'"


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
    scenario_key: str = "purpose.allowed_use",
) -> dict[str, Any]:
    """Validate SQL through Metatate and return the agent-facing decision."""

    answer = client.validate_query_context(
        sql_text,
        scenario_key=scenario_key,
        default_database=DATABASE,
        default_schema=SCHEMA,
    )
    state = str(answer.get("state") or "")
    verdict = str(answer.get("verdict") or "") if state == "answered" else state

    status = "approved"
    final_sql: str | None = sql_text
    if verdict == "fail":
        status = "blocked"
        final_sql = None
    elif verdict != "pass":
        status = "revised"
        final_sql = SAFE_ANALYTICS_SQL

    return {
        "table_name": TABLE_NAME,
        "verdict": verdict,
        "status": status,
        "publication_id": _publication_id(answer),
        "flagged_reasons": _flagged_reasons(answer),
        "original_sql": sql_text,
        "final_sql": final_sql,
    }


def retrieval_prompt_to_sql(prompt: str) -> tuple[str, str]:
    """Small deterministic planner used by retrieval framework tests.

    Returns (sql, canonical scenario_key)."""

    normalized = prompt.lower()
    if "marketing" in normalized or "email campaign" in normalized:
        return MARKETING_SQL, "purpose.prohibited_use"
    if "email" in normalized or "identify" in normalized:
        return UNSAFE_ANALYTICS_SQL, "purpose.allowed_use"
    return SAFE_ANALYTICS_SQL, "purpose.allowed_use"


def assert_guard_behavior(results: dict[str, dict[str, Any]], call_count: int) -> None:
    """Assert the core behavior every framework runtime must prove."""

    assert call_count >= 3, f"expected at least three Metatate calls, got {call_count}"

    safe = results["safe"]
    assert safe["verdict"] == "pass", safe
    assert safe["status"] == "approved", safe
    assert safe["final_sql"] == SAFE_ANALYTICS_SQL, safe

    unsafe = results["unsafe"]
    assert unsafe["verdict"] == "warn", unsafe
    assert unsafe["status"] == "revised", unsafe
    assert unsafe["final_sql"] == SAFE_ANALYTICS_SQL, unsafe
    assert "email" not in unsafe["final_sql"].lower(), unsafe

    blocked = results["blocked"]
    assert blocked["verdict"] == "fail", blocked
    assert blocked["status"] == "blocked", blocked
    assert blocked["final_sql"] is None, blocked


def _publication_id(answer: dict[str, Any]) -> str | None:
    publication = answer.get("publication")
    if isinstance(publication, dict):
        value = publication.get("publication_id")
        return str(value) if value else None
    return None


def _flagged_reasons(answer: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    for finding in answer.get("findings") or []:
        for instruction in finding.get("instructions") or []:
            if instruction.get("decision") in {"deny", "mask_full", "mask_partial"}:
                reason = str(instruction.get("decision_reason") or "")
                if reason and reason not in reasons:
                    reasons.append(reason)
    return reasons
