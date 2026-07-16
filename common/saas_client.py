"""Live client for the Metatate Cloud MCP endpoint — native, no translation.

Metatate Cloud speaks the typed-answer contract directly: structured
``asset {database, schema, table, column?}`` references (lowercase normalized
names), snake_case keys, typed states
(``answered`` / ``review_required`` / ``not_enough_published_state``),
destination-aware transfer authorization (``operation`` / ``destination`` /
``consumer_jurisdiction``), and intent-/column-aware query validation.
This client passes those arguments through verbatim and returns each tool's
``structuredContent`` untouched — every answer is 100% server-derived, and the
offline recordings replay the same shapes (see ``common/metatate_client.py``).

Scenario keys are canonical (`purpose.allowed_use`, `ai.training`,
`residency.cross_border_transfer`, …). When you omit ``scenario_key``, the
SERVER's deterministic mapper resolves your free-text ``use`` — an unmappable
use is the typed ``scenario_unresolved`` answer, never a guess.
"""

from __future__ import annotations

from typing import Any

from .metatate_client import ManagedMCPMetatateClient


def _drop_none(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


class MetatateCloudClient(ManagedMCPMetatateClient):
    """The seven governance tools over the workspace MCP endpoint
    (bearer ``mtt_…`` token from the MCP module's Tokens tab)."""

    def discover_context(
        self, database: str | None = None, schema: str | None = None
    ) -> dict[str, Any]:
        return self.call_tool(
            "discover_context", _drop_none({"database": database, "schema": schema})
        )

    def get_decision_context(
        self, asset: dict[str, str], scenario_key: str | None = None
    ) -> dict[str, Any]:
        return self.call_tool(
            "get_decision_context",
            _drop_none({"asset": asset, "scenario_key": scenario_key}),
        )

    def inspect_data_meaning(self, ref: dict[str, str]) -> dict[str, Any]:
        return self.call_tool("inspect_data_meaning", {"ref": ref})

    def inspect_governance_rules(
        self, asset: dict[str, str], scenario_key: str | None = None
    ) -> dict[str, Any]:
        return self.call_tool(
            "inspect_governance_rules",
            _drop_none({"asset": asset, "scenario_key": scenario_key}),
        )

    def authorize_use(
        self,
        asset: dict[str, str],
        use: str,
        scenario_key: str | None = None,
        operation: str | None = None,
        destination: dict[str, str] | None = None,
        consumer_jurisdiction: str | None = None,
    ) -> dict[str, Any]:
        return self.call_tool(
            "authorize_use",
            _drop_none(
                {
                    "asset": asset,
                    "use": use,
                    "scenario_key": scenario_key,
                    "operation": operation,
                    "destination": destination,
                    "consumer_jurisdiction": consumer_jurisdiction,
                }
            ),
        )

    def validate_query_context(
        self,
        sql: str,
        scenario_key: str | None = None,
        use: str | None = None,
        default_database: str | None = None,
        default_schema: str | None = None,
        operation: str | None = None,
        destination: dict[str, str] | None = None,
        consumer_jurisdiction: str | None = None,
    ) -> dict[str, Any]:
        return self.call_tool(
            "validate_query_context",
            _drop_none(
                {
                    "sql": sql,
                    "scenario_key": scenario_key,
                    "use": use,
                    "default_database": default_database,
                    "default_schema": default_schema,
                    "operation": operation,
                    "destination": destination,
                    "consumer_jurisdiction": consumer_jurisdiction,
                }
            ),
        )

    def explain_why(self, decision_id: str) -> dict[str, Any]:
        # `kind='decision'` is the only server explain surface; validation
        # records have none (docs/live-mode-saas.md).
        return self.call_tool("explain_why", {"kind": "decision", "decision_id": decision_id})
