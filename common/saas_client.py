"""Live client for the Metatate SaaS (cross-platform) MCP server.

The SaaS server speaks the v2 typed-answer contract: structured
``asset {database, schema, table, column?}`` references (lowercase normalized
names), snake_case keys everywhere, typed answer states
(``answered`` / ``review_required`` / ``not_enough_published_state``), and
destination-aware transfer authorization (``operation`` / ``destination`` /
``consumer_jurisdiction`` inputs). This client translates the notebooks'
v1-style calls (``table_name`` FQNs, flattened params) to that contract and
maps the typed answers back onto the canonical fixture payload shape
(``{request_id, snapshot_id, as_of, status, data}``) so every notebook,
gate, and acceptance script runs unchanged.

Decisions stay 100% server-derived — this layer renames, nests, and
re-labels; it never invents governance outcomes.
"""

from __future__ import annotations

import json
import os
import uuid
from copy import deepcopy
from typing import Any

from .metatate_client import (
    ManagedMCPMetatateClient,
    _drop_none,
    _extract_mcp_payload,
    _meets_sensitivity,
)

# Canonical scenario keys the client maps intents onto (a deliberate, explicit
# table — free text is never guessed into a runtime key client-side).
_PROHIBITED_USES = {"marketing", "advertising", "personalization"}
_TRAINING_USES = {"ml_training", "training", "train", "fine_tuning", "fine-tuning"}
_ALLOWED_USES = {"analytics", "reporting", "support", "renewal_planning"}
_INFERENCE_USES = {"inference", "rag", "retrieval", "embedding", "embeddings"}

_DECISION_LABELS = {
    "allow": "ALLOW",
    "deny": "DENY",
    "conditional": "CONDITIONAL",
    "mask_full": "CONDITIONAL",
    "mask_partial": "CONDITIONAL",
    "require_review": "REVIEW",
    "log_only": "ALLOW",
    "retain": "ALLOW",
}

_CONDITION_REASON_CODES = {
    "approval_required": "APPROVAL_REQUIRED",
    "anonymize_first": "ANONYMIZATION_REQUIRED",
    "role_restricted": "ROLE_RESTRICTED",
    "ai_restriction": "AI_RESTRICTION",
}


