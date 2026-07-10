"""Small Metatate client helpers used by the notebooks.

Offline mode reads committed fixture responses. Live mode calls the Snowflake-
managed Metatate MCP server.
"""

from __future__ import annotations

import json
import os
import time
from copy import deepcopy
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dotenv is a notebook convenience.
    load_dotenv = None


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPO_ROOT / "sample-data" / "acmecloud" / "metatate-responses"


class OfflineMetatateClient:
    """Deterministic fixture-backed client for public notebooks."""

    def __init__(self, fixture_dir: Path | str = FIXTURE_DIR) -> None:
        self.fixture_dir = Path(fixture_dir)

    def _load(self, name: str) -> dict[str, Any]:
        with (self.fixture_dir / f"{name}.json").open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def discover_context(self, **params: Any) -> dict[str, Any]:
        response = self._load("discover_context")
        tables = response["data"]["tables"]
        database = _upper_or_none(params.get("database"))
        schema = _upper_or_none(params.get("schema"))
        domain = params.get("domain")
        has_pii = params.get("has_pii")
        compliance_any = set(params.get("compliance_any") or [])
        min_sensitivity = params.get("min_sensitivity")

        filtered = []
        for table in tables:
            if database and table.get("database_name") != database:
                continue
            if schema and table.get("schema_name") != schema:
                continue
            if domain and table.get("domain") != domain:
                continue
            if has_pii is not None and bool(table.get("has_pii")) is not bool(has_pii):
                continue
            if compliance_any and not compliance_any.intersection(table.get("compliance_frameworks") or []):
                continue
            if min_sensitivity and not _meets_sensitivity(table.get("sensitivity"), min_sensitivity):
                continue
            filtered.append(table)

        result = deepcopy(response)
        result["data"]["tables"] = filtered
        result["data"]["total"] = len(filtered)
        return result

    def get_decision_context(self, table_name: str) -> dict[str, Any]:
        if _normalize_table(table_name) == "ACMECLOUD_DEMO.PUBLIC.CUSTOMERS":
            return self._load("get_decision_context_customers")
        return _unknown_table_response(table_name)

    def inspect_data_meaning(self, table_name: str, columns: list[str] | None = None) -> dict[str, Any]:
        if _normalize_table(table_name) != "ACMECLOUD_DEMO.PUBLIC.CUSTOMERS":
            return _unknown_table_response(table_name)
        response = self._load("inspect_data_meaning_customers")
        if not columns:
            return response
        wanted = {_upper_or_none(column) for column in columns}
        result = deepcopy(response)
        result["data"]["columns"] = [
            column for column in response["data"]["columns"] if column["column_name"] in wanted
        ]
        return result

    def inspect_governance_rules(self, table_name: str, columns: list[str] | None = None) -> dict[str, Any]:
        if _normalize_table(table_name) == "ACMECLOUD_DEMO.PUBLIC.CUSTOMERS":
            return self._load("inspect_governance_rules_customers")
        return _unknown_table_response(table_name)

    def authorize_use(
        self,
        table_name: str,
        operation: str,
        intended_use: str,
        **params: Any,
    ) -> dict[str, Any]:
        table = _normalize_table(table_name)
        op = operation.lower()
        use = intended_use.lower()
        destination = params.get("destination") or {}
        destination_system = str(destination.get("system") or "").upper()

        if table == "ACMECLOUD_DEMO.PUBLIC.SUPPORT_TICKETS" and op == "train":
            return self._load("authorize_train_support_tickets_deny")
        if op == "export" and destination_system == "SALESFORCE":
            return self._load("authorize_export_salesforce_conditional")
        if op == "export" and destination_system in {"ADS_PLATFORM", "EXTERNAL_LLM_VENDOR"}:
            return self._load("authorize_export_ads_platform_deny")
        if use in {"marketing", "advertising", "personalization"}:
            return self._load("authorize_use_marketing_deny")
        if use in {"analytics", "reporting"}:
            return self._load("authorize_use_analytics_conditional")
        return {
            "request_id": "offline-authorize-unknown",
            "snapshot_id": "offline-acmecloud-v1",
            "status": "ok",
            "data": {
                "decision": "UNKNOWN",
                "table_name": table_name,
                "operation": operation,
                "intended_use": intended_use,
                "rationale": "The offline fixture has no matching rule for this request.",
                "agent_action": {"type": "ask_for_more_context"},
            },
        }

    def validate_query_context(self, sql: str, **params: Any) -> dict[str, Any]:
        normalized_sql = sql.upper()
        intended_use = str(params.get("intended_use") or "").lower()
        operation = str(params.get("operation") or "").lower()

        if intended_use in {"marketing", "advertising", "personalization"}:
            return self._load("validate_query_context_marketing_deny")
        if intended_use in {"ml_training", "training", "train"} or operation == "train":
            return self._load("validate_query_context_training_deny")
        if "EMAIL" in normalized_sql or "CUSTOMER_NAME" in normalized_sql or "SELECT *" in normalized_sql:
            return self._load("validate_query_context_analytics")
        return self._load("validate_query_context_safe_analytics")

    def explain_why(
        self,
        decision_id: str | None = None,
        validation_id: str | None = None,
    ) -> dict[str, Any]:
        if decision_id == "offline-decision-transfer-001":
            return self._load("explain_why_salesforce_conditional")
        if validation_id == "offline-validation-query-001":
            return self._load("validate_query_context_analytics")
        return {
            "request_id": "offline-explain-not-found",
            "snapshot_id": "offline-acmecloud-v1",
            "status": "error",
            "data": {
                "decision_id": decision_id,
                "validation_id": validation_id,
                "message": "The offline fixture does not include that decision or validation id.",
            },
        }


