"""Provider-neutral LLM planner for LIVE mode (never used in CI).

Drafting and narration are the ONLY things the model does — every governance
decision still comes from Metatate, and the arc's routing reads the typed
answers, not the prose. Select a model with ``METATATE_EXAMPLES_LLM``
(anything ``init_chat_model`` accepts, e.g. ``anthropic:claude-sonnet-5``).
"""

from __future__ import annotations

from typing import Any


class LlmPlanner:
    def __init__(self, model: str) -> None:
        try:
            from langchain.chat_models import init_chat_model
        except ImportError as exc:  # pragma: no cover - dependency guard.
            raise RuntimeError(
                "Install requirements-llm.txt to use the LLM planner "
                "(pip install -r requirements-llm.txt plus your provider extra)."
            ) from exc
        self._model = init_chat_model(model)

    def draft_dashboard_sql(self, brief: str, rulebook: dict[str, Any]) -> str:
        families = sorted(
            {str(rule.get("instruction_family")) for rule in rulebook.get("rules") or []}
        )
        prompt = (
            "Draft ONE PostgreSQL SELECT for this task and return only the SQL, "
            "no fences, no prose.\n"
            f"Task: {brief}\n"
            "Table: acmecloud_demo.public.customers"
            "(customer_id, customer_name, email, account_status, arr, region, "
            "marketing_consent, created_at).\n"
            f"Active governance rule families on the table: {', '.join(families)}."
        )
        return _text(self._model.invoke(prompt)).strip().rstrip(";")

    def revise_sql(self, draft_sql: str, validation: dict[str, Any]) -> str:
        reasons = [
            str(instruction.get("decision_reason") or "")
            for finding in validation.get("findings") or []
            for instruction in finding.get("instructions") or []
        ]
        prompt = (
            "Metatate validated this SQL as WARN. Revise it so it passes: "
            "aggregate, and drop every masked or unnecessary column. Return only "
            "the SQL, no fences, no prose.\n"
            f"SQL: {draft_sql}\n"
            f"Findings: {'; '.join(reason for reason in reasons if reason)}"
        )
        return _text(self._model.invoke(prompt)).strip().rstrip(";")

    def narrate(self, step: str, answer: dict[str, Any]) -> str:
        prompt = (
            f"In one short sentence, narrate this governed-agent step for a log. "
            f"Step: {step}. Typed answer (truncate mentally, cite the decision): "
            f"{str(answer)[:600]}"
        )
        return _text(self._model.invoke(prompt)).strip()


def _text(message: Any) -> str:
    content = getattr(message, "content", message)
    if isinstance(content, list):
        return "".join(
            part.get("text", "") if isinstance(part, dict) else str(part) for part in content
        )
    return str(content)