class SaasMcpMetatateClient(ManagedMCPMetatateClient):
    """Live client for the Metatate SaaS MCP endpoint (bearer ``mtt_…`` token).

    Inherits the JSON-RPC transport (retries, SSE-or-JSON parsing, the
    optional ``initialize`` handshake) from :class:`ManagedMCPMetatateClient`
    and overrides auth headers, per-tool argument translation, and response
    normalization.
    """

    def __init__(self, endpoint: str | None = None) -> None:
        super().__init__(endpoint=endpoint or _saas_endpoint_from_env())
        # Bearer-only token: METATATE_MCP_TOKEN_ENV names the variable holding
        # the SaaS token (default METATATE_SAAS_MCP_TOKEN); METATATE_MCP_PAT_ENV
        # keeps working so run_notebook_pack.sh's live gate needs no changes.
        self.token_env = os.getenv("METATATE_MCP_TOKEN_ENV") or os.getenv(
            "METATATE_MCP_PAT_ENV", "METATATE_SAAS_MCP_TOKEN"
        )
        self.default_database = os.getenv("METATATE_SAAS_DEFAULT_DATABASE", "acmecloud_demo")
        self.default_schema = os.getenv("METATATE_SAAS_DEFAULT_SCHEMA", "public")
        self._assets_cache: list[dict[str, Any]] | None = None
        self._meaning_cache: dict[str, dict[str, Any]] = {}

    @property
    def session(self) -> Any:
        if self._session is None:
            try:
                import requests
            except ImportError as exc:  # pragma: no cover - live dependency.
                raise RuntimeError("Install requirements-live.txt to use live mode") from exc

            token = os.getenv(self.token_env)
            if not token:
                raise RuntimeError(
                    f"SaaS live mode requires a Metatate MCP access token in ${self.token_env} "
                    "(issue one in the workspace MCP module → Tokens)."
                )
            self._session = requests.Session()
            self._session.headers.update(
                {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                }
            )
        return self._session

    # ------------------------------------------------------------------
    # Tool surface (same seven duck-typed methods as the other clients)
    # ------------------------------------------------------------------

    def discover_context(self, **params: Any) -> dict[str, Any]:
        assets = self._governed_assets()
        tables: list[dict[str, Any]] = []
        for asset in assets:
            tables.append(self._table_summary(asset))

        database = _lower_or_none(params.get("database_name") or params.get("database"))
        schema = _lower_or_none(params.get("schema_name") or params.get("schema"))
        domain = params.get("domain")
        has_pii = params.get("has_pii")
        compliance_any = set(params.get("compliance_any") or [])
        if params.get("compliance_framework"):
            compliance_any.add(params["compliance_framework"])
        min_sensitivity = params.get("min_sensitivity")

        filtered = []
        for table in tables:
            if database and table["database_name"].lower() != database:
                continue
            if schema and table["schema_name"].lower() != schema:
                continue
            if domain and table.get("domain") != domain:
                continue
            if has_pii is not None and bool(table.get("has_pii")) is not bool(has_pii):
                continue
            if compliance_any and not compliance_any.intersection(table.get("compliance_frameworks") or []):
                continue
            if min_sensitivity and not _meets_sensitivity(table.get("sensitivity"), min_sensitivity):
                continue
            filtered.append(table)

        return _envelope(
            "discover",
            self._publication_hint(),
            "ok",
            {"total": len(filtered), "tables": filtered},
        )

    def get_decision_context(self, table_name: str) -> dict[str, Any]:
        asset = self._asset_ref(table_name)
        answer = self._tool("get_decision_context", {"asset": asset})
        if answer.get("_error"):
            return _error_payload(table_name, answer)
        state = answer.get("state")
        if state == "not_enough_published_state":
            return _not_enough_payload(table_name, answer)

        decisions = answer.get("decisions") or []
        meaning = self._table_meaning(asset)
        policies = sorted({(d.get("provenance") or {}).get("policy_name") or "?" for d in decisions})
        enforceable = [d for d in decisions if d.get("category") == "enforceable"]
        masked_columns = {
            (d.get("scope") or {}).get("column")
            for d in decisions
            if d.get("instruction_family") == "masking" and (d.get("scope") or {}).get("column")
        }
        business = answer.get("business_context") or {}
        retention_rows = [d for d in decisions if d.get("instruction_family") == "retention"]

        data = {
            "table_name": table_name,
            "policy_summary": {
                "sensitivity": (meaning.get("classification") or {}).get("sensitivity"),
                "enforcement_mode": "enforce"
                if any(d.get("enforcement_mode") == "enforce" for d in decisions)
                else "advisory",
                "policy_count": len(policies),
                "enforceable_count": len({(d.get("provenance") or {}).get("policy_name") for d in enforceable}),
                "advisory_count": max(
                    0,
                    len(policies)
                    - len({(d.get("provenance") or {}).get("policy_name") for d in enforceable}),
                ),
                "has_pii": bool(meaning.get("pii")),
                "pii_column_count": len(masked_columns),
                "control_tags": _control_tags(decisions),
            },
            "business_context": {
                "owner": business.get("owner"),
                "steward": business.get("steward"),
                "domain": business.get("domain"),
                "purpose": business.get("purpose"),
                "definitions": [],
            },
            "lineage": {
                "sources": [],
                "transformations": [],
                "dependents": [],
                "note": "Lineage is not part of the SaaS governed context yet.",
            },
            "retention": {
                "policy": retention_rows[0].get("decision_reason") if retention_rows else None
            },
            "contacts": {"owner": business.get("owner"), "steward": business.get("steward")},
        }
        return _envelope("decision-context", answer.get("publication"), "ok", data)

    def inspect_data_meaning(self, table_name: str, columns: list[str] | None = None) -> dict[str, Any]:
        asset = self._asset_ref(table_name)
        table_meaning = self._tool("inspect_data_meaning", {"ref": asset})
        if table_meaning.get("_error"):
            return _error_payload(table_name, table_meaning)

        column_names = [c.lower() for c in columns] if columns else self._governed_columns(asset)
        out_columns: list[dict[str, Any]] = []
        for column in column_names:
            fact = self._column_meaning(asset, column)
            if fact is None:
                continue
            classification = fact.get("classification") or {}
            masking = fact.get("masking") or {}
            out_columns.append(
                {
                    "column_name": column.upper(),
                    "data_type_id": (fact.get("data_type") or "unknown").upper(),
                    "data_type_label": _title(fact.get("data_type") or "unknown"),
                    "classification_sensitivity": classification.get("sensitivity"),
                    "classification_confidence": None,
                    "data_category": _title(classification.get("category")),
                    "is_pii": bool(fact.get("pii")),
                    "masking_type": masking.get("type"),
                    "effective_sensitivity": classification.get("sensitivity"),
                    "policy_name": None,
                }
            )
        data = {
            "table_name": table_name,
            "description": table_meaning.get("meaning"),
            "columns": out_columns,
        }
        return _envelope("data-meaning", self._publication_hint(), "ok", data)

    def inspect_governance_rules(self, table_name: str, columns: list[str] | None = None) -> dict[str, Any]:
        asset = self._asset_ref(table_name)
        answer = self._tool("inspect_governance_rules", {"asset": asset})
        if answer.get("_error"):
            return _error_payload(table_name, answer)
        if answer.get("state") == "not_enough_published_state":
            return _not_enough_payload(table_name, answer)

        usage_rules: list[dict[str, Any]] = []
        validation_rules: list[dict[str, Any]] = []
        transfer_rules: list[dict[str, Any]] = []
        for rule in answer.get("rules") or []:
            family = rule.get("instruction_family")
            policy = (rule.get("provenance") or {}).get("policy_name")
            mode = rule.get("enforcement_mode")
            if family == "usage_guidance":
                usage_rules.append(
                    {
                        "rule_type": "prohibited_use"
                        if rule.get("scenario_key") == "purpose.prohibited_use"
                        else "permitted_use",
                        "uses": [],
                        "effect": "deny" if rule.get("decision") == "deny" else "allow",
                        "description": rule.get("decision_reason"),
                        "policy_name": policy,
                        "enforcement_mode": mode,
                    }
                )
            elif family == "ai_governance":
                usage_rules.append(
                    {
                        "rule_type": "ai_governance",
                        "uses": [rule.get("scenario_key")],
                        "effect": "deny" if rule.get("decision") == "deny" else "conditional",
                        "description": rule.get("decision_reason"),
                        "policy_name": policy,
                        "enforcement_mode": mode,
                    }
                )
            elif family == "masking":
                parameters = rule.get("parameters") or {}
                validation_rules.append(
                    {
                        "rule_type": "column_masking",
                        "rule_config": {
                            "columns": [c for c in [(rule.get("scope") or {}).get("column")] if c],
                            "type": parameters.get("type"),
                        },
                        "description": rule.get("decision_reason"),
                        "policy_name": policy,
                        "enforcement_mode": mode,
                    }
                )
            elif family == "transfer_governance":
                parameters = rule.get("parameters") or {}
                for authored in parameters.get("rules") or []:
                    transfer_rules.append(
                        {
                            "effect": authored.get("effect")
                            or ("conditional" if authored.get("requiresApproval") else "allow"),
                            "operations": authored.get("operations") or [],
                            "destination_systems": authored.get("destinationSystems") or [],
                            "destination_jurisdictions": authored.get("destinationJurisdictions") or [],
                            "consumer_jurisdictions": authored.get("consumerJurisdictions") or [],
                            "requires_approval": bool(authored.get("requiresApproval")),
                            "requires_anonymization": bool(authored.get("requiresAnonymization")),
                            "required_role": authored.get("requiredRole"),
                            "policy_name": policy,
                        }
                    )
                if parameters.get("defaultEffect"):
                    transfer_rules.append(
                        {
                            "effect": parameters["defaultEffect"],
                            "operations": [],
                            "destination_systems": ["*"],
                            "destination_jurisdictions": [],
                            "consumer_jurisdictions": [],
                            "requires_approval": parameters["defaultEffect"] == "conditional",
                            "requires_anonymization": False,
                            "required_role": None,
                            "policy_name": policy,
                        }
                    )
        data = {
            "table_name": table_name,
            "usage_rules": usage_rules,
            "validation_rules": validation_rules,
            "transfer_rules": transfer_rules,
        }
        status = "warning" if answer.get("state") == "review_required" else "ok"
        return _envelope("governance-rules", answer.get("publication"), status, data)

    def authorize_use(self, table_name: str, operation: str, intended_use: str, **params: Any) -> dict[str, Any]:
        asset = self._asset_ref(table_name, _single_column(params.get("columns")))
        destination = params.get("destination") or {}
        destination_system = params.get("destination_system") or destination.get("system")
        destination_jurisdiction = params.get("destination_jurisdiction") or destination.get("jurisdiction")
        consumer_jurisdiction = params.get("consumer_jurisdiction")
        has_transfer_context = bool(destination_system or destination_jurisdiction or consumer_jurisdiction)

        scenario = _scenario_for(operation, intended_use, has_transfer_context)
        arguments: dict[str, Any] = {
            "asset": asset,
            "use": f"{operation} {table_name} for {intended_use}".strip(),
        }
        if scenario:
            arguments["scenario_key"] = scenario
        if operation:
            arguments["operation"] = operation
        dest: dict[str, Any] = {}
        if destination_system:
            dest["system"] = str(destination_system)
        if destination_jurisdiction:
            dest["jurisdiction"] = str(destination_jurisdiction)
        if dest:
            arguments["destination"] = dest
        if consumer_jurisdiction:
            arguments["consumer_jurisdiction"] = str(consumer_jurisdiction)

        answer = self._tool("authorize_use", arguments, retry_without_transfer=True)
        if answer.get("_error"):
            return _error_payload(table_name, answer)

        state = answer.get("state")
        if state == "not_enough_published_state":
            data = {
                "decision": "UNKNOWN",
                "decision_id": None,
                "table_name": table_name,
                "operation": operation,
                "intended_use": intended_use,
                "reason_codes": [str(answer.get("reason_code") or "").upper()],
                "rationale": answer.get("message"),
                "matched_instructions": [],
                "conditions": [],
                "prohibitions": [],
                "obligations": [],
                "agent_action": {
                    "type": "ask_for_more_context",
                    "message": (answer.get("next_actions") or ["Publish governance for this asset."])[0],
                },
            }
            return _envelope("authorize", None, "ok", data)

        decision_value = answer.get("decision")
        label = _DECISION_LABELS.get(decision_value, "UNKNOWN")
        if state == "review_required":
            label = "REVIEW"
        conditions = answer.get("conditions") or []
        prohibitions = answer.get("prohibitions") or []
        obligations = answer.get("obligations") or []
        reason_codes = _authorize_reason_codes(answer, label)
        agent_action = _agent_action(label, answer)

        data = {
            "decision": label,
            "decision_id": answer.get("decision_id"),
            "table_name": table_name,
            "operation": operation,
            "intended_use": intended_use,
            "reason_codes": reason_codes,
            "rationale": answer.get("reason"),
            "matched_instructions": [_instruction_summary(i) for i in answer.get("instructions") or []],
            "conditions": [c.get("requirement") for c in conditions if c.get("requirement")],
            "prohibitions": [p.get("detail") for p in prohibitions if p.get("detail")],
            "obligations": [_obligation_summary(o) for o in obligations],
            "agent_action": agent_action,
        }
        if destination_system or destination_jurisdiction:
            data["destination"] = _drop_none(
                {"system": destination_system, "jurisdiction": destination_jurisdiction}
            )
        if consumer_jurisdiction:
            data["consumer_jurisdiction"] = consumer_jurisdiction
        return _envelope("authorize", answer.get("publication"), "ok", data)

    def validate_query_context(self, sql: str, **params: Any) -> dict[str, Any]:
        operation = str(params.get("operation") or "")
        intended_use = str(params.get("intended_use") or "")
        destination_system = params.get("destination_system")
        consumer_jurisdiction = params.get("consumer_jurisdiction")
        has_transfer_context = bool(destination_system or consumer_jurisdiction)
        scenario = _scenario_for(operation, intended_use, has_transfer_context)

        arguments: dict[str, Any] = {
            "sql": sql,
            "default_database": self.default_database,
            "default_schema": self.default_schema,
        }
        if scenario:
            arguments["scenario_key"] = scenario
        if operation:
            arguments["operation"] = operation
        if destination_system:
            arguments["destination"] = _drop_none(
                {
                    "system": destination_system,
                    "jurisdiction": params.get("destination_jurisdiction"),
                }
            )
        if consumer_jurisdiction:
            arguments["consumer_jurisdiction"] = str(consumer_jurisdiction)

        answer = self._tool("validate_query_context", arguments, retry_without_transfer=True)
        if answer.get("_error"):
            return _error_payload(sql[:80], answer)
        if answer.get("state") == "not_enough_published_state":
            return _not_enough_payload(sql[:80], answer)

        verdict = answer.get("verdict")
        label = {"pass": "ALLOW", "warn": "CONDITIONAL", "fail": "DENY"}.get(verdict, "REVIEW")
        findings = answer.get("findings") or []

        tables_accessed: list[str] = []
        columns_accessed: list[dict[str, Any]] = []
        sql_findings: list[dict[str, Any]] = []
        reason_codes: list[str] = []
        rationale = None
        for finding in findings:
            ref = finding.get("ref") or {}
            fqn = ".".join(
                str(ref.get(k) or "").upper() for k in ("database", "schema", "table")
            )
            tables_accessed.append(fqn)
            if finding.get("status") == "not_enough_published_state":
                sql_findings.append(
                    {
                        "severity": "warning",
                        "code": "NO_PUBLISHED_STATE",
                        "message": f"{fqn} has no published governance for this query.",
                    }
                )
                _append_unique(reason_codes, "NO_PUBLISHED_STATE")
                continue
            for instruction in finding.get("instructions") or []:
                scope = instruction.get("scope") or {}
                decision = instruction.get("decision")
                if scope.get("column"):
                    columns_accessed.append(
                        {
                            "table_name": fqn,
                            "column": str(scope["column"]).upper(),
                            "is_pii": decision in {"mask_full", "mask_partial"},
                            "effective_sensitivity": None,
                        }
                    )
                if decision in {"mask_full", "mask_partial"}:
                    sql_findings.append(
                        {
                            "severity": "warning",
                            "code": "PII_COLUMN_SELECTED",
                            "message": instruction.get("decision_reason"),
                        }
                    )
                    _append_unique(reason_codes, "MASKING_REQUIRED")
                    rationale = rationale or instruction.get("decision_reason")
                if decision == "deny":
                    sql_findings.append(
                        {
                            "severity": "error",
                            "code": _deny_code(instruction),
                            "message": instruction.get("decision_reason"),
                        }
                    )
                    _append_unique(reason_codes, _deny_code(instruction))
                    rationale = instruction.get("decision_reason")

        if not reason_codes:
            reason_codes = ["NO_RESTRICTED_COLUMNS_SELECTED"] if label == "ALLOW" else [f"{verdict}".upper()]
        agent_action = {
            "DENY": {"type": "block", "message": rationale or "This query violates published governance."},
            "CONDITIONAL": {
                "type": "revise_query",
                "message": rationale or "Mask or drop the flagged columns, then re-validate.",
            },
            "ALLOW": {"type": "proceed", "message": "No restricted columns or prohibited intents detected."},
        }.get(label, {"type": "review_controls", "message": "Review the validation findings."})

        data = {
            "validation_id": f"saas-validate-{uuid.uuid4().hex[:8]}",
            "sql": sql,
            "tables_accessed": tables_accessed,
            "extracted_columns": [c["column"] for c in columns_accessed],
            "columns_accessed": columns_accessed,
            "sql_findings": sql_findings,
            "decision": {
                "decision": label,
                "reason_codes": reason_codes,
                "rationale": rationale or agent_action["message"],
            },
            "agent_action": agent_action,
        }
        status = "warning" if label == "CONDITIONAL" else "ok"
        return _envelope("validate", answer.get("publication"), status, data)

    def explain_why(
        self,
        decision_id: str | None = None,
        validation_id: str | None = None,
    ) -> dict[str, Any]:
        if decision_id and _is_uuid(decision_id):
            answer = self._tool("explain_why", {"kind": "decision", "decision_id": decision_id})
            if not answer.get("_error") and answer.get("state") in {"answered", "review_required"}:
                record = answer.get("record") or {}
                scope = record.get("scope") or {}
                fqn = ".".join(
                    str(scope.get(k) or "").upper() for k in ("database", "schema", "table")
                )
                data = {
                    "decision_id": decision_id,
                    "decision": _DECISION_LABELS.get(record.get("decision"), "UNKNOWN"),
                    "table_name": fqn,
                    "rationale": answer.get("explanation"),
                    "matched_instructions": [_instruction_summary(record)],
                    "obligations": [],
                    "current": answer.get("current"),
                    "trace": {
                        "rules_evaluated": [record.get("instruction_key")],
                        "precedence_path": [record.get("primary_resolution_source")],
                    },
                }
                return _envelope("explain", answer.get("publication"), "ok", data)
        return {
            "request_id": f"saas-explain-{uuid.uuid4().hex[:8]}",
            "snapshot_id": "saas-not-found",
            "status": "error",
            "data": {
                "decision_id": decision_id,
                "validation_id": validation_id,
                "message": "The SaaS endpoint explains decision ids returned by authorize_use; "
                "validation records have no server-side explain surface.",
            },
        }

    # ------------------------------------------------------------------
    # Transport + shared helpers
    # ------------------------------------------------------------------

    def _tool(
        self,
        name: str,
        arguments: dict[str, Any],
        retry_without_transfer: bool = False,
    ) -> dict[str, Any]:
        """Call one canonical tool; return the typed payload or ``{_error}``."""
        self._ensure_initialized()
        response = self._request("tools/call", {"name": name, "arguments": arguments})
        result = response.get("result", {})
        if result.get("isError"):
            text = next(
                (item.get("text", "") for item in result.get("content") or [] if item.get("type") == "text"),
                "",
            )
            code = _error_code(text)
            if code == "invalid_parameters" and retry_without_transfer and (
                "destination" in arguments or "operation" in arguments or "consumer_jurisdiction" in arguments
            ):
                # Older servers without ADR-0009/0011 inputs: degrade to the
                # collapsed verdicts rather than failing the notebook run.
                stripped = {
                    k: v
                    for k, v in arguments.items()
                    if k not in {"destination", "operation", "consumer_jurisdiction"}
                }
                return self._tool(name, stripped)
            return {"_error": True, "error_code": code, "message": text}
        structured = result.get("structuredContent")
        if isinstance(structured, dict):
            return structured
        return _extract_mcp_payload(response)

    def _asset_ref(self, table_name: str, column: str | None = None) -> dict[str, str]:
        parts = [p for p in str(table_name).strip().split(".") if p]
        if len(parts) >= 3:
            database, schema, table = parts[-3], parts[-2], parts[-1]
        elif len(parts) == 2:
            database, (schema, table) = self.default_database, (parts[0], parts[1])
        else:
            database, schema, table = self.default_database, self.default_schema, parts[0]
        ref = {"database": database.lower(), "schema": schema.lower(), "table": table.lower()}
        if column:
            ref["column"] = column.lower()
        return ref

    def _governed_assets(self) -> list[dict[str, Any]]:
        if self._assets_cache is None:
            answer = self._tool("discover_context", {})
            if answer.get("_error") or answer.get("state") != "answered":
                self._assets_cache = []
            else:
                self._assets_cache = list(answer.get("assets") or [])
                self._publication = answer.get("publication")
        return self._assets_cache

    def _publication_hint(self) -> dict[str, Any] | None:
        self._governed_assets()
        return getattr(self, "_publication", None)

    def _governed_columns(self, asset: dict[str, str]) -> list[str]:
        columns = []
        for entry in self._governed_assets():
            ref = entry.get("ref") or {}
            if (
                ref.get("database") == asset["database"]
                and ref.get("schema") == asset["schema"]
                and ref.get("table") == asset["table"]
                and ref.get("column")
            ):
                columns.append(ref["column"])
        return sorted(set(columns))

    def _table_meaning(self, asset: dict[str, str]) -> dict[str, Any]:
        key = f"{asset['database']}.{asset['schema']}.{asset['table']}"
        if key not in self._meaning_cache:
            fact = self._tool(
                "inspect_data_meaning",
                {"ref": {k: asset[k] for k in ("database", "schema", "table")}},
            )
            self._meaning_cache[key] = {} if fact.get("_error") else fact
        return self._meaning_cache[key]

    def _column_meaning(self, asset: dict[str, str], column: str) -> dict[str, Any] | None:
        key = f"{asset['database']}.{asset['schema']}.{asset['table']}.{column}"
        if key not in self._meaning_cache:
            fact = self._tool(
                "inspect_data_meaning",
                {
                    "ref": {
                        "database": asset["database"],
                        "schema": asset["schema"],
                        "table": asset["table"],
                        "column": column,
                    }
                },
            )
            self._meaning_cache[key] = {} if fact.get("_error") else fact
        return self._meaning_cache[key] or None

    def _table_summary(self, asset: dict[str, Any]) -> dict[str, Any]:
        ref = asset.get("ref") or {}
        base = {
            "database": ref.get("database"),
            "schema": ref.get("schema"),
            "table": ref.get("table"),
        }
        rules = self._tool("get_decision_context", {"asset": base})
        decisions = rules.get("decisions") or [] if not rules.get("_error") else []
        meaning = self._table_meaning(base)
        business = rules.get("business_context") or {}
        masked_columns = {
            (d.get("scope") or {}).get("column")
            for d in decisions
            if d.get("instruction_family") == "masking" and (d.get("scope") or {}).get("column")
        }
        return {
            "full_table_name": ".".join(str(base[k]).upper() for k in ("database", "schema", "table")),
            "database_name": str(base["database"]).upper(),
            "schema_name": str(base["schema"]).upper(),
            "table_name": str(base["table"]).upper(),
            "sensitivity": (meaning.get("classification") or {}).get("sensitivity"),
            "enforcement_mode": "enforce"
            if any(d.get("enforcement_mode") == "enforce" for d in decisions)
            else "advisory",
            "policy_names": sorted(
                {(d.get("provenance") or {}).get("policy_name") or "?" for d in decisions}
            ),
            "tags": _control_tags(decisions),
            "compliance_frameworks": _control_tags(decisions),
            "has_pii": bool(meaning.get("pii")) or bool(masked_columns),
            "pii_column_count": len(masked_columns),
            "domain": business.get("domain"),
            "owner": business.get("owner"),
        }