class ManagedMCPMetatateClient:
    """Live client for the Snowflake-managed Metatate MCP server."""

    def __init__(self, endpoint: str | None = None) -> None:
        if load_dotenv:
            load_dotenv(REPO_ROOT / ".env")

        self.endpoint = endpoint or _mcp_endpoint_from_env()
        self.role = os.getenv("METATATE_MCP_ROLE") or os.getenv("SNOWFLAKE_ROLE")
        self.token_type = os.getenv("METATATE_MCP_TOKEN_TYPE", "PROGRAMMATIC_ACCESS_TOKEN")
        self.token_env = os.getenv("METATATE_MCP_PAT_ENV", "METATATE_EXAMPLES_PAT")
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
                    f"Live mode requires a Snowflake PAT in ${self.token_env}. "
                    "Set METATATE_MCP_PAT_ENV to use a different environment variable."
                )

            self._session = requests.Session()
            headers = {
                "Authorization": f"Bearer {token}",
                "X-Snowflake-Authorization-Token-Type": self.token_type,
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            }
            if self.role:
                headers["X-Snowflake-Role"] = self.role
            self._session.headers.update(headers)
        return self._session

    def discover_context(self, **params: Any) -> dict[str, Any]:
        compliance_any = params.get("compliance_any") or []
        if isinstance(compliance_any, str):
            compliance_framework = compliance_any
        else:
            compliance_framework = next(iter(compliance_any), None)

        return self._call_tool(
            "discover-context",
            _drop_none(
                {
                    "database_name": params.get("database_name") or params.get("database"),
                    "schema_name": params.get("schema_name") or params.get("schema"),
                    "min_sensitivity": params.get("min_sensitivity"),
                    "compliance_framework": params.get("compliance_framework") or compliance_framework,
                    "has_pii": params.get("has_pii"),
                    "domain": params.get("domain"),
                }
            ),
        )

    def get_decision_context(self, table_name: str) -> dict[str, Any]:
        return self._call_tool("get-decision-context", {"table_name": table_name})

    def inspect_data_meaning(self, table_name: str, columns: list[str] | None = None) -> dict[str, Any]:
        response = self._call_tool(
            "inspect-data-meaning",
            _column_scoped_arguments(table_name, columns),
        )
        return _normalize_data_meaning_response(_filter_columns(response, columns))

    def inspect_governance_rules(self, table_name: str, columns: list[str] | None = None) -> dict[str, Any]:
        return self._call_tool(
            "inspect-governance-rules",
            _column_scoped_arguments(table_name, columns),
        )

    def authorize_use(self, table_name: str, operation: str, intended_use: str, **params: Any) -> dict[str, Any]:
        destination = params.get("destination") or {}
        payload: dict[str, Any] = {
            "table_name": table_name,
            "operation": operation,
            "intended_use": intended_use,
            "actor_role": params.get("actor_role"),
            "columns_csv": _csv(params.get("columns")),
            "destination_system": params.get("destination_system") or destination.get("system"),
            "destination_jurisdiction": params.get("destination_jurisdiction") or destination.get("jurisdiction"),
            "consumer_jurisdiction": params.get("consumer_jurisdiction"),
            "context_json": _json_string(params.get("context")),
            "raw_request_text": params.get("raw_request_text"),
            "normalized_request_json": _json_string(params.get("normalized_request")),
            "normalization_meta_json": _json_string(params.get("normalization_meta")),
        }
        return self._call_tool("authorize-use", _drop_none(payload))

    def validate_query_context(self, sql: str, **params: Any) -> dict[str, Any]:
        payload = {
            "sql_text": sql,
            "operation": params.get("operation"),
            "intended_use": params.get("intended_use"),
            "actor_role": params.get("actor_role"),
            "destination_system": params.get("destination_system"),
            "destination_jurisdiction": params.get("destination_jurisdiction"),
            "consumer_jurisdiction": params.get("consumer_jurisdiction"),
        }
        return _normalize_validation_response(self._call_tool("validate-query-context", _drop_none(payload)))

    def explain_why(
        self,
        decision_id: str | None = None,
        validation_id: str | None = None,
    ) -> dict[str, Any]:
        return self._call_tool("explain-why", _drop_none({"decision_id": decision_id, "validation_id": validation_id}))

    def _call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self._ensure_initialized()
        response = self._request("tools/call", {"name": name, "arguments": arguments})
        return _extract_mcp_payload(response)

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        self._request(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {}, "resources": {}},
                "clientInfo": {"name": "metatate-examples", "version": "1.0.0"},
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
        backend = os.getenv("METATATE_MCP_BACKEND", "snowflake").strip().lower()
        if backend == "saas":
            from .saas_client import SaasMcpMetatateClient

            return SaasMcpMetatateClient()
        if backend != "snowflake":
            raise ValueError("METATATE_MCP_BACKEND must be snowflake or saas")
        return ManagedMCPMetatateClient()
    if mode != "offline":
        raise ValueError("METATATE_EXAMPLES_MODE must be offline or live")
    return OfflineMetatateClient()


