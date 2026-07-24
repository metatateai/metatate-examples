"""The governed agent arc: one task, end to end, every step a typed decision.

A single LangGraph ``StateGraph`` takes a realistic multi-part brief and
VISIBLY changes course because of governance:

1. it reads the rulebook first (``inspect_governance_rules`` as a planning
   input, not an afterthought);
2. its first SQL draft comes back ``warn`` — it revises and re-validates to
   ``pass`` (bounded self-revision, never returning unvalidated SQL);
3. the Salesforce export is ``conditional`` — it builds a human exception
   packet (reusing ``human_exception_workflow``) and resumes only after the
   reviewer attests the required controls;
4. the raw-ticket fine-tune is ``deny`` — it REROUTES to the governed
   alternative the estate actually allows (feature-store training), and that
   reroute is itself an evidenced authorize call;
5. it closes by chaining ``explain_why`` over every decision id it collected.

Deterministic offline: the ScriptedPlanner walks the same graph making only
RECORDED calls. The optional LLM planner (live mode) drafts/revises/narrates —
governance calls and routing stay identical.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, TypedDict

from common import get_client
from governed_agent_arc.planner import Planner, ScriptedPlanner
from human_exception_workflow import ReviewDecision, apply_review, item_from_answer

ARC_BRIEF = (
    "Build the EU churn dashboard, push the at-risk segment to Salesforce, "
    "and fine-tune the support assistant on ticket text."
)

MAX_REVISIONS = 1

_DATABASE = "acmecloud_demo"
_SCHEMA = "public"
_CUSTOMERS = {"database": _DATABASE, "schema": _SCHEMA, "table": "customers"}
_TICKETS = {"database": _DATABASE, "schema": _SCHEMA, "table": "support_tickets"}
_FEATURES = {"database": _DATABASE, "schema": _SCHEMA, "table": "ml_feature_store"}

# The export leg mirrors human_exception_workflow's canonical Salesforce
# request (same use text and transfer context as the recorded fixture).
EXPORT_REQUEST: dict[str, Any] = {
    "request_id": "arc-export-salesforce",
    "kind": "authorization",
    "title": "Export the at-risk segment to Salesforce",
    "description": "Sync customer fields to Salesforce for account operations.",
    "asset": _CUSTOMERS,
    "use": "sync approved customer fields to the CRM",
    "scenario_key": "residency.cross_border_transfer",
    "operation": "export",
    "destination": {"system": "SALESFORCE", "jurisdiction": "US"},
    "consumer_jurisdiction": "EU",
    "owner": "Revenue Operations",
    "reviewer_queue": "privacy-review",
    "required_attestations": ["approval_recorded", "anonymization_before_transfer"],
}

EXPORT_REVIEW = ReviewDecision(
    review_id="review-arc-export-salesforce",
    reviewer="privacy-review@example.com",
    decision="approve",
    comments="Approved for Salesforce only after anonymization and evidence recording.",
    controls_attested=["approval_recorded", "anonymization_before_transfer"],
)


def _answer_label(answer: dict[str, Any]) -> str:
    state = str(answer.get("state") or "")
    if state and state != "answered":
        return state
    if answer.get("verdict"):
        return str(answer["verdict"])
    if answer.get("decision"):
        return str(answer["decision"])
    if "current" in answer:
        return "current" if answer.get("current") else "stale"
    return state or "answered"


def _evidence_id(answer: dict[str, Any]) -> str | None:
    decision_id = answer.get("decision_id")
    if isinstance(decision_id, str):
        return decision_id
    publication = answer.get("publication")
    if isinstance(publication, dict) and isinstance(publication.get("publication_id"), str):
        return str(publication["publication_id"])
    record = answer.get("record")
    if isinstance(record, dict) and isinstance(record.get("decision_id"), str):
        return str(record["decision_id"])
    return None


class ArcRecordingClient:
    """Wrap the examples client and record every Metatate call the arc makes."""

    def __init__(self, client: Any | None = None) -> None:
        self.client = client or get_client()
        self.calls: list[dict[str, Any]] = []

    def _record(self, tool: str, answer: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(
            {"tool": tool, "label": _answer_label(answer), "evidence_id": _evidence_id(answer)}
        )
        return answer

    def inspect_governance_rules(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._record(
            "inspect_governance_rules", self.client.inspect_governance_rules(*args, **kwargs)
        )

    def authorize_use(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._record("authorize_use", self.client.authorize_use(*args, **kwargs))

    def validate_query_context(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._record(
            "validate_query_context", self.client.validate_query_context(*args, **kwargs)
        )

    def explain_why(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._record("explain_why", self.client.explain_why(*args, **kwargs))


class GovernedArcState(TypedDict, total=False):
    brief: str
    rulebook: dict[str, Any]
    dashboard_authorization: dict[str, Any]
    original_draft_sql: str
    draft_sql: str
    sql_validation: dict[str, Any]
    revision_count: int
    final_sql: str | None
    dashboard_status: str
    export_authorization: dict[str, Any]
    exception_packet: dict[str, Any] | None
    export_status: str
    resume_payload: dict[str, Any] | None
    finetune_decision: dict[str, Any]
    reroute_decision: dict[str, Any] | None
    training_status: str
    explain_ids: list[str]
    explanations: list[dict[str, Any]]
    transcript: list[str]


def build_governed_agent_arc(client: Any, planner: Planner | None = None) -> Any:
    """Compile the arc as a LangGraph StateGraph over an injected client."""

    try:
        from langgraph.graph import END, StateGraph
    except ImportError as exc:  # pragma: no cover - dependency guard.
        raise RuntimeError(
            "Install requirements-framework.txt to run the governed agent arc"
        ) from exc

    planner = planner or ScriptedPlanner()

    def say(state: GovernedArcState, line: str) -> list[str]:
        return [*state.get("transcript", []), line]

    def read_rulebook(state: GovernedArcState) -> GovernedArcState:
        rulebook = client.inspect_governance_rules(_CUSTOMERS)
        rules = rulebook.get("rules") or []
        families = sorted({str(rule.get("instruction_family")) for rule in rules})
        return {
            **state,
            "rulebook": rulebook,
            "transcript": say(
                state,
                f"rulebook: {len(rules)} active rules on customers "
                f"({', '.join(families[:5])}, ...)",
            ),
        }

    def authorize_dashboard(state: GovernedArcState) -> GovernedArcState:
        answer = client.authorize_use(
            _CUSTOMERS,
            use="build a churn analytics dashboard",
            scenario_key="purpose.allowed_use",
        )
        return {
            **state,
            "dashboard_authorization": answer,
            "explain_ids": [*state.get("explain_ids", []), *filter(None, [answer.get("decision_id")])],
            "transcript": say(state, f"dashboard use -> {_answer_label(answer)}"),
        }

    def draft_dashboard_sql(state: GovernedArcState) -> GovernedArcState:
        draft = planner.draft_dashboard_sql(state["brief"], state.get("rulebook", {}))
        return {
            **state,
            "original_draft_sql": draft,
            "draft_sql": draft,
            "revision_count": state.get("revision_count", 0),
            "transcript": say(state, f"draft SQL: {draft}"),
        }

    def validate_dashboard_sql(state: GovernedArcState) -> GovernedArcState:
        validation = client.validate_query_context(
            state["draft_sql"],
            scenario_key="purpose.allowed_use",
            default_database=_DATABASE,
            default_schema=_SCHEMA,
        )
        return {
            **state,
            "sql_validation": validation,
            "transcript": say(state, f"validate -> {_answer_label(validation)}"),
        }

    def route_after_validation(state: GovernedArcState) -> str:
        verdict = _answer_label(state.get("sql_validation", {}))
        if verdict == "pass":
            return "accept"
        if verdict == "warn" and state.get("revision_count", 0) < MAX_REVISIONS:
            return "revise"
        return "abort"

    def revise_dashboard_sql(state: GovernedArcState) -> GovernedArcState:
        revised = planner.revise_sql(state["draft_sql"], state.get("sql_validation", {}))
        return {
            **state,
            "draft_sql": revised,
            "revision_count": state.get("revision_count", 0) + 1,
            "transcript": say(state, f"revised SQL: {revised}"),
        }

    def accept_dashboard_sql(state: GovernedArcState) -> GovernedArcState:
        return {
            **state,
            "final_sql": state["draft_sql"],
            "dashboard_status": "validated",
            "transcript": say(state, "dashboard SQL accepted after governance review"),
        }

    def abort_dashboard(state: GovernedArcState) -> GovernedArcState:
        # Never return unvalidated SQL — the arc continues, without a dashboard.
        return {
            **state,
            "final_sql": None,
            "dashboard_status": "aborted_after_revisions",
            "transcript": say(state, "dashboard aborted: revision budget exhausted"),
        }

    def request_salesforce_export(state: GovernedArcState) -> GovernedArcState:
        answer = client.authorize_use(
            EXPORT_REQUEST["asset"],
            use=str(EXPORT_REQUEST["use"]),
            scenario_key=str(EXPORT_REQUEST["scenario_key"]),
            operation=str(EXPORT_REQUEST["operation"]),
            destination=dict(EXPORT_REQUEST["destination"]),
            consumer_jurisdiction=str(EXPORT_REQUEST["consumer_jurisdiction"]),
        )
        return {
            **state,
            "export_authorization": answer,
            "explain_ids": [*state.get("explain_ids", []), *filter(None, [answer.get("decision_id")])],
            "transcript": say(state, f"Salesforce export -> {_answer_label(answer)}"),
        }

    def route_after_export(state: GovernedArcState) -> str:
        label = _answer_label(state.get("export_authorization", {}))
        if label == "conditional":
            return "exception"
        if label == "allow":
            return "proceed"
        return "blocked"

    def build_packet(state: GovernedArcState) -> GovernedArcState:
        item = item_from_answer(EXPORT_REQUEST, state["export_authorization"])
        return {
            **state,
            "exception_packet": item.packet,
            "export_status": item.status,
            "transcript": say(
                state,
                f"exception packet {item.packet['packet_id']} -> {item.status} "
                f"(queue: {item.reviewer_queue})",
            ),
        }

    def resume_with_controls(state: GovernedArcState) -> GovernedArcState:
        item = item_from_answer(EXPORT_REQUEST, state["export_authorization"])
        reviewed = apply_review(item, EXPORT_REVIEW)
        return {
            **state,
            "export_status": reviewed.status,
            "resume_payload": reviewed.resume_payload,
            "transcript": say(
                state,
                f"review approved with attested controls -> {reviewed.status}",
            ),
        }

    def export_proceeds(state: GovernedArcState) -> GovernedArcState:
        return {
            **state,
            "export_status": "proceeded_without_exception",
            "transcript": say(state, "export allowed outright"),
        }

    def export_blocked(state: GovernedArcState) -> GovernedArcState:
        return {
            **state,
            "export_status": "blocked_by_policy",
            "transcript": say(state, "export blocked by policy"),
        }

    def request_ticket_finetune(state: GovernedArcState) -> GovernedArcState:
        answer = client.authorize_use(
            _TICKETS,
            use="fine-tune a support assistant on ticket text",
            scenario_key="ai.training",
        )
        return {
            **state,
            "finetune_decision": answer,
            "explain_ids": [*state.get("explain_ids", []), *filter(None, [answer.get("decision_id")])],
            "transcript": say(state, f"fine-tune on raw tickets -> {_answer_label(answer)}"),
        }

    def route_after_finetune(state: GovernedArcState) -> str:
        label = _answer_label(state.get("finetune_decision", {}))
        if label == "deny":
            return "reroute"
        if label == "allow":
            return "proceed"
        return "review"

    def reroute_to_governed_training(state: GovernedArcState) -> GovernedArcState:
        # The deny's next_actions point at an alternative asset; the rulebook
        # already showed training is feature-store territory. The reroute is
        # itself a governed, evidenced authorize call — not a workaround.
        answer = client.authorize_use(
            _FEATURES,
            use="train the churn model on derived features",
            scenario_key="ai.training",
        )
        status = (
            "rerouted_to_governed_alternative"
            if _answer_label(answer) == "allow"
            else "blocked_by_policy"
        )
        return {
            **state,
            "reroute_decision": answer,
            "training_status": status,
            "explain_ids": [*state.get("explain_ids", []), *filter(None, [answer.get("decision_id")])],
            "transcript": say(
                state,
                f"reroute: train on ml_feature_store features -> {_answer_label(answer)}",
            ),
        }

    def training_proceeds(state: GovernedArcState) -> GovernedArcState:
        return {
            **state,
            "training_status": "proceeded",
            "transcript": say(state, "training allowed as asked"),
        }

    def training_needs_review(state: GovernedArcState) -> GovernedArcState:
        return {
            **state,
            "training_status": "needs_policy_review",
            "transcript": say(state, "training question routed to policy review"),
        }

    def explain_decisions(state: GovernedArcState) -> GovernedArcState:
        explanations = []
        for decision_id in state.get("explain_ids", []):
            explanation = client.explain_why(decision_id)
            explanations.append(explanation)
        return {
            **state,
            "explanations": explanations,
            "transcript": say(
                state,
                f"explain_why chained over {len(explanations)} decisions "
                f"(all current: {all(e.get('current') for e in explanations)})",
            ),
        }

    graph = StateGraph(GovernedArcState)
    graph.add_node("read_rulebook", read_rulebook)
    graph.add_node("authorize_dashboard", authorize_dashboard)
    graph.add_node("draft_dashboard_sql", draft_dashboard_sql)
    graph.add_node("validate_dashboard_sql", validate_dashboard_sql)
    graph.add_node("revise_dashboard_sql", revise_dashboard_sql)
    graph.add_node("accept_dashboard_sql", accept_dashboard_sql)
    graph.add_node("abort_dashboard", abort_dashboard)
    graph.add_node("request_salesforce_export", request_salesforce_export)
    graph.add_node("build_packet", build_packet)
    graph.add_node("resume_with_controls", resume_with_controls)
    graph.add_node("export_proceeds", export_proceeds)
    graph.add_node("export_blocked", export_blocked)
    graph.add_node("request_ticket_finetune", request_ticket_finetune)
    graph.add_node("reroute_to_governed_training", reroute_to_governed_training)
    graph.add_node("training_proceeds", training_proceeds)
    graph.add_node("training_needs_review", training_needs_review)
    graph.add_node("explain_decisions", explain_decisions)

    graph.set_entry_point("read_rulebook")
    graph.add_edge("read_rulebook", "authorize_dashboard")
    graph.add_edge("authorize_dashboard", "draft_dashboard_sql")
    graph.add_edge("draft_dashboard_sql", "validate_dashboard_sql")
    graph.add_conditional_edges(
        "validate_dashboard_sql",
        route_after_validation,
        {
            "accept": "accept_dashboard_sql",
            "revise": "revise_dashboard_sql",
            "abort": "abort_dashboard",
        },
    )
    graph.add_edge("revise_dashboard_sql", "validate_dashboard_sql")
    graph.add_edge("accept_dashboard_sql", "request_salesforce_export")
    graph.add_edge("abort_dashboard", "request_salesforce_export")
    graph.add_conditional_edges(
        "request_salesforce_export",
        route_after_export,
        {
            "exception": "build_packet",
            "proceed": "export_proceeds",
            "blocked": "export_blocked",
        },
    )
    graph.add_edge("build_packet", "resume_with_controls")
    graph.add_edge("resume_with_controls", "request_ticket_finetune")
    graph.add_edge("export_proceeds", "request_ticket_finetune")
    graph.add_edge("export_blocked", "request_ticket_finetune")
    graph.add_conditional_edges(
        "request_ticket_finetune",
        route_after_finetune,
        {
            "reroute": "reroute_to_governed_training",
            "proceed": "training_proceeds",
            "review": "training_needs_review",
        },
    )
    graph.add_edge("reroute_to_governed_training", "explain_decisions")
    graph.add_edge("training_proceeds", "explain_decisions")
    graph.add_edge("training_needs_review", "explain_decisions")
    graph.add_edge("explain_decisions", END)
    return graph.compile()


@dataclass(frozen=True)
class ArcReport:
    brief: str
    decision_sequence: list[dict[str, Any]]
    metatate_calls: int
    draft_sql: str | None
    final_sql: str | None
    revision_count: int
    dashboard_status: str
    export_status: str
    exception_packet: dict[str, Any] | None
    resume_payload: dict[str, Any] | None
    training_status: str
    rerouted: bool
    explanations: list[dict[str, Any]]
    transcript: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_arc(client: Any | None = None, planner: Planner | None = None) -> ArcReport:
    """Run the whole arc and return the evidence-bearing report."""

    recording = client if isinstance(client, ArcRecordingClient) else ArcRecordingClient(client)
    graph = build_governed_agent_arc(recording, planner)
    state: GovernedArcState = graph.invoke(
        {"brief": ARC_BRIEF, "revision_count": 0, "explain_ids": [], "transcript": []}
    )
    explanations = state.get("explanations", [])
    return ArcReport(
        brief=state.get("brief", ARC_BRIEF),
        decision_sequence=[
            {"tool": call["tool"], "label": call["label"]} for call in recording.calls
        ],
        metatate_calls=len(recording.calls),
        draft_sql=state.get("original_draft_sql"),
        final_sql=state.get("final_sql"),
        revision_count=state.get("revision_count", 0),
        dashboard_status=state.get("dashboard_status", "unknown"),
        export_status=state.get("export_status", "unknown"),
        exception_packet=state.get("exception_packet"),
        resume_payload=state.get("resume_payload"),
        training_status=state.get("training_status", "unknown"),
        rerouted=state.get("reroute_decision") is not None,
        explanations=[
            {
                "decision_id": (explanation.get("record") or {}).get("decision_id"),
                "current": explanation.get("current"),
            }
            for explanation in explanations
        ],
        transcript=state.get("transcript", []),
    )


def print_transcript(report: ArcReport) -> None:
    print(f"brief: {report.brief}")
    for line in report.transcript:
        print(f"  {line}")
    print(
        f"outcome: dashboard={report.dashboard_status} export={report.export_status} "
        f"training={report.training_status}"
    )
    print(f"metatate calls: {report.metatate_calls}; every step evidence-bearing")