# ----------------------------------------------------------------------
# Module helpers
# ----------------------------------------------------------------------


def _saas_endpoint_from_env() -> str:
    endpoint = os.getenv("METATATE_MCP_URL")
    if not endpoint:
        raise RuntimeError(
            "SaaS live mode requires METATATE_MCP_URL — the full MCP endpoint, "
            "e.g. https://<your-workspace-mcp-host>/mcp (Connect tab of the MCP module)."
        )
    return endpoint.rstrip("/")


def _scenario_for(operation: str, intended_use: str, has_transfer_context: bool) -> str | None:
    op = (operation or "").strip().lower()
    use = (intended_use or "").strip().lower()
    if use in _PROHIBITED_USES:
        return "purpose.prohibited_use"
    if op == "train" or use in _TRAINING_USES:
        return "ai.training"
    if op == "export" or use in {"external_sharing", "export"} or has_transfer_context:
        return "residency.cross_border_transfer"
    if use in _ALLOWED_USES:
        return "purpose.allowed_use"
    if use in _INFERENCE_USES:
        return "ai.inference"
    return None


def _authorize_reason_codes(answer: dict[str, Any], label: str) -> list[str]:
    codes: list[str] = []
    scenario = str(answer.get("scenario_key") or "")
    if label == "DENY":
        if scenario == "purpose.prohibited_use":
            codes.append("PROHIBITED_USE")
        elif scenario == "ai.training":
            codes.append("AI_TRAINING_BLOCKED")
        elif scenario == "residency.cross_border_transfer":
            codes.append("TRANSFER_DENIED")
        else:
            codes.append("USE_DENIED")
    if label == "CONDITIONAL" and scenario == "residency.cross_border_transfer":
        codes.append("TRANSFER_CONDITIONAL")
    for condition in answer.get("conditions") or []:
        code = _CONDITION_REASON_CODES.get(condition.get("kind"))
        if code:
            _append_unique(codes, code)
    if any(o.get("type") == "mask" for o in answer.get("obligations") or []):
        _append_unique(codes, "MASKING_REQUIRED")
    if label == "REVIEW":
        _append_unique(codes, str(answer.get("reason_code") or "REVIEW_REQUIRED").upper())
    if not codes:
        codes.append(f"{label}_BY_POLICY" if label in {"ALLOW", "DENY"} else label)
    return codes