def _mcp_endpoint_from_env() -> str:
    endpoint = os.getenv("METATATE_MCP_URL")
    if endpoint:
        return endpoint.rstrip("/")

    account_url = os.getenv("METATATE_MCP_ACCOUNT_URL") or os.getenv("SNOWFLAKE_ACCOUNT_URL")
    if not account_url:
        raise RuntimeError(
            "Live mode requires METATATE_MCP_URL, or METATATE_MCP_ACCOUNT_URL plus app/schema/server names."
        )

    app_name = os.getenv("METATATE_APP_NAME", "METATATE_APP")
    schema_name = os.getenv("METATATE_MCP_SCHEMA", "CORE")
    server_name = os.getenv("METATATE_MCP_SERVER_NAME", "METATATE_MCP")
    return (
        account_url.rstrip("/")
        + f"/api/v2/databases/{app_name}/schemas/{schema_name}/mcp-servers/{server_name}"
    )


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


def _extract_mcp_payload(response: dict[str, Any]) -> dict[str, Any]:
    result = response.get("result", {})
    content = result.get("content") or []
    text = next((item.get("text", "") for item in content if item.get("type") == "text"), "")
    if result.get("isError"):
        raise RuntimeError(text or json.dumps(response))
    if not text:
        raise RuntimeError(f"MCP tool response did not include text content: {json.dumps(response)}")
    return json.loads(text)


def _column_scoped_arguments(table_name: str, columns: list[str] | None) -> dict[str, Any]:
    payload = {"table_name": table_name}
    if columns and len(columns) == 1:
        payload["column_name"] = columns[0]
    return payload


def _filter_columns(response: dict[str, Any], columns: list[str] | None) -> dict[str, Any]:
    if not columns or len(columns) == 1:
        return response
    wanted = {_upper_or_none(column) for column in columns}
    result = deepcopy(response)
    result["data"]["columns"] = [
        column for column in response.get("data", {}).get("columns", []) if column.get("column_name") in wanted
    ]
    return result


def _normalize_data_meaning_response(response: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(response)
    for column in result.get("data", {}).get("columns", []):
        if "masking_type" not in column:
            masking = column.get("masking") or {}
            column["masking_type"] = masking.get("type")
    return result


def _normalize_validation_response(response: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(response)
    data = result.setdefault("data", {})

    decision = data.get("decision")
    if isinstance(decision, dict):
        if "decision" not in decision and data.get("overall_decision"):
            decision["decision"] = data["overall_decision"]
        if "rationale" not in decision and data.get("summary"):
            decision["rationale"] = data["summary"]
    elif data.get("overall_decision"):
        data["decision"] = {"decision": data["overall_decision"], "rationale": data.get("summary")}

    action = data.setdefault("agent_action", {})
    if "message" not in action:
        action["message"] = action.get("safe_next_step") or action.get("suggested_next_tool") or "Review the validation result before proceeding."
    if "type" not in action:
        if data.get("overall_decision") == "DENY":
            action["type"] = "block"
        elif action.get("rewrite_required"):
            action["type"] = "revise_query"
        elif data.get("overall_decision") == "ALLOW":
            action["type"] = "proceed"
        else:
            action["type"] = "review_controls"
    if "validation_id" not in data and action.get("validation_id"):
        data["validation_id"] = action["validation_id"]

    return result


def _drop_none(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


def _csv(value: Any) -> str | None:
    if not value:
        return None
    if isinstance(value, str):
        return value
    return ",".join(str(item) for item in value)


def _json_string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value)


def _normalize_table(table_name: str) -> str:
    return table_name.strip().upper()


def _upper_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).strip().upper()


def _meets_sensitivity(actual: str | None, minimum: str) -> bool:
    order = {
        "public": 0,
        "internal": 1,
        "medium": 1,
        "confidential": 2,
        "high": 2,
        "restricted": 3,
        "critical": 3,
    }
    return order.get(str(actual or "").lower(), 0) >= order.get(str(minimum).lower(), 0)


def _unknown_table_response(table_name: str) -> dict[str, Any]:
    return {
        "request_id": "offline-table-not-found",
        "snapshot_id": "offline-acmecloud-v1",
        "status": "error",
        "data": {
            "table_name": table_name,
            "message": "The offline fixture only includes detailed responses for ACMECLOUD_DEMO.PUBLIC.CUSTOMERS.",
        },
    }
