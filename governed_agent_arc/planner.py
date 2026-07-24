"""Planner seam for the governed agent arc.

The arc's GOVERNANCE calls and routing never depend on the planner — the
planner only drafts SQL, revises it after a Metatate verdict, and narrates.
CI always uses the deterministic ScriptedPlanner (the house rule: CI never
calls an LLM); a provider-neutral LLM planner is opt-in for LIVE mode via
``METATATE_EXAMPLES_LLM`` (e.g. ``anthropic:claude-sonnet-5`` or
``openai:gpt-4.1`` — anything ``langchain.chat_models.init_chat_model``
accepts, see requirements-llm.txt).
"""

from __future__ import annotations

import os
from typing import Any, Protocol

from framework_runtime.scenarios import SAFE_ANALYTICS_SQL, UNSAFE_ANALYTICS_SQL


class Planner(Protocol):
    """What the arc needs from a planner. Nothing here touches governance."""

    def draft_dashboard_sql(self, brief: str, rulebook: dict[str, Any]) -> str: ...

    def revise_sql(self, draft_sql: str, validation: dict[str, Any]) -> str: ...

    def narrate(self, step: str, answer: dict[str, Any]) -> str: ...


class ScriptedPlanner:
    """Deterministic planner: canonical draft, canonical revision, no prose.

    The draft deliberately references the masked email column (the canonical
    UNSAFE analytics query) so the arc earns a real ``warn`` and must revise —
    exactly the recorded decision path the offline fixtures replay.
    """

    def draft_dashboard_sql(self, brief: str, rulebook: dict[str, Any]) -> str:
        return UNSAFE_ANALYTICS_SQL

    def revise_sql(self, draft_sql: str, validation: dict[str, Any]) -> str:
        return SAFE_ANALYTICS_SQL

    def narrate(self, step: str, answer: dict[str, Any]) -> str:
        return ""


def get_planner() -> Planner:
    """ScriptedPlanner unless METATATE_EXAMPLES_LLM opts into live drafting."""

    model = os.environ.get("METATATE_EXAMPLES_LLM", "").strip()
    if not model:
        return ScriptedPlanner()
    mode = os.environ.get("METATATE_EXAMPLES_MODE", "offline").strip().lower()
    if mode != "live":
        raise ValueError(
            "METATATE_EXAMPLES_LLM requires METATATE_EXAMPLES_MODE=live: offline "
            "replay only answers recorded calls, and an LLM-drafted query would "
            "hit the typed offline_fixture_missing error by design."
        )
    from governed_agent_arc.llm_planner import LlmPlanner

    return LlmPlanner(model)
