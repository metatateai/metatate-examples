"""The canonical offline case set — one source of truth for recording AND routing.

Each case is a real Metatate Cloud tool call (native typed-answer contract).
`scripts/record_offline_fixtures.py` replays every case against a live
workspace and commits the typed answers under
`sample-data/acmecloud/metatate-responses/`; `OfflineMetatateClient` routes
incoming calls back to those recordings by matching the same request shapes.

The authorize/validate ids mirror `sample-data/acmecloud/expected-decisions.yaml`
(the estate spec's behavior contract), so the offline pack demonstrates the
exact cases the product asserts against its engine-derived state.
"""

from __future__ import annotations

from typing import Any

DATABASE = "acmecloud_demo"
SCHEMA = "public"


def asset(table: str, column: str | None = None, schema: str = SCHEMA) -> dict[str, str]:
    ref: dict[str, str] = {"database": DATABASE, "schema": schema, "table": table}
    if column is not None:
        ref["column"] = column
    return ref


# Every case: {id, tool, arguments}. `explain_why` arguments may reference a
# previously recorded answer's decision_id as "@<case_id>.decision_id" — the
# recorder resolves it, and the offline client matches the recorded value.
CASES: list[dict[str, Any]] = [
    # ---- discovery / context / meaning / rules --------------------------------
    {"id": "discover_context", "tool": "discover_context", "arguments": {}},
    {
        "id": "decision_context_customers",
        "tool": "get_decision_context",
        "arguments": {"asset": asset("customers")},
    },
    {
        "id": "rules_customers",
        "tool": "inspect_governance_rules",
        "arguments": {"asset": asset("customers")},
    },
    {
        "id": "rules_customer_exports",
        "tool": "inspect_governance_rules",
        "arguments": {"asset": asset("customer_exports")},
    },
    {
        "id": "meaning_customers",
        "tool": "inspect_data_meaning",
        "arguments": {"ref": asset("customers")},
    },
    {
        "id": "meaning_customers_email",
        "tool": "inspect_data_meaning",
        "arguments": {"ref": asset("customers", "email")},
    },
    {
        "id": "meaning_support_tickets_ticket_text",
        "tool": "inspect_data_meaning",
        "arguments": {"ref": asset("support_tickets", "ticket_text")},
    },
    # ---- authorize (ids mirror expected-decisions.yaml) -----------------------
    {
        "id": "marketing-customers-deny",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("customers"),
            "scenario_key": "purpose.prohibited_use",
            "use": "launch a marketing campaign on customer contact data",
        },
    },
    {
        "id": "analytics-customers-allow",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("customers"),
            "scenario_key": "purpose.allowed_use",
            "use": "build a churn analytics dashboard",
        },
    },
    {
        "id": "support-tickets-allow",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("support_tickets"),
            "scenario_key": "purpose.allowed_use",
            "use": "triage open support tickets",
        },
    },
    {
        "id": "train-support-tickets-deny",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("support_tickets"),
            "scenario_key": "ai.training",
            "use": "fine-tune a support assistant on ticket text",
        },
    },
    {
        "id": "inference-customers-allow",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("customers"),
            "scenario_key": "ai.inference",
            "use": "summarize customer accounts with an LLM",
        },
    },
    {
        "id": "export-salesforce-conditional",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("customers"),
            "scenario_key": "residency.cross_border_transfer",
            "use": "sync approved customer fields to the CRM",
            "operation": "export",
            "destination": {"system": "SALESFORCE", "jurisdiction": "US"},
            "consumer_jurisdiction": "EU",
        },
    },
    {
        "id": "export-ads-platform-deny",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("customers"),
            "scenario_key": "residency.cross_border_transfer",
            "use": "send the customer batch to the advertising platform",
            "operation": "export",
            "destination": {"system": "ADS_PLATFORM", "jurisdiction": "US"},
            "consumer_jurisdiction": "US",
        },
    },
    {
        "id": "export-external-llm-deny",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("customers"),
            "scenario_key": "residency.cross_border_transfer",
            "use": "send the customer batch to an external LLM vendor",
            "operation": "export",
            "destination": {"system": "EXTERNAL_LLM_VENDOR", "jurisdiction": "US"},
            "consumer_jurisdiction": "US",
        },
    },
    {
        "id": "export-unmatched-destination-default",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("customer_exports"),
            "scenario_key": "residency.cross_border_transfer",
            "use": "stage the export batch in the internal warehouse",
            "operation": "export",
            "destination": {"system": "INTERNAL_WAREHOUSE", "jurisdiction": "US"},
            "consumer_jurisdiction": "US",
        },
    },
    # ---- estate v2: HR / PCI / ML / ungoverned --------------------------------
    {
        "id": "hr-read-role-gated-deny",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("employees"),
            "scenario_key": "access.read",
            "use": "browse employee records",
        },
    },
    {
        "id": "hr-name-custom-mask-review",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("employees", "full_name"),
            "scenario_key": "masking.display",
            "use": "display employee names in the people directory",
        },
    },
    {
        "id": "employee-public-sharing-deny",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("employees"),
            "scenario_key": "sharing.public",
            "use": "publish the org chart externally",
        },
    },
    {
        "id": "ml-training-features-allow",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("ml_feature_store"),
            "scenario_key": "ai.training",
            "use": "train the churn model on derived features",
        },
    },
    {
        "id": "ml-retrieval-context-allow",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("ml_feature_store"),
            "scenario_key": "ai.retrieval_context",
            "use": "feed churn features into agent retrieval context",
        },
    },
    {
        "id": "ml-embedding-storage-allow",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("ml_feature_store"),
            "scenario_key": "ai.embedding_storage",
            "use": "index feature vectors in the embedding store",
        },
    },
    {
        "id": "ml-vendor-transfer-deny",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("ml_feature_store"),
            "scenario_key": "ai.vendor_transfer",
            "use": "share churn features with an external AI vendor",
        },
    },
    {
        "id": "ml-automated-decisioning-deny",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("ml_feature_store"),
            "scenario_key": "ai.automated_decisioning",
            "use": "auto-cancel accounts from churn scores",
        },
    },
    {
        "id": "legacy-backup-ungoverned",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("legacy_customer_backup"),
            "scenario_key": "purpose.allowed_use",
            "use": "report on the legacy customer backup",
        },
    },
    {
        "id": "rules_employees",
        "tool": "inspect_governance_rules",
        "arguments": {"asset": asset("employees")},
    },
    {
        "id": "meaning_payment_methods_card_token",
        "tool": "inspect_data_meaning",
        "arguments": {"ref": asset("payment_methods", "card_token")},
    },
    {
        "id": "meaning_employees_work_email",
        "tool": "inspect_data_meaning",
        "arguments": {"ref": asset("employees", "work_email")},
    },
    {
        "id": "customer-360-internal-sharing-allow",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("subscriptions"),
            "scenario_key": "sharing.internal",
            "use": "share account health summaries with the success team",
        },
    },
    # ---- validate (ids mirror expected-decisions.yaml) ------------------------
    {
        "id": "safe-aggregate-pass",
        "tool": "validate_query_context",
        "arguments": {
            "sql": "SELECT region, SUM(arr) FROM customers GROUP BY region",
            "scenario_key": "purpose.allowed_use",
            "default_database": DATABASE,
            "default_schema": SCHEMA,
        },
    },
    {
        "id": "email-detail-warn",
        "tool": "validate_query_context",
        "arguments": {
            "sql": "SELECT customer_name, email FROM customers WHERE region = 'EU'",
            "scenario_key": "purpose.allowed_use",
            "default_database": DATABASE,
            "default_schema": SCHEMA,
        },
    },
    {
        "id": "marketing-detail-fail",
        "tool": "validate_query_context",
        "arguments": {
            "sql": "SELECT customer_name, email FROM customers WHERE marketing_consent = 'opted_in'",
            "scenario_key": "purpose.prohibited_use",
            "default_database": DATABASE,
            "default_schema": SCHEMA,
        },
    },
    {
        "id": "training-ticket-text-fail",
        "tool": "validate_query_context",
        "arguments": {
            "sql": "SELECT ticket_text FROM support_tickets",
            "scenario_key": "ai.training",
            "default_database": DATABASE,
            "default_schema": SCHEMA,
        },
    },
    {
        "id": "card-last4-detail-warn",
        "tool": "validate_query_context",
        "arguments": {
            "sql": "SELECT card_last4 FROM payment_methods",
            "scenario_key": "purpose.allowed_use",
            "default_database": DATABASE,
            "default_schema": SCHEMA,
        },
    },
    {
        "id": "employee-no-intent-fail",
        "tool": "validate_query_context",
        "arguments": {
            "sql": "SELECT salary FROM employees",
            "default_database": DATABASE,
            "default_schema": SCHEMA,
        },
    },
    {
        "id": "work-email-taxonomy-mask-warn",
        "tool": "validate_query_context",
        "arguments": {
            "sql": "SELECT work_email FROM employees",
            "scenario_key": "purpose.allowed_use",
            "default_database": DATABASE,
            "default_schema": SCHEMA,
        },
    },
    # ---- explain (chained from recorded authorize answers) --------------------
    {
        "id": "explain_analytics_decision",
        "tool": "explain_why",
        "arguments": {"kind": "decision", "decision_id": "@analytics-customers-allow.decision_id"},
    },
    {
        "id": "explain_salesforce_decision",
        "tool": "explain_why",
        "arguments": {"kind": "decision", "decision_id": "@export-salesforce-conditional.decision_id"},
    },
    # ---- estate v3 (APPENDED — case order drives the recorder's uuid ---------
    # numbering, so new cases always go at the end to keep every earlier
    # recording byte-identical).
    {
        "id": "conflict-prospect-outreach-review",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("marketing_prospects"),
            "scenario_key": "purpose.allowed_use",
            "use": "run outreach against the prospect list",
        },
    },
    {
        "id": "retention-subscriptions-retain",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("subscriptions"),
            "scenario_key": "retention.lifecycle",
            "use": "confirm how long subscription revenue facts must be kept",
        },
    },
    {
        "id": "employee-region-rows-conditional",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("employees"),
            "scenario_key": "access.row_filter",
            "use": "read employee rows for my region",
        },
    },
    {
        "id": "employee-gdpr-context-log-only",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("employees"),
            "scenario_key": "compliance.regulatory",
            "use": "review the GDPR context for employee records",
        },
    },
    {
        "id": "pci-card-token-mask-obligation",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("payment_methods", "card_token"),
            "scenario_key": "masking.display",
            "use": "display stored payment instruments in the support console",
        },
    },
    # Free-text front door: deliberately NO scenario_key on the next two.
    {
        "id": "freetext-training-deny",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("support_tickets"),
            "use": "fine-tune a model on this data",
        },
    },
    {
        "id": "freetext-ambiguous-unresolved",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("customers"),
            "use": "compare ai.training and ai.inference guidance for customer data",
        },
    },
    {
        "id": "finance-invoices-allowed-use",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("invoices", schema="finance"),
            "scenario_key": "purpose.allowed_use",
            "use": "prepare the quarterly revenue recognition report",
        },
    },
    {
        "id": "finance-ledger-public-sharing-deny",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("revenue_ledger", schema="finance"),
            "scenario_key": "sharing.public",
            "use": "publish ledger extracts on the public status page",
        },
    },
    {
        "id": "join-customers-subscriptions-pass",
        "tool": "validate_query_context",
        "arguments": {
            "sql": "SELECT c.region, SUM(s.arr) FROM customers c JOIN subscriptions s ON s.customer_id = c.customer_id GROUP BY c.region",
            "scenario_key": "purpose.allowed_use",
            "default_database": DATABASE,
            "default_schema": SCHEMA,
        },
    },
    {
        "id": "select-star-payment-methods-warn",
        "tool": "validate_query_context",
        "arguments": {
            "sql": "SELECT * FROM payment_methods LIMIT 5",
            "scenario_key": "purpose.allowed_use",
            "default_database": DATABASE,
            "default_schema": SCHEMA,
        },
    },
    {
        "id": "payment-id-only-pass",
        "tool": "validate_query_context",
        "arguments": {
            "sql": "SELECT payment_method_id FROM payment_methods",
            "scenario_key": "purpose.allowed_use",
            "default_database": DATABASE,
            "default_schema": SCHEMA,
        },
    },
    {
        "id": "cte-subscriptions-aggregate-pass",
        "tool": "validate_query_context",
        "arguments": {
            "sql": "WITH recent AS (SELECT customer_id, arr FROM subscriptions WHERE end_date IS NULL) SELECT customer_id, SUM(arr) FROM recent GROUP BY customer_id",
            "scenario_key": "purpose.allowed_use",
            "default_database": DATABASE,
            "default_schema": SCHEMA,
        },
    },
    {
        "id": "join-legacy-ungoverned-warn",
        "tool": "validate_query_context",
        "arguments": {
            "sql": "SELECT c.customer_name, l.exported_at FROM customers c JOIN legacy_customer_backup l ON l.customer_id = c.customer_id",
            "scenario_key": "purpose.allowed_use",
            "default_database": DATABASE,
            "default_schema": SCHEMA,
        },
    },
    {
        "id": "same-sql-analytics-intent-pass",
        "tool": "validate_query_context",
        "arguments": {
            "sql": "SELECT region, COUNT(*) FROM customers GROUP BY region",
            "scenario_key": "purpose.allowed_use",
            "default_database": DATABASE,
            "default_schema": SCHEMA,
        },
    },
    {
        "id": "same-sql-marketing-intent-fail",
        "tool": "validate_query_context",
        "arguments": {
            "sql": "SELECT region, COUNT(*) FROM customers GROUP BY region",
            "scenario_key": "purpose.prohibited_use",
            "default_database": DATABASE,
            "default_schema": SCHEMA,
        },
    },
    {
        "id": "finance-cross-schema-join-pass",
        "tool": "validate_query_context",
        "arguments": {
            "sql": "SELECT i.invoice_id, r.amount FROM finance.invoices i JOIN finance.revenue_ledger r ON r.invoice_id = i.invoice_id",
            "scenario_key": "purpose.allowed_use",
            "default_database": DATABASE,
            "default_schema": SCHEMA,
        },
    },
    # ---- governed agent arc (APPENDED — same uuid-stability rule as above):
    # the arc chains explain_why over the fine-tune deny and the governed
    # training reroute in addition to the two explains recorded earlier.
    {
        "id": "explain_train_deny_decision",
        "tool": "explain_why",
        "arguments": {"kind": "decision", "decision_id": "@train-support-tickets-deny.decision_id"},
    },
    {
        "id": "explain_ml_training_decision",
        "tool": "explain_why",
        "arguments": {"kind": "decision", "decision_id": "@ml-training-features-allow.decision_id"},
    },
]


def _norm(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _norm(v) for k, v in sorted(value.items()) if v is not None}
    if isinstance(value, str):
        return value.strip()
    return value


def signature(tool: str, arguments: dict[str, Any]) -> str:
    """A stable matching signature for (tool, arguments)."""
    import json

    return json.dumps({"tool": tool, "arguments": _norm(arguments)}, sort_keys=True)


def case_for(tool: str, arguments: dict[str, Any]) -> dict[str, Any] | None:
    """Find the canonical case matching a call (exact normalized match)."""
    wanted = signature(tool, arguments)
    for case in CASES:
        if case["tool"] != tool:
            continue
        if signature(tool, case["arguments"]) == wanted:
            return case
    return None
