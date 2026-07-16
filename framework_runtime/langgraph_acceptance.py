#!/usr/bin/env python3
"""LangGraph runtime acceptance for the Metatate SQL guard pattern.

This imports the actual LangGraph StateGraph runtime, invokes a graph node that
calls Metatate, and asserts that Metatate decisions change the graph output.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, TypedDict

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


class AgentState(TypedDict, total=False):
    sql_text: str
    scenario_key: str
    result: dict[str, Any]


def main() -> None:
    try:
        from langgraph.graph import END, StateGraph
    except ImportError as exc:
        raise SystemExit("LangGraph is not installed. Run: pip install -r requirements-framework.txt") from exc

    client = RecordingMetatateClient()

    def validate_with_metatate(state: AgentState) -> AgentState:
        result = validate_sql_for_agent(
            client,
            sql_text=state["sql_text"],
            scenario_key=state.get("scenario_key", "purpose.allowed_use"),
            operation="read",
            actor_role="DATA_ANALYST",
        )
        return {**state, "result": result}

    graph = StateGraph(AgentState)
    graph.add_node("validate_with_metatate", validate_with_metatate)
    graph.set_entry_point("validate_with_metatate")
    graph.add_edge("validate_with_metatate", END)
    app = graph.compile()

    results = {
        "safe": app.invoke({"sql_text": SAFE_ANALYTICS_SQL, "scenario_key": "purpose.allowed_use"})["result"],
        "unsafe": app.invoke({"sql_text": UNSAFE_ANALYTICS_SQL, "scenario_key": "purpose.allowed_use"})["result"],
        "blocked": app.invoke({"sql_text": MARKETING_SQL, "scenario_key": "purpose.prohibited_use"})["result"],
    }

    assert_guard_behavior(results, len(client.calls))
    print(json.dumps({"framework": "langgraph", "results": results}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
