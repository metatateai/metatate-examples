"""Reusable LangGraph governed SQL agent example.

The graph is deterministic on purpose: it proves where Metatate sits in the
agent workflow without relying on model output.
"""

from __future__ import annotations

from typing import Any, TypedDict

from framework_runtime.scenarios import MARKETING_SQL, SAFE_ANALYTICS_SQL, UNSAFE_ANALYTICS_SQL


class GovernedSqlAgentState(TypedDict, total=False):
    question: str
    scenario_key: str
    draft_sql: str
    validation: dict[str, Any]
    decision: str
    route: str
    final_sql: str | None
    answer: str
    notes: list[str]
    publication_id: str | None


def build_governed_sql_agent(client: Any) -> Any:
    """Build a LangGraph SQL agent that validates every draft with Metatate."""

    try:
        from langgraph.graph import END, StateGraph
    except ImportError as exc:  # pragma: no cover - dependency guard.
        raise RuntimeError("Install requirements-framework.txt to run the LangGraph runtime example") from exc

    def plan_sql(state: GovernedSqlAgentState) -> GovernedSqlAgentState:
        sql_text, scenario_key = plan_question(state["question"])
        return {**state, "draft_sql": sql_text, "scenario_key": scenario_key, "notes": []}

    def validate_with_metatate(state: GovernedSqlAgentState) -> GovernedSqlAgentState:
        validation = client.validate_query_context(
            state["draft_sql"],
            scenario_key=state["scenario_key"],
            default_database="acmecloud_demo",
            default_schema="public",
        )
        decision = decision_label(validation)
        route = route_for_decision(decision)
        return {
            **state,
            "validation": validation,
            "decision": decision,
            "route": route,
            "publication_id": publication_id(validation),
        }

    def approve_sql(state: GovernedSqlAgentState) -> GovernedSqlAgentState:
        return {
            **state,
            "final_sql": state["draft_sql"],
            "answer": "Metatate approved the SQL for analytics. The agent may return the query.",
            "notes": [*state.get("notes", []), "approved_by_metatate"],
        }

    def revise_sql(state: GovernedSqlAgentState) -> GovernedSqlAgentState:
        return {
            **state,
            "final_sql": SAFE_ANALYTICS_SQL,
            "answer": "Metatate required minimization. The agent revised the SQL before returning it.",
            "notes": [*state.get("notes", []), "revised_after_metatate_decision"],
        }

    def block_sql(state: GovernedSqlAgentState) -> GovernedSqlAgentState:
        return {
            **state,
            "final_sql": None,
            "answer": "Metatate blocked this use. The agent must not return executable SQL.",
            "notes": [*state.get("notes", []), "blocked_by_metatate"],
        }

    graph = StateGraph(GovernedSqlAgentState)
    graph.add_node("plan_sql", plan_sql)
    graph.add_node("validate_with_metatate", validate_with_metatate)
    graph.add_node("approve_sql", approve_sql)
    graph.add_node("revise_sql", revise_sql)
    graph.add_node("block_sql", block_sql)
    graph.set_entry_point("plan_sql")
    graph.add_edge("plan_sql", "validate_with_metatate")
    graph.add_conditional_edges(
        "validate_with_metatate",
        lambda state: state["route"],
        {
            "approve": "approve_sql",
            "revise": "revise_sql",
            "block": "block_sql",
        },
    )
    graph.add_edge("approve_sql", END)
    graph.add_edge("revise_sql", END)
    graph.add_edge("block_sql", END)
    return graph.compile()


def plan_question(question: str) -> tuple[str, str]:
    """Map a user question to a deterministic SQL draft and canonical scenario."""

    normalized = question.lower()
    if "marketing" in normalized or "email campaign" in normalized:
        return MARKETING_SQL, "purpose.prohibited_use"
    if "email" in normalized or "identify" in normalized:
        return UNSAFE_ANALYTICS_SQL, "purpose.allowed_use"
    return SAFE_ANALYTICS_SQL, "purpose.allowed_use"


def route_for_decision(verdict: str) -> str:
    if verdict == "fail":
        return "block"
    if verdict == "pass":
        return "approve"
    return "revise"


def summarize_state(state: GovernedSqlAgentState) -> dict[str, Any]:
    return {
        "question": state["question"],
        "route": state.get("route"),
        "decision": state.get("decision"),
        "scenario_key": state.get("scenario_key"),
        "publication_id": state.get("publication_id"),
        "draft_sql": state.get("draft_sql"),
        "final_sql": state.get("final_sql"),
        "answer": state.get("answer"),
        "notes": state.get("notes", []),
    }


def acceptance_result(state: GovernedSqlAgentState) -> dict[str, Any]:
    route = state["route"]
    status = {"approve": "approved", "revise": "revised", "block": "blocked"}[route]
    return {
        "verdict": state["decision"],
        "status": status,
        "original_sql": state["draft_sql"],
        "final_sql": state.get("final_sql"),
        "publication_id": state.get("publication_id"),
        "route": route,
        "answer": state.get("answer"),
    }


def decision_label(answer: dict[str, Any]) -> str:
    state = str(answer.get("state") or "")
    if state and state != "answered":
        return state
    return str(answer.get("verdict") or "unknown")


def publication_id(answer: dict[str, Any]) -> str | None:
    publication = answer.get("publication")
    if isinstance(publication, dict) and publication.get("publication_id"):
        return str(publication["publication_id"])
    return None
