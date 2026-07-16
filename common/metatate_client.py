"""Metatate client helpers used by the notebooks — native typed-answer contract.

Offline mode replays RECORDED Metatate Cloud answers (committed under
`sample-data/acmecloud/metatate-responses/`, captured by
`scripts/record_offline_fixtures.py` from a live workspace) — the payloads a
reader studies offline are byte-shaped like the live endpoint's. Live mode
calls your Metatate Cloud workspace's MCP endpoint (see docs/live-mode-saas.md).

Both clients expose the same seven methods with the same native arguments
(structured `asset`/`ref` dicts, canonical `scenario_key`, destination-aware
transfer context) and return the tool's typed answer verbatim:
`state: answered | review_required | not_enough_published_state`, lowercase
decision vocabulary (`allow / deny / conditional / mask_partial / …`),
`verdict: pass | warn | fail`, structured `conditions` / `obligations` /
`prohibitions`, cited `instructions`, and `publication` provenance.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dotenv is a notebook convenience.
    load_dotenv = None

from .fixture_cases import CASES, case_for

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPO_ROOT / "sample-data" / "acmecloud" / "metatate-responses"


class MetatateToolError(RuntimeError):
    """A typed MCP tool error (`unauthorized`, `asset_not_found`, …)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class OfflineMetatateClient:
    """Replays the recorded typed answers for the canonical case set.

    Calls must match a case in `common/fixture_cases.py` (the notebooks do);
    anything else raises a `MetatateToolError` naming the recorded cases, so an
    offline reader is never shown an invented governance answer.
    """

    def __init__(self, fixture_dir: Path | str = FIXTURE_DIR) -> None:
        self.fixture_dir = Path(fixture_dir)
        self._decision_explains: dict[str, str] | None = None

    # ---- the seven tools ---------------------------------------------------

    def discover_context(self, **arguments: Any) -> dict[str, Any]:
        return self._dispatch("discover_context", _drop_none(arguments))

    def get_decision_context(
        self, asset: dict[str, str], scenario_key: str | None = None
    ) -> dict[str, Any]:
        return self._dispatch(
            "get_decision_context",
            _drop_none({"asset": asset, "scenario_key": scenario_key}),
        )

    def inspect_data_meaning(self, ref: dict[str, str]) -> dict[str, Any]:
        return self._dispatch("inspect_data_meaning", {"ref": ref})

    def inspect_governance_rules(
        self, asset: dict[str, str], scenario_key: str | None = None
    ) -> dict[str, Any]:
        return self._dispatch(
            "inspect_governance_rules",
            _drop_none({"asset": asset, "scenario_key": scenario_key}),
        )

    def authorize_use(
        self,
        asset: dict[str, str],
        use: str,
        scenario_key: str | None = None,
        operation: str | None = None,
        destination: dict[str, str] | None = None,
        consumer_jurisdiction: str | None = None,
    ) -> dict[str, Any]:
        return self._dispatch(
            "authorize_use",
            _drop_none(
                {
                    "asset": asset,
                    "use": use,
                    "scenario_key": scenario_key,
                    "operation": operation,
                    "destination": destination,
                    "consumer_jurisdiction": consumer_jurisdiction,
                }
            ),
        )

    def validate_query_context(
        self,
        sql: str,
        scenario_key: str | None = None,
        use: str | None = None,
        default_database: str | None = None,
        default_schema: str | None = None,
        operation: str | None = None,
        destination: dict[str, str] | None = None,
        consumer_jurisdiction: str | None = None,
    ) -> dict[str, Any]:
        return self._dispatch(
            "validate_query_context",
            _drop_none(
                {
                    "sql": sql,
                    "scenario_key": scenario_key,
                    "use": use,
                    "default_database": default_database,
                    "default_schema": default_schema,
                    "operation": operation,
                    "destination": destination,
                    "consumer_jurisdiction": consumer_jurisdiction,
                }
            ),
        )

    def explain_why(self, decision_id: str) -> dict[str, Any]:
        explains = self._decision_explain_index()
        case_id = explains.get(str(decision_id))
        if case_id is None:
            raise MetatateToolError(
                "offline_fixture_missing",
                "The offline recordings only explain decision_ids returned by the "
                "recorded authorize answers (chain from one of those).",
            )
        return self._load(case_id)

    # ---- routing -----------------------------------------------------------

    def _dispatch(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        case = case_for(tool, arguments)
        if case is None:
            nearest = ", ".join(c["id"] for c in CASES if c["tool"] == tool)
            raise MetatateToolError(
                "offline_fixture_missing",
                f"No recorded offline answer for this exact {tool} call. "
                f"Recorded cases: {nearest}. Run live mode for ad-hoc questions.",
            )
        return self._load(str(case["id"]))

    def _load(self, case_id: str) -> dict[str, Any]:
        path = self.fixture_dir / f"{case_id}.json"
        with path.open("r", encoding="utf-8") as handle:
            recording = json.load(handle)
        return recording["answer"]

    def _decision_explain_index(self) -> dict[str, str]:
        if self._decision_explains is None:
            index: dict[str, str] = {}
            for case in CASES:
                if case["tool"] != "explain_why":
                    continue
                reference = str(case["arguments"].get("decision_id") or "")
                if not reference.startswith("@"):
                    continue
                source_id = reference[1:].split(".", 1)[0]
                answer = self._load(source_id)
                decision_id = answer.get("decision_id")
                if isinstance(decision_id, str):
                    index[decision_id] = str(case["id"])
            self._decision_explains = index
        return self._decision_explains


class ManagedMCPMetatateClient:
    """MCP-over-HTTP transport: handshake, retries, SSE-or-JSON parsing, and
    typed tool errors. The concrete live client is
    :class:`common.saas_client.MetatateCloudClient`."""

    def __init__(self, endpoint: str | None = None) -> None:
        if load_dotenv:
            load_dotenv(REPO_ROOT / ".env")

        self.endpoint = endpoint or _mcp_endpoint_from_env()
        self.token_env = os.getenv("METATATE_MCP_PAT_ENV", "METATATE_SAAS_MCP_TOKEN")
        self.timeout_seconds = int(os.getenv("METATATE_MCP_TIMEOUT_SECONDS", "120"))
        self.retry_attempts = max(1, int(os.getenv("METATATE_MCP_RETRY_ATTEMPTS", "4")))
        self.retry_backoff_seconds = float(os.getenv("METATATE_MCP_RETRY_BACKOFF_SECONDS", "1"))
        self._session = None
        self._initialized = False

    @property
    def session(self) -> Any:
        if self._session is None:
            try:
                import requests
            except ImportError as exc:  # pragma: no cover - live dependency.
                raise RuntimeError("Install requirements-live.txt to use live mode") from exc

            token = os.getenv(self.token_env)
            if not token:
                raise RuntimeError(
                    f"Live mode requires a Metatate MCP access token in ${self.token_env}. "
                    "Set METATATE_MCP_PAT_ENV to use a different environment variable."
                )

            self._session = requests.Session()
            self._session.headers.update(
                {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                }
            )
        return self._session

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call one canonical tool; return its typed answer (structuredContent)."""
        self._ensure_initialized()
        response = self._request("tools/call", {"name": name, "arguments": arguments})
        result = response.get("result", {})
        text = next(
            (item.get("text", "") for item in result.get("content") or [] if item.get("type") == "text"),
            "",
        )
        if result.get("isError"):
            code, message = _tool_error(text)
            raise MetatateToolError(code, message)
        structured = result.get("structuredContent")
        if isinstance(structured, dict):
            return structured
        if text:
            return json.loads(text)
        raise RuntimeError(f"MCP tool response had no content: {json.dumps(response)}")

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        self._request(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {}, "resources": {}},
                "clientInfo": {"name": "metatate-examples", "version": "2.0.0"},
            },
        )
        notification_response = self._post_json_with_retry(
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            "notifications/initialized",
        )
        if notification_response.status_code >= 400:
            raise RuntimeError(
                "MCP initialization notification failed with "
                f"HTTP {notification_response.status_code}: {notification_response.text}"
            )
        self._initialized = True

    def _request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": method,
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        response = self._post_json_with_retry(payload, method)
        if response.status_code >= 400:
            raise RuntimeError(f"MCP request failed with HTTP {response.status_code}: {response.text}")
        return _parse_sse_or_json(response.text)

    def _post_json_with_retry(self, payload: dict[str, Any], method: str) -> Any:
        retryable_statuses = {408, 425, 429, 500, 502, 503, 504}
        last_error: Exception | None = None

        for attempt in range(1, self.retry_attempts + 1):
            try:
                response = self.session.post(self.endpoint, json=payload, timeout=self.timeout_seconds)
            except Exception as exc:
                last_error = exc
                if attempt == self.retry_attempts:
                    break
                time.sleep(self._retry_delay(attempt))
                continue

            if response.status_code in retryable_statuses and attempt < self.retry_attempts:
                time.sleep(self._retry_delay(attempt))
                continue
            return response

        raise RuntimeError(
            f"MCP request {method} failed after {self.retry_attempts} attempts: {last_error}"
        ) from last_error

    def _retry_delay(self, attempt: int) -> float:
        return min(self.retry_backoff_seconds * (2 ** (attempt - 1)), 8.0)


def get_client() -> Any:
    if load_dotenv:
        load_dotenv(REPO_ROOT / ".env")
    mode = os.getenv("METATATE_EXAMPLES_MODE", "offline").strip().lower()
    if mode == "live":
        backend = os.getenv("METATATE_MCP_BACKEND", "saas").strip().lower()
        if backend != "saas":
            raise ValueError(
                "This repo's live mode targets Metatate Cloud (METATATE_MCP_BACKEND=saas). "
                "Snowflake Native App examples: "
                "https://github.com/metatateai/metatate-snowflake-examples"
            )
        from .saas_client import MetatateCloudClient

        return MetatateCloudClient()
    if mode != "offline":
        raise ValueError("METATATE_EXAMPLES_MODE must be offline or live")
    return OfflineMetatateClient()


def _mcp_endpoint_from_env() -> str:
    endpoint = os.getenv("METATATE_MCP_URL")
    if not endpoint:
        raise RuntimeError(
            "Live mode requires METATATE_MCP_URL — the full MCP endpoint from the "
            "workspace MCP module's Connect tab, e.g. https://<your-workspace-mcp-host>/mcp."
        )
    return endpoint.rstrip("/")


def _parse_sse_or_json(text: str) -> dict[str, Any]:
    for event in text.split("\n\n"):
        if not event.strip():
            continue
        lines = event.split("\n")
        if any("event: message" in line for line in lines):
            data_line = next((line for line in lines if line.startswith("data: ")), None)
            if data_line:
                return json.loads(data_line[6:].strip())
    return json.loads(text)


def _tool_error(text: str) -> tuple[str, str]:
    try:
        error = json.loads(text).get("error") or {}
        return str(error.get("code") or "error"), str(error.get("message") or text)
    except (ValueError, AttributeError):
        return "error", text


def _drop_none(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}
