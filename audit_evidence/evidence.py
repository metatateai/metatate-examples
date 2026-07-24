#!/usr/bin/env python3
"""The audit evidence packet — from decision ids to an audit-ready report.

"Advisory" does not mean unaccountable: every Metatate answer carries a
`decision_id`, publication provenance, and cited policy versions, and
`explain_why` re-resolves any decision after the fact (including whether it
is still CURRENT in the live publication). This module turns a day of
governed questions into a single evidence packet a governance lead can hand
to an auditor — decisions, citations, conditions, obligations, the explain
chain, and the honest corners where the estate refused to guess.

Offline it replays recorded answers; live it collects real evidence from
your workspace. The server keeps its own ledger too: MCP Tools → Tokens →
"View requests" in the product.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from common import get_client

_DB = "acmecloud_demo"


def _asset(table: str, column: str | None = None, schema: str = "public") -> dict[str, str]:
    ref = {"database": _DB, "schema": schema, "table": table}
    if column:
        ref["column"] = column
    return ref


# The canonical "day of governed decisions" (every call is a recorded case):
# four decision-bearing answers with explain chains, plus the two honest
# corners — the ungoverned legacy table and the monitored custom mask.
DEFAULT_QUESTIONS: list[dict[str, Any]] = [
    {
        "question": "Can we build a churn analytics dashboard on customers?",
        "asset": _asset("customers"),
        "use": "build a churn analytics dashboard",
        "scenario_key": "purpose.allowed_use",
    },
    {
        "question": "Can we sync approved customer fields to Salesforce for EU consumers?",
        "asset": _asset("customers"),
        "use": "sync approved customer fields to the CRM",
        "scenario_key": "residency.cross_border_transfer",
        "operation": "export",
        "destination": {"system": "SALESFORCE", "jurisdiction": "US"},
        "consumer_jurisdiction": "EU",
    },
    {
        "question": "Can we fine-tune the support assistant on raw ticket text?",
        "asset": _asset("support_tickets"),
        "use": "fine-tune a support assistant on ticket text",
        "scenario_key": "ai.training",
    },
    {
        "question": "Can we train the churn model on derived features instead?",
        "asset": _asset("ml_feature_store"),
        "use": "train the churn model on derived features",
        "scenario_key": "ai.training",
    },
    {
        "question": "Can we report on the legacy customer backup?",
        "asset": _asset("legacy_customer_backup"),
        "use": "report on the legacy customer backup",
        "scenario_key": "purpose.allowed_use",
    },
    {
        "question": "Can we display employee names in the people directory?",
        "asset": _asset("employees", "full_name"),
        "use": "display employee names in the people directory",
        "scenario_key": "masking.display",
    },
]


@dataclass(frozen=True)
class PacketEntry:
    question: str
    asset: str
    scenario_key: str | None
    state: str
    decision: str | None
    reason_code: str | None
    evidence_id: str | None
    policy: str | None
    policy_version: int | None
    instruction_key: str | None
    conditions: list[str]
    obligations: list[str]
    prohibitions: int
    explanation_current: bool | None
    explanation: str | None


@dataclass(frozen=True)
class EvidencePacket:
    publication_id: str | None
    published_at: str | None
    total: int
    explained: int
    current: int
    honest_corners: int
    entries: list[PacketEntry]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["entries"] = [asdict(entry) for entry in self.entries]
        return payload


def _asset_path(ref: dict[str, Any]) -> str:
    parts = [str(ref.get(key)) for key in ("database", "schema", "table") if ref.get(key)]
    path = ".".join(parts)
    return f"{path}.{ref['column']}" if ref.get("column") else path


def _entry_from_answer(
    question: dict[str, Any],
    answer: dict[str, Any],
    explanation: dict[str, Any] | None,
) -> PacketEntry:
    instructions = answer.get("instructions") or []
    provenance = (instructions[0].get("provenance") or {}) if instructions else {}
    return PacketEntry(
        question=str(question["question"]),
        asset=_asset_path(question["asset"]),
        scenario_key=answer.get("scenario_key") or question.get("scenario_key"),
        state=str(answer.get("state") or "unknown"),
        decision=answer.get("decision"),
        reason_code=answer.get("reason_code"),
        evidence_id=answer.get("decision_id"),
        policy=provenance.get("policy_name"),
        policy_version=provenance.get("version_number"),
        instruction_key=(instructions[0].get("instruction_key") if instructions else None),
        conditions=[str(c.get("kind")) for c in answer.get("conditions") or []],
        obligations=[
            f"{o.get('type')}: {o.get('target')}" for o in answer.get("obligations") or []
        ],
        prohibitions=len(answer.get("prohibitions") or []),
        explanation_current=(explanation or {}).get("current"),
        explanation=(explanation or {}).get("explanation"),
    )


def collect_evidence(
    client: Any | None = None,
    questions: list[dict[str, Any]] | None = None,
) -> EvidencePacket:
    """Ask the governed questions, chain explain_why, assemble the packet."""

    client = client or get_client()
    if questions is None:
        questions = DEFAULT_QUESTIONS

    entries: list[PacketEntry] = []
    publication_id: str | None = None
    published_at: str | None = None

    for question in questions:
        answer = client.authorize_use(
            question["asset"],
            use=str(question.get("use") or question["question"]),
            scenario_key=question.get("scenario_key"),
            operation=question.get("operation"),
            destination=question.get("destination"),
            consumer_jurisdiction=question.get("consumer_jurisdiction"),
        )
        publication = answer.get("publication")
        if publication_id is None and isinstance(publication, dict):
            publication_id = publication.get("publication_id")
            published_at = publication.get("published_at")

        explanation = None
        if answer.get("state") == "answered" and answer.get("decision_id"):
            explanation = client.explain_why(answer["decision_id"])
        entries.append(_entry_from_answer(question, answer, explanation))

    explained = sum(1 for entry in entries if entry.explanation_current is not None)
    return EvidencePacket(
        publication_id=publication_id,
        published_at=published_at,
        total=len(entries),
        explained=explained,
        current=sum(1 for entry in entries if entry.explanation_current is True),
        honest_corners=sum(1 for entry in entries if entry.state != "answered"),
        entries=entries,
    )


def render_markdown(packet: EvidencePacket) -> str:
    lines = [
        "# Metatate evidence packet",
        "",
        f"Publication `{packet.publication_id}` (published {packet.published_at}).",
        f"{packet.total} governed decisions; {packet.current}/{packet.explained} explained "
        f"and CURRENT; {packet.honest_corners} honest corners (no fabricated answers).",
        "",
        "## Decisions",
    ]
    number = 0
    for entry in packet.entries:
        if entry.state != "answered":
            continue
        number += 1
        lines += [
            "",
            f"### {number}. {entry.question}",
            f"- Asset: `{entry.asset}` — scenario `{entry.scenario_key}`",
            f"- Decision: **{entry.decision}** (state {entry.state})",
            f"- Evidence: `{entry.evidence_id}`",
        ]
        if entry.policy:
            lines.append(
                f"- Cited policy: {entry.policy} v{entry.policy_version} "
                f"(instruction `{entry.instruction_key}`)"
            )
        if entry.conditions:
            lines.append(f"- Conditions: {', '.join(entry.conditions)}")
        if entry.obligations:
            lines.append(f"- Obligations: {'; '.join(entry.obligations)}")
        if entry.prohibitions:
            lines.append(f"- Prohibitions cited: {entry.prohibitions}")
        if entry.explanation_current is not None:
            lines.append(f"- Explain chain: current = {str(entry.explanation_current).lower()}")

    lines += ["", "## Honest corners", ""]
    for entry in packet.entries:
        if entry.state == "answered":
            continue
        lines.append(
            f"- `{entry.asset}` ({entry.scenario_key}): **{entry.state}**"
            f" ({entry.reason_code}) — the estate refused to guess."
        )
    lines += [
        "",
        "## Ledger",
        "",
        "Every call above is also in the workspace's server-side request log "
        "(MCP Tools → Tokens → View requests). Advisory answers, accountable "
        "trail: decision ids resolve via `explain_why` for as long as the "
        "history is retained, and `current` flags decisions superseded by a "
        "later publication.",
    ]
    return "\n".join(lines) + "\n"


def print_packet(packet: EvidencePacket) -> None:
    print(
        f"evidence packet: {packet.total} decisions, "
        f"{packet.current}/{packet.explained} explained+current, "
        f"{packet.honest_corners} honest corners"
    )
    for entry in packet.entries:
        label = entry.decision or entry.state
        evidence = f" evidence={entry.evidence_id}" if entry.evidence_id else ""
        print(f"  {entry.asset} [{entry.scenario_key}] -> {label}{evidence}")
