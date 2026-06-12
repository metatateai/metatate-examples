#!/usr/bin/env python3
"""Live Cortex Agent runtime acceptance for Metatate examples.

This script intentionally has no offline fallback. It creates a Snowflake
Cortex Agent with a generic custom tool backed by a Snowflake stored procedure.
That procedure calls the Metatate Native App Snowflake Intelligence wrapper.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

try:
    import requests
except ImportError as exc:  # pragma: no cover - dependency guard.
    raise SystemExit("Install requirements-live.txt before running Cortex Agent acceptance.") from exc


DEFAULT_SQL_TEXT = (
    "SELECT customer_id, email, arr "
    "FROM ACMECLOUD_DEMO.PUBLIC.CUSTOMERS "
    "WHERE region = 'EU'"
)
TOOL_NAME = "validate_query_with_metatate"
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")


class AcceptanceError(RuntimeError):
    """Raised when the live Cortex Agent runtime contract is not met."""


@dataclass(frozen=True)
class Config:
    account_url: str
    token: str
    token_type: str
    role: str
    warehouse: str
    database: str
    schema: str
    app_name: str
    procedure_name: str
    agent_name: str
    model: str
    timeout_seconds: int

    @property
    def procedure_fqn(self) -> str:
        return f"{self.database}.{self.schema}.{self.procedure_name}"

    @property
    def metatate_validate_fqn(self) -> str:
        return f"{self.app_name}.CORE.AGENT_VALIDATE_QUERY_CONTEXT"

    @property
    def agent_fqn(self) -> str:
        return f"{self.database}.{self.schema}.{self.agent_name}"


class SnowflakeClient:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {config.token}",
                "X-Snowflake-Authorization-Token-Type": config.token_type,
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    def sql(self, statement: str, timeout: int | None = None) -> dict[str, Any]:
        response = self.session.post(
            f"{self.config.account_url}/api/v2/statements",
            json={
                "statement": statement,
                "timeout": timeout or self.config.timeout_seconds,
                "role": self.config.role,
                "warehouse": self.config.warehouse,
            },
            timeout=timeout or self.config.timeout_seconds,
        )
        return self._result_or_raise(response, poll=True)

    def post(self, path: str, payload: dict[str, Any], timeout: int | None = None) -> dict[str, Any]:
        response = self.session.post(
            f"{self.config.account_url}{path}",
            json=payload,
            timeout=timeout or self.config.timeout_seconds,
        )
        return self._result_or_raise(response, poll=False)

    def _result_or_raise(self, response: requests.Response, poll: bool) -> dict[str, Any]:
        if response.status_code in {200, 201}:
            return response.json()
        if poll and response.status_code == 202:
            return self._poll_statement(response.json())
        raise AcceptanceError(
            f"Snowflake request failed with HTTP {response.status_code}: {response.text[:2000]}"
        )

    def _poll_statement(self, payload: dict[str, Any]) -> dict[str, Any]:
        status_url = payload.get("statementStatusUrl")
        if not status_url:
            raise AcceptanceError(f"Async SQL response did not include statementStatusUrl: {payload}")

        deadline = time.monotonic() + self.config.timeout_seconds
        while time.monotonic() < deadline:
            response = self.session.get(f"{self.config.account_url}{status_url}", timeout=30)
            if response.status_code == 200:
                return response.json()
            if response.status_code != 202:
                raise AcceptanceError(
                    f"Async SQL status failed with HTTP {response.status_code}: {response.text[:2000]}"
                )
            time.sleep(2)
        raise AcceptanceError("Timed out waiting for async SQL statement to finish.")


def main() -> None:
    config = load_config()
    validate_config(config)
    client = SnowflakeClient(config)

    setup_runtime_objects(client, config)
    direct_result = run_direct_tool_smoke(client, config)
    agent_response = create_and_run_agent(client, config)
    agent_result = assert_agent_result(agent_response)

    direct_decision = decision_label(direct_result)
    agent_decision = decision_label(agent_result)
    if direct_decision != "CONDITIONAL" or agent_decision != "CONDITIONAL":
        raise AcceptanceError(
            f"Expected CONDITIONAL decisions from direct wrapper and agent runtime, got "
            f"{direct_decision} and {agent_decision}."
        )

    print("Cortex Agent runtime acceptance passed")
    print(f"- Agent: {config.agent_fqn}")
    print(f"- Tool: {TOOL_NAME}")
    print(f"- Decision: {agent_decision}")
    print(f"- Can execute query: {agent_result['data']['agent_action'].get('can_execute_query')}")


def load_config() -> Config:
    token_env = os.getenv("METATATE_CORTEX_PAT_ENV") or os.getenv(
        "METATATE_MCP_PAT_ENV", "METATATE_EXAMPLES_PAT"
    )
    token = os.getenv(token_env)
    if not token:
        raise AcceptanceError(f"${token_env} must contain the Snowflake PAT secret.")

    account_url = (
        os.getenv("METATATE_CORTEX_ACCOUNT_URL")
        or os.getenv("METATATE_MCP_ACCOUNT_URL")
        or os.getenv("SNOWFLAKE_ACCOUNT_URL")
        or account_url_from_mcp_url()
    )
    if not account_url:
        raise AcceptanceError(
            "Set METATATE_CORTEX_ACCOUNT_URL, METATATE_MCP_ACCOUNT_URL, "
            "SNOWFLAKE_ACCOUNT_URL, or METATATE_MCP_URL."
        )

    return Config(
        account_url=account_url.rstrip("/"),
        token=token,
        token_type=os.getenv("METATATE_MCP_TOKEN_TYPE", "PROGRAMMATIC_ACCESS_TOKEN"),
        role=os.getenv("METATATE_CORTEX_ROLE") or os.getenv("SNOWFLAKE_ROLE", "NAC"),
        warehouse=os.getenv("METATATE_CORTEX_WAREHOUSE", "WH_NAC"),
        database=os.getenv("METATATE_CORTEX_DATABASE", "METATATE_EXAMPLES_RUNTIME"),
        schema=os.getenv("METATATE_CORTEX_SCHEMA", "CORTEX_AGENT"),
        app_name=os.getenv("METATATE_APP_NAME", "METATATE_APP"),
        procedure_name=os.getenv("METATATE_CORTEX_PROCEDURE", "METATATE_VALIDATE_QUERY_TOOL"),
        agent_name=os.getenv("METATATE_CORTEX_AGENT", "METATATE_GOVERNED_SQL_AGENT"),
        model=os.getenv("METATATE_CORTEX_AGENT_MODEL", "auto"),
        timeout_seconds=int(os.getenv("METATATE_CORTEX_TIMEOUT_SECONDS", "300")),
    )


def account_url_from_mcp_url() -> str | None:
    mcp_url = os.getenv("METATATE_MCP_URL")
    if not mcp_url:
        return None
    parsed = urlparse(mcp_url)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def validate_config(config: Config) -> None:
    for name, value in (
        ("role", config.role),
        ("warehouse", config.warehouse),
        ("database", config.database),
        ("schema", config.schema),
        ("app_name", config.app_name),
        ("procedure_name", config.procedure_name),
        ("agent_name", config.agent_name),
    ):
        if not IDENTIFIER_RE.match(value):
            raise AcceptanceError(f"{name} must be an unquoted Snowflake identifier, got {value!r}.")


def setup_runtime_objects(client: SnowflakeClient, config: Config) -> None:
    for statement in (
        f"CREATE DATABASE IF NOT EXISTS {config.database}",
        f"CREATE SCHEMA IF NOT EXISTS {config.database}.{config.schema}",
        create_wrapper_procedure_sql(config),
    ):
        client.sql(statement)


def create_wrapper_procedure_sql(config: Config) -> str:
    return f"""
