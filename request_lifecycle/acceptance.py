#!/usr/bin/env python3
"""Non-writing acceptance for the request lifecycle orchestration."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common.metatate_client import _explain_arguments  # noqa: E402
from request_lifecycle.workflow import (  # noqa: E402
    AUTHORIZATION_ARGUMENTS,
    preview,
    retry_with_active_exception,
    submit,
)

AUTH_ID = "a1000000-0000-4000-8000-000000000001"
REQUEST_ID = "a1000000-0000-4000-8000-000000000002"
EXCEPTION_ID = "a1000000-0000-4000-8000-000000000003"


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def authorize_use(self, **arguments: Any) -> dict[str, Any]:
        self.calls.append(("authorize_use", arguments))
        return {"state": "answered", "authorization_id": AUTH_ID, "decision": "conditional"}

    def request_access(self, authorization_id: str) -> dict[str, Any]:
        self.calls.append(("request_access", {"authorization_id": authorization_id}))
        return {"state": "submitted", "request_id": REQUEST_ID, "request_status": "open"}

    def check_request(self, request_id: str) -> dict[str, Any]:
        self.calls.append(("check_request", {"request_id": request_id}))
        return {
            "request_id": request_id,
            "status": "resolved",
            "resolution_kind": "exception_granted",
            "exception": {"exception_id": EXCEPTION_ID, "state": "active"},
        }


def _answers(*values: str):
    remaining = iter(values)
    return lambda _prompt: next(remaining)


def main() -> int:
    assert preview()["mode"] == "preview"
    assert preview()["required_token_scopes"] == ["read", "request"]

    client = FakeClient()
    assert submit(client, "acme", input_fn=_answers("no"), output=lambda _s: None) is None
    assert client.calls == [], "a rejected first confirmation must make zero MCP calls"

    client = FakeClient()
    assert submit(
        client,
        "acme",
        input_fn=_answers("START", "not the bound confirmation"),
        output=lambda _s: None,
    ) is None
    assert [name for name, _ in client.calls] == ["authorize_use"]

    client = FakeClient()
    submitted = submit(
        client,
        "acme",
        input_fn=_answers("START", f"REQUEST {AUTH_ID}"),
        output=lambda _s: None,
    )
    assert submitted and submitted["request_id"] == REQUEST_ID
    assert client.calls[0] == ("authorize_use", AUTHORIZATION_ARGUMENTS)
    assert client.calls[1] == ("request_access", {"authorization_id": AUTH_ID})

    retried = retry_with_active_exception(client, REQUEST_ID)
    assert retried["authorization_id"] == AUTH_ID
    retry_arguments = client.calls[-1][1]
    assert retry_arguments["satisfied_conditions"] == [
        {"kind": "approval", "exception_id": EXCEPTION_ID}
    ]

    assert _explain_arguments("decision") == {"kind": "decision", "decision_id": "decision"}
    assert _explain_arguments(authorization_id="authorization") == {
        "kind": "authorization", "authorization_id": "authorization"
    }
    assert _explain_arguments(validation_id="validation") == {
        "kind": "validation", "validation_id": "validation"
    }
    for arguments in ({}, {"decision_id": "d", "validation_id": "v"}):
        try:
            _explain_arguments(**arguments)
        except ValueError:
            pass
        else:
            raise AssertionError("explain_why must require exactly one reference")

    print("request lifecycle acceptance passed (no live request created)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