def _agent_action(label: str, answer: dict[str, Any]) -> dict[str, Any]:
    next_actions = answer.get("next_actions") or []
    message = next_actions[0] if next_actions else answer.get("reason")
    if label == "DENY":
        return {"type": "block", "message": message or "This use is prohibited by published policy."}
    if label == "CONDITIONAL":
        return {
            "type": "proceed_with_controls",
            "message": message or "Satisfy the stated conditions, then proceed.",
        }
    if label == "ALLOW":
        return {"type": "proceed", "message": message or "This use is permitted by published policy."}
    return {"type": "ask_for_more_context", "message": message or "Review the governance answer."}


def _instruction_summary(instruction: dict[str, Any]) -> dict[str, Any]:
    provenance = instruction.get("provenance") or {}
    return {
        "id": instruction.get("instruction_key"),
        "decision_id": instruction.get("decision_id"),
        "title": _title(instruction.get("instruction_family")),
        "description": instruction.get("decision_reason"),
        "policy_name": provenance.get("policy_name"),
        "scenario": instruction.get("scenario_key"),
        "decision": instruction.get("decision"),
    }


def _obligation_summary(obligation: dict[str, Any]) -> str:
    if obligation.get("type") == "mask":
        method = f" ({obligation['method']})" if obligation.get("method") else ""
        return f"Mask {obligation.get('target')}{method}."
    if obligation.get("type") == "retain":
        return f"Apply the retention policy to {obligation.get('target')}."
    return json.dumps(obligation)