CREATE OR REPLACE PROCEDURE {config.procedure_fqn}(
    SQL_TEXT VARCHAR,
    OPERATION VARCHAR,
    INTENDED_USE VARCHAR,
    ACTOR_ROLE VARCHAR
)
RETURNS VARIANT
LANGUAGE JAVASCRIPT
EXECUTE AS CALLER
AS
$$
var stmt = snowflake.createStatement({{
  sqlText: 'CALL {config.metatate_validate_fqn}(?, ?, ?, ?)',
  binds: [SQL_TEXT, OPERATION, INTENDED_USE, ACTOR_ROLE]
}});
var rs = stmt.execute();
rs.next();
return rs.getColumnValue(1);
$$
""".strip()


def run_direct_tool_smoke(client: SnowflakeClient, config: Config) -> dict[str, Any]:
    response = client.sql(
        f"""
CALL {config.procedure_fqn}(
  {sql_literal(DEFAULT_SQL_TEXT)},
  'read',
  'analytics',
  'DATA_ANALYST'
)
""".strip(),
        timeout=120,
    )
    result = first_cell(response)
    payload = parse_variant(result)
    assert_metatate_result(payload)
    return payload


def create_and_run_agent(client: SnowflakeClient, config: Config) -> dict[str, Any]:
    agent_payload = {
        "name": config.agent_name,
        "comment": "Runtime acceptance agent for Metatate examples. Safe to replace.",
        "profile": {"display_name": "Metatate Governed SQL Agent"},
        "models": {"orchestration": config.model},
        "instructions": {
            "response": "Return a concise summary of the Metatate validation decision. Do not execute SQL.",
            "orchestration": (
                f"Always call {TOOL_NAME} before answering any SQL validation request. "
                "Report the decision and whether the SQL should execute."
            ),
        },
        "orchestration": {"budget": {"seconds": 90, "tokens": 8000}},
        "tools": [
            {
                "tool_spec": {
                    "type": "generic",
                    "name": TOOL_NAME,
                    "description": (
                        "Validate a SQL query against Metatate deployed decision policies "
                        "before execution."
                    ),
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "sql_text": {"type": "string", "description": "SQL query text to validate."},
                            "operation": {"type": "string", "description": "Operation such as read."},
                            "intended_use": {
                                "type": "string",
                                "description": "Business purpose such as analytics or marketing.",
                            },
                            "actor_role": {
                                "type": "string",
                                "description": "Business role requesting the operation.",
                            },
                        },
                    },
                    "required": ["sql_text", "operation", "intended_use", "actor_role"],
                }
            }
        ],
        "tool_resources": {
            TOOL_NAME: {
                "type": "procedure",
                "execution_environment": {
                    "type": "warehouse",
                    "warehouse": config.warehouse,
                    "query_timeout": 120,
                },
                "identifier": config.procedure_fqn,
            }
        },
    }
    client.post(
        f"/api/v2/databases/{config.database}/schemas/{config.schema}/agents?createMode=orReplace",
        agent_payload,
        timeout=120,
    )

    prompt = (
        "Validate this SQL and report the Metatate decision: "
        f"{DEFAULT_SQL_TEXT}. Operation read, intended_use analytics, actor_role DATA_ANALYST."
    )
    return client.post(
        f"/api/v2/databases/{config.database}/schemas/{config.schema}/agents/{config.agent_name}:run",
        {
            "stream": False,
            "tool_choice": {"type": "auto", "name": [TOOL_NAME]},
            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        },
        timeout=config.timeout_seconds,
    )


def assert_agent_result(response: dict[str, Any]) -> dict[str, Any]:
    content = response.get("content") or []
    tool_uses = [item.get("tool_use") for item in content if item.get("tool_use")]
    tool_results = [item.get("tool_result") for item in content if item.get("tool_result")]

    if not tool_uses:
        raise AcceptanceError(f"Cortex Agent response did not include a tool_use: {json.dumps(response)[:2000]}")
    if not tool_results:
        raise AcceptanceError(f"Cortex Agent response did not include a tool_result: {json.dumps(response)[:2000]}")

    tool_use = tool_uses[0]
    if tool_use.get("name") != TOOL_NAME:
        raise AcceptanceError(f"Expected tool {TOOL_NAME}, got {tool_use.get('name')}.")
    if tool_use.get("client_side_execute") is not False:
        raise AcceptanceError("Expected Cortex Agent to execute the tool server-side.")

    result = tool_results[0]
    if result.get("status") != "success":
        raise AcceptanceError(f"Cortex Agent tool_result was not successful: {result}")

    payload = extract_tool_result_payload(result)
    assert_metatate_result(payload)
    return payload


def extract_tool_result_payload(tool_result: dict[str, Any]) -> dict[str, Any]:
    content = tool_result.get("content") or []
    json_content = next((item.get("json") for item in content if item.get("type") == "json"), None)
    if not isinstance(json_content, dict):
        raise AcceptanceError(f"Tool result did not include JSON content: {tool_result}")
    result = json_content.get("result")
    payload = parse_variant(result)
    if not isinstance(payload, dict):
        raise AcceptanceError(f"Tool result payload was not a JSON object: {payload!r}")
    return payload


def assert_metatate_result(payload: dict[str, Any]) -> None:
    data = payload.get("data") or {}
    action = data.get("agent_action") or {}
    if decision_label(payload) != "CONDITIONAL":
        raise AcceptanceError(f"Expected CONDITIONAL Metatate decision, got {decision_label(payload)}.")
    if action.get("can_execute_query") is not False:
        raise AcceptanceError(f"Expected can_execute_query=false, got {action.get('can_execute_query')!r}.")
    columns = {str(column).upper() for column in data.get("extracted_columns") or []}
    if "EMAIL" not in columns:
        raise AcceptanceError(f"Expected EMAIL to be recognized as a governed column, got {columns}.")


def decision_label(payload: dict[str, Any]) -> str:
    data = payload.get("data") or {}
    decision = data.get("decision")
    if isinstance(decision, dict):
        return str(decision.get("decision") or decision.get("overall_decision") or "UNKNOWN").upper()
    return str(decision or data.get("overall_decision") or "UNKNOWN").upper()


def first_cell(response: dict[str, Any]) -> Any:
    data = response.get("data") or []
    if not data or not data[0]:
        raise AcceptanceError(f"SQL response did not include a result row: {response}")
    return data[0][0]


def parse_variant(value: Any) -> Any:
    if isinstance(value, str):
        return json.loads(value)
    return value


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


if __name__ == "__main__":
    try:
        main()
    except AcceptanceError as exc:
        print(f"Cortex Agent runtime acceptance failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
