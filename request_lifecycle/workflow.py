"""Safe client-side orchestration for the server-backed B1 request lane.

The default pack never calls request_access. This module makes the workflow
available without weakening that boundary: preview is non-writing, submit is
two-stage confirmed, and the caller must bring a live {read, request} token.
"""

from __future__ import annotations

from typing import Any, Callable

ASSET = {"database": "acmecloud_demo", "schema": "public", "table": "customers"}
AUTHORIZATION_ARGUMENTS: dict[str, Any] = {
    "asset": ASSET,
    "use": "sync approved customer fields to the CRM",
    "scenario_key": "residency.cross_border_transfer",
    "operation": "export",
    "destination": {"system": "SALESFORCE", "jurisdiction": "US"},
    "consumer_jurisdiction": "EU",
}

Input = Callable[[str], str]
Output = Callable[[str], None]


def preview() -> dict[str, Any]:
    """Return the non-writing walkthrough plan with no endpoint call."""
    return {
        "mode": "preview",
        "required_token_scopes": ["read", "request"],
        "authorize_use": dict(AUTHORIZATION_ARGUMENTS),
        "request_access": {
            "source": {"kind": "authorization", "id": "<authorization_id>"}
        },
        "warning": (
            "Live submission writes a real steward request and may notify configured "
            "stewards. Complete it in Activity > Review requests."
        ),
    }


def submit(
    client: Any,
    tenant_slug: str,
    *,
    input_fn: Input = input,
    output: Output = print,
) -> dict[str, Any] | None:
    """Create one request only after two explicit, value-bound confirmations."""
    output("This live walkthrough writes durable decision evidence and may file a real request.")
    output("The request may trigger steward notifications configured for this workspace.")
    if input_fn("Type START to run the cited authorization: ").strip() != "START":
        output("Aborted before any MCP call.")
        return None

    authorization = client.authorize_use(**AUTHORIZATION_ARGUMENTS)
    authorization_id = authorization.get("authorization_id")
    if not isinstance(authorization_id, str) or not authorization_id:
        raise RuntimeError("authorize_use returned no authorization_id")

    output(
        "Pending request_access: "
        f"source={{kind: authorization, id: {authorization_id}}}"
    )
    expected = f"REQUEST {authorization_id}"
    if input_fn(f"Type {expected} to file the steward request: ").strip() != expected:
        output("Request not filed; the authorization evidence remains recorded.")
        return None

    submitted = client.request_access(authorization_id)
    request_id = submitted.get("request_id")
    if isinstance(request_id, str) and request_id:
        output(f"Request: /{tenant_slug}/activity/review-requests/{request_id}")
    return submitted


def status(client: Any, request_id: str) -> dict[str, Any]:
    """Read the subject-verified, read-time request status."""
    return client.check_request(request_id)


def retry_with_active_exception(client: Any, request_id: str) -> dict[str, Any]:
    """Retry the canonical authorization only with a live server grant."""
    request = status(client, request_id)
    exception = request.get("exception")
    if not isinstance(exception, dict) or exception.get("state") != "active":
        raise RuntimeError("request has no active exception to retry")
    exception_id = exception.get("exception_id")
    if not isinstance(exception_id, str) or not exception_id:
        raise RuntimeError("active exception has no exception_id")
    return client.authorize_use(
        **AUTHORIZATION_ARGUMENTS,
        satisfied_conditions=[{"kind": "approval", "exception_id": exception_id}],
    )