def _control_tags(decisions: list[dict[str, Any]]) -> list[str]:
    tags: list[str] = []
    families = {d.get("instruction_family") for d in decisions}
    scenarios = {(d.get("scenario_key"), d.get("decision")) for d in decisions}
    if "masking" in families or "classification" in families:
        _append_unique(tags, "privacy_sensitive")
    if ("ai.training", "deny") in scenarios:
        _append_unique(tags, "ai_training_blocked")
    if "transfer_governance" in families:
        _append_unique(tags, "restricted_transfer")
    if "retention" in families:
        _append_unique(tags, "retention_required")
    return tags


def _deny_code(instruction: dict[str, Any]) -> str:
    scenario = str(instruction.get("scenario_key") or "")
    if scenario == "purpose.prohibited_use":
        return "PROHIBITED_USE"
    if scenario == "ai.training":
        return "AI_TRAINING_BLOCKED"
    if scenario == "residency.cross_border_transfer":
        return "TRANSFER_DENIED"
    return "USE_DENIED"


def _envelope(
    tool: str,
    publication: dict[str, Any] | None,
    status: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    publication = publication or {}
    return {
        "request_id": f"saas-{tool}-{uuid.uuid4().hex[:8]}",
        "snapshot_id": publication.get("publication_id") or "saas-no-publication",
        "as_of": publication.get("published_at"),
        "status": status,
        "data": data,
    }


def _error_payload(subject: str, answer: dict[str, Any]) -> dict[str, Any]:
    code = answer.get("error_code") or "error"
    if code == "asset_not_found":
        message = "The SaaS catalog has no governed asset matching that reference."
    else:
        message = answer.get("message") or f"MCP tool error: {code}."
    return {
        "request_id": f"saas-error-{uuid.uuid4().hex[:8]}",
        "snapshot_id": "saas-error",
        "status": "error",
        "data": {"table_name": subject, "error_code": code, "message": message},
    }


def _not_enough_payload(subject: str, answer: dict[str, Any]) -> dict[str, Any]:
    return {
        "request_id": f"saas-not-enough-{uuid.uuid4().hex[:8]}",
        "snapshot_id": "saas-no-publication",
        "status": "error",
        "data": {
            "table_name": subject,
            "reason_code": answer.get("reason_code"),
            "message": answer.get("message")
            or "Not enough published governance state for this request.",
        },
    }


def _error_code(text: str) -> str:
    try:
        return (json.loads(text).get("error") or {}).get("code") or "error"
    except (ValueError, AttributeError):
        lowered = text.lower()
        for code in ("invalid_parameters", "asset_not_found", "not_supported", "rate_limited"):
            if code in lowered:
                return code
        return "error"


def _single_column(columns: Any) -> str | None:
    if isinstance(columns, (list, tuple)) and len(columns) == 1:
        return str(columns[0])
    return None


def _lower_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).strip().lower()


def _title(value: Any) -> str | None:
    if not value:
        return None
    return str(value).replace("_", " ").replace(".", " · ").title()


def _append_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False
