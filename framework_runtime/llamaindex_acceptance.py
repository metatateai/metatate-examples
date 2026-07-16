#!/usr/bin/env python3
"""LlamaIndex runtime acceptance for the Metatate retrieval guard pattern.

This imports the actual LlamaIndex FunctionTool, invokes the tool runtime, and
asserts that Metatate decisions change the returned retrieval plan.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from framework_runtime.scenarios import (  # noqa: E402
    RecordingMetatateClient,
    assert_guard_behavior,
    retrieval_prompt_to_sql,
    validate_sql_for_agent,
)


def main() -> None:
    try:
        from llama_index.core.tools import FunctionTool
    except ImportError as exc:
        raise SystemExit(
            "LlamaIndex core is not installed. Run: pip install -r requirements-framework.txt"
        ) from exc

    client = RecordingMetatateClient()

    def metatate_governed_retrieval(query: str) -> str:
        """Plan governed retrieval only after validating the implied data access."""

        sql_text, scenario_key = retrieval_prompt_to_sql(query)
        result = validate_sql_for_agent(
            client,
            sql_text=sql_text,
            scenario_key=scenario_key,
        )
        result["query"] = query
        return json.dumps(result, sort_keys=True)

    tool = FunctionTool.from_defaults(
        fn=metatate_governed_retrieval,
        name="metatate_governed_retrieval",
        description="Validate governed retrieval with Metatate before returning a plan.",
        return_direct=True,
    )

    results = {
        "safe": _call_tool(tool, "Summarize active ARR by region."),
        "unsafe": _call_tool(tool, "Find the EU customers and include emails."),
        "blocked": _call_tool(tool, "Build a direct marketing email campaign list."),
    }

    assert_guard_behavior(results, len(client.calls))
    _assert_schema(tool)
    print(json.dumps({"framework": "llamaindex", "results": results}, indent=2, sort_keys=True))


def _call_tool(tool: Any, query: str) -> dict[str, Any]:
    output = tool.call(query=query)
    raw_output = getattr(output, "raw_output", None)
    if raw_output is None:
        raw_output = str(output)
    return json.loads(raw_output)


def _assert_schema(tool: Any) -> None:
    schema = tool.metadata.get_parameters_dict()
    properties = schema.get("properties", {})
    assert "query" in properties, schema


if __name__ == "__main__":
    main()

