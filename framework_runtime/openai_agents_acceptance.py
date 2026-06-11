#!/usr/bin/env python3
"""OpenAI Agents SDK runtime acceptance for the Metatate guard pattern.

This does not call an OpenAI model. It imports the actual Agents SDK, registers a
Metatate-backed function tool on an Agent, invokes that FunctionTool runtime, and
asserts that Metatate decisions change the agent-facing result.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from framework_runtime.scenarios import (  # noqa: E402
    MARKETING_SQL,
    SAFE_ANALYTICS_SQL,
    UNSAFE_ANALYTICS_SQL,
    RecordingMetatateClient,
    assert_guard_behavior,
    validate_sql_for_agent,
)


def main() -> None:
    try:
        from agents import Agent, FunctionTool, function_tool
    except ImportError as exc:
        raise SystemExit(
            "OpenAI Agents SDK is not installed. Run: pip install -r requirements-framework.txt"
        ) from exc

    client = RecordingMetatateClient()

    @function_tool(name_override="metatate_validate_sql", failure_error_function=None)
    def metatate_validate_sql(
        sql_text: str,
        intended_use: str = "analytics",
        operation: str = "read",
        actor_role: str = "DATA_ANALYST",
    ) -> str:
        """Validate SQL through Metatate before an agent uses it."""

        result = validate_sql_for_agent(
            client,
            sql_text=sql_text,
            intended_use=intended_use,
            operation=operation,
            actor_role=actor_role,
        )
        return json.dumps(result, sort_keys=True)

    agent = Agent(
        name="Metatate governed SQL agent",
        instructions="Validate generated SQL with Metatate before returning it.",
        tools=[metatate_validate_sql],
    )
    tool = _single_function_tool(agent.tools, FunctionTool)

    results = asyncio.run(
        _invoke_cases(
            tool,
            agent,
            {
                "safe": {
                    "sql_text": SAFE_ANALYTICS_SQL,
                    "intended_use": "analytics",
                },
                "unsafe": {
                    "sql_text": UNSAFE_ANALYTICS_SQL,
                    "intended_use": "analytics",
                },
                "blocked": {
                    "sql_text": MARKETING_SQL,
                    "intended_use": "marketing",
                },
            },
        )
    )

    assert_guard_behavior(results, len(client.calls))
    _assert_schema(tool)
    print(json.dumps({"framework": "openai-agents", "results": results}, indent=2, sort_keys=True))


def _single_function_tool(tools: list[Any], function_tool_type: type[Any]) -> Any:
    function_tools = [tool for tool in tools if isinstance(tool, function_tool_type)]
    assert len(function_tools) == 1, f"expected one FunctionTool, got {len(function_tools)}"
    return function_tools[0]


async def _invoke_cases(
    tool: Any,
    agent: Any,
    cases: dict[str, dict[str, str]],
) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for name, payload in cases.items():
        raw_result = await _invoke_openai_function_tool(tool, agent, payload)
        results[name] = json.loads(raw_result)
    return results


async def _invoke_openai_function_tool(tool: Any, agent: Any, payload: dict[str, str]) -> str:
    input_json = json.dumps(payload)
    invoke = tool.on_invoke_tool
    signature = inspect.signature(invoke)
    parameter_count = len(signature.parameters)

    if parameter_count == 2:
        result = invoke(_openai_tool_context(tool, agent, input_json), input_json)
    elif parameter_count == 1:
        result = invoke(input_json)
    else:
        raise AssertionError(f"Unsupported FunctionTool invocation signature: {signature}")

    if inspect.isawaitable(result):
        result = await result
    assert isinstance(result, str), f"expected string tool result, got {type(result)!r}"
    return result


def _openai_tool_context(tool: Any, agent: Any, input_json: str) -> Any:
    try:
        from agents.tool_context import ToolContext
    except ImportError:
        return None

    return ToolContext(
        context=None,
        tool_name=tool.name,
        tool_call_id=f"{tool.name}-acceptance",
        tool_arguments=input_json,
        agent=agent,
    )


def _assert_schema(tool: Any) -> None:
    schema = tool.params_json_schema
    properties = schema.get("properties", {})
    assert "sql_text" in properties, schema
    assert "intended_use" in properties, schema


if __name__ == "__main__":
    main()
