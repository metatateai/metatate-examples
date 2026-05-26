"""Small Metatate client helpers used by the notebooks.

Offline mode reads committed fixture responses. Live mode calls the canonical
Metatate Native App SQL functions and procedures in Snowflake.
"""

from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dotenv is a notebook convenience.
    load_dotenv = None


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPO_ROOT / "sample-data" / "acmecloud" / "metatate-responses"
APP_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


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
        return self._load("validate_query_context_analytics")

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


class SnowflakeMetatateClient:
    """Live client for the Metatate Native App SQL tool layer."""

    def __init__(self, app_name: str | None = None) -> None:
        if load_dotenv:
            load_dotenv(REPO_ROOT / ".env")

        self.app_name = app_name or os.getenv("METATATE_APP_NAME", "METATATE_APP")
        if not APP_IDENTIFIER.match(self.app_name):
            raise ValueError("METATATE_APP_NAME must be a simple Snowflake identifier")
        self._connection = None

    @property
    def connection(self) -> Any:
        if self._connection is None:
            try:
                import snowflake.connector
            except ImportError as exc:  # pragma: no cover - live dependency.
                raise RuntimeError("Install requirements-live.txt to use live mode") from exc

            connection_name = os.getenv("SNOWFLAKE_CONNECTION_NAME")
            connections_file_path = os.getenv("SNOWFLAKE_CONNECTIONS_FILE")
            if connection_name:
                kwargs: dict[str, Any] = {"connection_name": connection_name}
                if connections_file_path:
                    kwargs["connections_file_path"] = connections_file_path
                if os.getenv("SNOWFLAKE_ROLE"):
                    kwargs["role"] = os.environ["SNOWFLAKE_ROLE"]
                if os.getenv("SNOWFLAKE_WAREHOUSE"):
                    kwargs["warehouse"] = os.environ["SNOWFLAKE_WAREHOUSE"]
                self._connection = snowflake.connector.connect(**kwargs)
            else:
                connect_kwargs: dict[str, Any] = {
                    "account": os.environ["SNOWFLAKE_ACCOUNT"],
                    "user": os.environ["SNOWFLAKE_USER"],
                    "role": os.getenv("SNOWFLAKE_ROLE"),
                    "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
                    "authenticator": os.getenv("SNOWFLAKE_AUTHENTICATOR", "externalbrowser"),
                }
                password = os.getenv("SNOWFLAKE_PASSWORD")
                token_env = os.getenv("SNOWFLAKE_PAT_ENV")
                if token_env:
                    password = os.environ[token_env]
                    connect_kwargs["authenticator"] = "programmatic_access_token"
                if password:
                    connect_kwargs["password"] = password
                self._connection = snowflake.connector.connect(**connect_kwargs)
        return self._connection

    def discover_context(self, **params: Any) -> dict[str, Any]:
        return self._select_variant("DISCOVER_CONTEXT", params)

    def get_decision_context(self, table_name: str) -> dict[str, Any]:
        return self._select_variant("GET_DECISION_CONTEXT", {"table_name": table_name})

    def inspect_data_meaning(self, table_name: str, columns: list[str] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"table_name": table_name}
        if columns:
            payload["columns"] = columns
        return self._select_variant("INSPECT_DATA_MEANING", payload)

    def inspect_governance_rules(self, table_name: str, columns: list[str] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"table_name": table_name}
        if columns:
            payload["columns"] = columns
        return self._select_variant("INSPECT_GOVERNANCE_RULES", payload)

    def authorize_use(self, table_name: str, operation: str, intended_use: str, **params: Any) -> dict[str, Any]:
        payload = {"table_name": table_name, "operation": operation, "intended_use": intended_use, **params}
        return self._call_variant("AUTHORIZE_USE", payload)

    def validate_query_context(self, sql: str, **params: Any) -> dict[str, Any]:
        payload = {"sql": sql, **params}
        return self._call_variant("VALIDATE_QUERY_CONTEXT", payload)

    def explain_why(
        self,
        decision_id: str | None = None,
        validation_id: str | None = None,
    ) -> dict[str, Any]:
        payload = {"decision_id": decision_id, "validation_id": validation_id}
        return self._call_variant("EXPLAIN_WHY", {k: v for k, v in payload.items() if v})

    def _select_variant(self, object_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        sql = f"SELECT {self.app_name}.CORE.{object_name}(PARSE_JSON(%s))"
        return self._execute_json(sql, payload)

    def _call_variant(self, object_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        sql = f"CALL {self.app_name}.CORE.{object_name}(PARSE_JSON(%s))"
        return self._execute_json(sql, payload)

    def _execute_json(self, sql: str, payload: dict[str, Any]) -> dict[str, Any]:
        cursor = self.connection.cursor()
        try:
            cursor.execute(sql, (json.dumps(payload),))
            row = cursor.fetchone()
            if not row:
                raise RuntimeError("Snowflake returned no rows")
            return _coerce_json(row[0])
        finally:
            cursor.close()


def get_client() -> OfflineMetatateClient | SnowflakeMetatateClient:
    if load_dotenv:
        load_dotenv(REPO_ROOT / ".env")
    mode = os.getenv("METATATE_EXAMPLES_MODE", "offline").strip().lower()
    if mode == "live":
        return SnowflakeMetatateClient()
    if mode != "offline":
        raise ValueError("METATATE_EXAMPLES_MODE must be offline or live")
    return OfflineMetatateClient()


def _coerce_json(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return json.loads(value)
    if hasattr(value, "as_dict"):
        return value.as_dict()
    raise TypeError(f"Cannot coerce Snowflake value to JSON: {type(value)!r}")


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
