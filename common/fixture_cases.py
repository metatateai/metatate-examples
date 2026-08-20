"""The canonical offline case set — one source of truth for recording AND routing.

Each case is a real Metatate Cloud tool call (native typed-answer contract).
`scripts/record_offline_fixtures.py` replays every case against a live
workspace and commits the typed answers under
`sample-data/customer-360/metatate-responses/`; `OfflineMetatateClient` routes
incoming calls back to those recordings by matching the same request shapes.

The authorize/validate ids mirror `sample-data/customer-360/expected-decisions.yaml`
(the estate spec's behavior contract), so the offline pack demonstrates the
exact cases the product asserts against its engine-derived state.
"""

from __future__ import annotations

from typing import Any

DATABASE = "master"
PRODUCT_DATABASE = "product"
CARE_DATABASE = "care"
BENEFITS_DATABASE = "benefits"
SCHEMA = "public"

DATABASE_BY_TABLE = {
    "product_usage_events": PRODUCT_DATABASE,
    "support_tickets": PRODUCT_DATABASE,
    "ml_feature_store": PRODUCT_DATABASE,
    "member_records": CARE_DATABASE,
    "applicants": BENEFITS_DATABASE,
    "qualifying_conditions": BENEFITS_DATABASE,
}

# One env var per bound role a case may carry. The recorder builds one live
# client per role present in CASES (fail-closed when an env is missing), and
# the live parity gate routes by the same map — a case's `bound_role` selects
# the CREDENTIAL, never a tool argument (roles ride verified tokens only).
ROLE_TOKEN_ENVS = {
    "agent": "METATATE_SAAS_MCP_AGENT_TOKEN",
    "clinical": "METATATE_SAAS_MCP_CLINICAL_TOKEN",
    "member_services": "METATATE_SAAS_MCP_MEMBER_SERVICES_TOKEN",
    "research": "METATATE_SAAS_MCP_RESEARCH_TOKEN",
    "marketing": "METATATE_SAAS_MCP_MARKETING_TOKEN",
}


def asset(table: str, column: str | None = None, schema: str = SCHEMA) -> dict[str, str]:
    ref: dict[str, str] = {
        "database": DATABASE_BY_TABLE.get(table, DATABASE),
        "schema": schema,
        "table": table,
    }
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
            "purpose_key": "analytics.reporting",
        },
    },
    {
        # PURPOSE-BLIND CONTROL. Identical asset, scenario and authored policy
        # to `analytics-customers-allow`, with the purpose deliberately OMITTED.
        # B3's redline: a purpose-blind call can never ride a permitted-uses
        # allow, so this must answer review_required and mint NO decision_id.
        # Nothing may chain an explain_why off it.
        "id": "analytics-customers-purpose-missing-review",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("customers"),
            "scenario_key": "purpose.allowed_use",
            "use": "build a churn analytics dashboard",
        },
    },
    {
        "id": "support-tickets-unmapped-policy-use-review",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("support_tickets"),
            "scenario_key": "purpose.allowed_use",
            "use": "triage open support tickets",
            "purpose_key": "operations.support",
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
            "purpose_key": "ai.inference",
            "use": "feed churn features into agent retrieval context",
        },
    },
    {
        "id": "ml-embedding-storage-review",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("ml_feature_store"),
            "scenario_key": "ai.embedding_storage",
            "purpose_key": "ai.inference",
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
            "purpose_key": "analytics.reporting",
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
            "purpose_key": "analytics.reporting",
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
            "default_database": PRODUCT_DATABASE,
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
            "purpose_key": "compliance.reporting",
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
            "purpose_key": "analytics.reporting",
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
            "purpose_key": "analytics.reporting",
        },
    },
    {
        "id": "join-legacy-ungoverned-warn",
        "tool": "validate_query_context",
        "arguments": {
            "sql": "SELECT c.customer_name, l.exported_at FROM customers c JOIN legacy_customer_backup l ON l.customer_id = c.customer_id",
            "scenario_key": "purpose.allowed_use",
            "purpose_key": "analytics.reporting",
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
            "purpose_key": "analytics.reporting",
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
            "purpose_key": "compliance.reporting",
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
    # ---- B3/B3T explanation union (APPENDED — preserve every prior uuid) -----
    {
        "id": "explain_analytics_authorization",
        "tool": "explain_why",
        "arguments": {
            "kind": "authorization",
            "authorization_id": "@analytics-customers-allow.authorization_id",
        },
    },
    {
        "id": "explain_safe_validation",
        "tool": "explain_why",
        "arguments": {
            "kind": "validation",
            "validation_id": "@safe-aggregate-pass.validation_id",
        },
    },
    # ---- Customer 360 purpose-bound access windows ---------------------------
    # Four explicit combinations make the policy matrix visible rather than
    # asking a reader to infer one dimension from another.
    {
        "id": "master-research-rolling-90-conditional",
        "tool": "authorize_use",
        "bound_role": "agent",
        "arguments": {
            "asset": asset("customers"),
            "scenario_key": "access.read",
            "use": "research recent customer behavior",
            "purpose_key": "research.general",
        },
    },
    {
        "id": "master-commercial-rolling-30-conditional",
        "tool": "authorize_use",
        "bound_role": "agent",
        "arguments": {
            "asset": asset("customers"),
            "scenario_key": "access.read",
            "use": "prepare a commercial customer analysis",
            "purpose_key": "commercial.general",
        },
    },
    {
        "id": "product-research-as-of-90-conditional",
        "tool": "authorize_use",
        "bound_role": "agent",
        "arguments": {
            "asset": asset("product_usage_events"),
            "scenario_key": "access.read",
            "use": "reproduce product research as of a fixed date",
            "purpose_key": "research.general",
            "data_access_context": {"as_of": "2026-08-01T00:00:00Z"},
        },
    },
    {
        "id": "product-commercial-as-of-30-conditional",
        "tool": "authorize_use",
        "bound_role": "agent",
        "arguments": {
            "asset": asset("product_usage_events"),
            "scenario_key": "access.read",
            "use": "reproduce a commercial product analysis as of a fixed date",
            "purpose_key": "commercial.general",
            "data_access_context": {"as_of": "2026-08-01T00:00:00Z"},
        },
    },
    {
        "id": "master-access-purpose-missing-review",
        "tool": "authorize_use",
        "bound_role": "agent",
        "arguments": {
            "asset": asset("customers"),
            "scenario_key": "access.read",
            "use": "read recent customer records",
        },
    },
    {
        "id": "product-access-as-of-missing-review",
        "tool": "authorize_use",
        "bound_role": "agent",
        "arguments": {
            "asset": asset("product_usage_events"),
            "scenario_key": "access.read",
            "use": "read product events for research",
            "purpose_key": "research.general",
        },
    },
    {
        "id": "master-research-rolling-90-pass",
        "tool": "validate_query_context",
        "bound_role": "agent",
        "arguments": {
            "sql": "SELECT customer_id, account_status FROM master.public.customers WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '90 days' AND created_at <= CURRENT_TIMESTAMP",
            "scenario_key": "access.read",
            "default_database": DATABASE,
            "default_schema": SCHEMA,
            "purpose_key": "research.general",
        },
    },
    {
        "id": "master-commercial-rolling-30-pass",
        "tool": "validate_query_context",
        "bound_role": "agent",
        "arguments": {
            "sql": "SELECT customer_id, account_status FROM master.public.customers WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days' AND created_at <= CURRENT_TIMESTAMP",
            "scenario_key": "access.read",
            "default_database": DATABASE,
            "default_schema": SCHEMA,
            "purpose_key": "commercial.general",
        },
    },
    {
        "id": "master-commercial-rolling-90-fail",
        "tool": "validate_query_context",
        "bound_role": "agent",
        "arguments": {
            "sql": "SELECT customer_id, account_status FROM master.public.customers WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '90 days' AND created_at <= CURRENT_TIMESTAMP",
            "scenario_key": "access.read",
            "default_database": DATABASE,
            "default_schema": SCHEMA,
            "purpose_key": "commercial.general",
        },
    },
    {
        "id": "product-research-as-of-90-pass",
        "tool": "validate_query_context",
        "bound_role": "agent",
        "arguments": {
            "sql": "SELECT customer_id, event_name FROM product.public.product_usage_events WHERE occurred_at >= TIMESTAMPTZ '2026-05-03T00:00:00Z' AND occurred_at <= TIMESTAMPTZ '2026-08-01T00:00:00Z'",
            "scenario_key": "access.read",
            "default_database": PRODUCT_DATABASE,
            "default_schema": SCHEMA,
            "purpose_key": "research.general",
            "data_access_context": {"as_of": "2026-08-01T00:00:00Z"},
        },
    },
    {
        "id": "product-commercial-as-of-30-pass",
        "tool": "validate_query_context",
        "bound_role": "agent",
        "arguments": {
            "sql": "SELECT customer_id, event_name FROM product.public.product_usage_events WHERE occurred_at >= TIMESTAMPTZ '2026-07-02T00:00:00Z' AND occurred_at <= TIMESTAMPTZ '2026-08-01T00:00:00Z'",
            "scenario_key": "access.read",
            "default_database": PRODUCT_DATABASE,
            "default_schema": SCHEMA,
            "purpose_key": "commercial.general",
            "data_access_context": {"as_of": "2026-08-01T00:00:00Z"},
        },
    },
    {
        "id": "product-commercial-as-of-90-fail",
        "tool": "validate_query_context",
        "bound_role": "agent",
        "arguments": {
            "sql": "SELECT customer_id, event_name FROM product.public.product_usage_events WHERE occurred_at >= TIMESTAMPTZ '2026-05-03T00:00:00Z' AND occurred_at <= TIMESTAMPTZ '2026-08-01T00:00:00Z'",
            "scenario_key": "access.read",
            "default_database": PRODUCT_DATABASE,
            "default_schema": SCHEMA,
            "purpose_key": "commercial.general",
            "data_access_context": {"as_of": "2026-08-01T00:00:00Z"},
        },
    },
    # ---- vertical packs (APPENDED — same uuid-stability rule as above). -------
    # AdTech: consent as three permissions in one field.
    {
        "id": "adtech-personalization-allowed-use-review",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("customers"),
            "scenario_key": "purpose.allowed_use",
            "use": "personalize offers from customer records",
            "purpose_key": "marketing.personalization",
        },
    },
    {
        "id": "adtech-personalization-prohibited-deny",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("customers"),
            "scenario_key": "purpose.prohibited_use",
            "use": "personalize offers from customer records",
            "purpose_key": "marketing.personalization",
        },
    },
    {
        "id": "adtech-consent-measurement-conditional",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("customers"),
            "scenario_key": "consent.required",
            "use": "measure campaign reach across customers",
            "purpose_key": "analytics.reporting",
        },
    },
    {
        "id": "adtech-consent-personalization-conditional",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("customers"),
            "scenario_key": "consent.required",
            "use": "personalize offers from customer records",
            "purpose_key": "marketing.personalization",
        },
    },
    {
        "id": "adtech-consent-activation-conditional",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("customers"),
            "scenario_key": "consent.required",
            "use": "activate an audience with a demand-side partner",
            "purpose_key": "sharing.third_party",
        },
    },
    {
        "id": "adtech-consent-purpose-missing-review",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("customers"),
            "scenario_key": "consent.required",
            "use": "use customer records for an advertising workflow",
        },
    },
    {
        "id": "adtech-export-approved-dsp-conditional",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("ad_audience_exports"),
            "scenario_key": "residency.cross_border_transfer",
            "use": "activate the consented audience with an approved partner",
            "operation": "export",
            "destination": {"system": "APPROVED_DSP_A"},
        },
    },
    {
        "id": "adtech-export-unlisted-dsp-deny",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("ad_audience_exports"),
            "scenario_key": "residency.cross_border_transfer",
            "use": "activate the audience with an unlisted platform",
            "operation": "export",
            "destination": {"system": "UNLISTED_DSP"},
        },
    },
    {
        "id": "adtech-consent-sql-analytics-pass",
        "tool": "validate_query_context",
        "arguments": {
            "sql": "SELECT customer_id, consent_measurement, consent_personalization, consent_activation FROM customers",
            "scenario_key": "purpose.allowed_use",
            "default_database": DATABASE,
            "default_schema": SCHEMA,
            "purpose_key": "analytics.reporting",
        },
    },
    {
        "id": "adtech-consent-sql-personalization-warn",
        "tool": "validate_query_context",
        "arguments": {
            "sql": "SELECT customer_id, consent_measurement, consent_personalization, consent_activation FROM customers",
            "scenario_key": "purpose.allowed_use",
            "default_database": DATABASE,
            "default_schema": SCHEMA,
            "purpose_key": "marketing.personalization",
        },
    },
    {
        "id": "explain_adtech_consent_authorization",
        "tool": "explain_why",
        "arguments": {
            "kind": "authorization",
            "authorization_id": "@adtech-consent-measurement-conditional.authorization_id",
        },
    },
    # Payments: local data isn't the source of truth.
    {
        "id": "meaning_payment_transactions_settlement_state",
        "tool": "inspect_data_meaning",
        "arguments": {"ref": asset("payment_transactions", "settlement_state", schema="finance")},
    },
    {
        "id": "meaning_network_settlements_settlement_state",
        "tool": "inspect_data_meaning",
        "arguments": {"ref": asset("network_settlements", "settlement_state", schema="finance")},
    },
    {
        "id": "pay-fraud-network-allow",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("network_settlements", schema="finance"),
            "scenario_key": "purpose.allowed_use",
            "use": "investigate suspected fraud on a settled transaction",
            "purpose_key": "fraud.detection",
        },
    },
    {
        "id": "pay-fraud-transactions-review",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("payment_transactions", schema="finance"),
            "scenario_key": "purpose.allowed_use",
            "use": "investigate suspected fraud on a settled transaction",
            "purpose_key": "fraud.detection",
        },
    },
    {
        "id": "pay-ops-transactions-allow",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("payment_transactions", schema="finance"),
            "scenario_key": "purpose.allowed_use",
            "use": "answer a customer-facing balance question",
            "purpose_key": "operations.support",
        },
    },
    {
        "id": "pay-audit-processor-allow",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("processor_settlements", schema="finance"),
            "scenario_key": "purpose.allowed_use",
            "use": "reconcile processor fees for the audit trail",
            "purpose_key": "compliance.audit",
        },
    },
    {
        "id": "pay-analytics-reconciled-conditional",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("payment_transactions", schema="finance"),
            "scenario_key": "quality.reliability",
            "use": "report revenue analytics over payment transactions",
            "purpose_key": "analytics.reporting",
        },
    },
    {
        "id": "pay-fraud-wrong-source-warn",
        "tool": "validate_query_context",
        "arguments": {
            "sql": "SELECT transaction_id, settlement_state FROM master.finance.payment_transactions WHERE settlement_state <> 'reconciled'",
            "scenario_key": "purpose.allowed_use",
            "default_database": DATABASE,
            "default_schema": SCHEMA,
            "purpose_key": "fraud.detection",
        },
    },
    {
        "id": "pay-fraud-right-source-pass",
        "tool": "validate_query_context",
        "arguments": {
            "sql": "SELECT transaction_id, settlement_state FROM master.finance.network_settlements",
            "scenario_key": "purpose.allowed_use",
            "default_database": DATABASE,
            "default_schema": SCHEMA,
            "purpose_key": "fraud.detection",
        },
    },
    {
        "id": "pay-reconciled-quality-warn",
        "tool": "validate_query_context",
        "arguments": {
            "sql": "SELECT transaction_id, amount FROM master.finance.payment_transactions",
            "scenario_key": "quality.reliability",
            "default_database": DATABASE,
            "default_schema": SCHEMA,
            "purpose_key": "analytics.reporting",
        },
    },
    # Healthcare: one person as four concepts (per-role credentials).
    {
        "id": "care-clinical-read-allow",
        "tool": "authorize_use",
        "bound_role": "clinical",
        "arguments": {
            "asset": asset("member_records"),
            "scenario_key": "access.read",
            "use": "read the full member record on a treatment basis",
        },
    },
    {
        "id": "care-member-services-read-review",
        "tool": "authorize_use",
        "bound_role": "member_services",
        "arguments": {
            "asset": asset("member_records"),
            "scenario_key": "access.read",
            "use": "read the full member record for coverage work",
        },
    },
    {
        "id": "care-research-read-review",
        "tool": "authorize_use",
        "bound_role": "research",
        "arguments": {
            "asset": asset("member_records"),
            "scenario_key": "access.read",
            "use": "read member records for a research cohort",
        },
    },
    {
        "id": "care-marketing-read-review",
        "tool": "authorize_use",
        "bound_role": "marketing",
        "arguments": {
            "asset": asset("member_records"),
            "scenario_key": "access.read",
            "use": "read member records for outreach targeting",
        },
    },
    {
        "id": "care-notes-clinical-allow",
        "tool": "authorize_use",
        "bound_role": "clinical",
        "arguments": {
            "asset": asset("member_records", "clinical_notes"),
            "scenario_key": "masking.display",
            "use": "display clinician notes during treatment",
        },
    },
    {
        "id": "care-notes-member-services-mask",
        "tool": "authorize_use",
        "bound_role": "member_services",
        "arguments": {
            "asset": asset("member_records", "clinical_notes"),
            "scenario_key": "masking.display",
            "use": "display the member record in a coverage tool",
        },
    },
    {
        "id": "care-eligibility-allow",
        "tool": "authorize_use",
        "bound_role": "member_services",
        "arguments": {
            "asset": asset("member_records"),
            "scenario_key": "purpose.allowed_use",
            "use": "check coverage eligibility for a claim",
            "purpose_key": "care.eligibility",
        },
    },
    {
        "id": "care-research-anonymize-conditional",
        "tool": "authorize_use",
        "bound_role": "research",
        "arguments": {
            "asset": asset("member_records"),
            "scenario_key": "protection.anonymization",
            "use": "analyze member outcomes for a research study",
            "purpose_key": "research.general",
        },
    },
    {
        "id": "care-training-deny",
        "tool": "authorize_use",
        "bound_role": "research",
        "arguments": {
            "asset": asset("member_records"),
            "scenario_key": "ai.training",
            "use": "train a model on member records",
        },
    },
    {
        "id": "care-marketing-outreach-deny",
        "tool": "authorize_use",
        "bound_role": "marketing",
        "arguments": {
            "asset": asset("member_records"),
            "scenario_key": "purpose.prohibited_use",
            "use": "market wellness products to members",
            "purpose_key": "marketing.advertising",
        },
    },
    {
        "id": "care-consent-eligibility-conditional",
        "tool": "authorize_use",
        "bound_role": "member_services",
        "arguments": {
            "asset": asset("member_records"),
            "scenario_key": "consent.required",
            "use": "check coverage eligibility for a claim",
            "purpose_key": "care.eligibility",
        },
    },
    {
        "id": "care-consent-research-conditional",
        "tool": "authorize_use",
        "bound_role": "research",
        "arguments": {
            "asset": asset("member_records"),
            "scenario_key": "consent.required",
            "use": "analyze member outcomes for a research study",
            "purpose_key": "research.general",
        },
    },
    {
        "id": "care-consent-marketing-conditional",
        "tool": "authorize_use",
        "bound_role": "marketing",
        "arguments": {
            "asset": asset("member_records"),
            "scenario_key": "consent.required",
            "use": "market wellness products to members",
            "purpose_key": "marketing.advertising",
        },
    },
    {
        "id": "care-consent-treatment-purpose-unruled-review",
        "tool": "authorize_use",
        "bound_role": "clinical",
        "arguments": {
            "asset": asset("member_records"),
            "scenario_key": "consent.required",
            "use": "treat the member in a clinical encounter",
            "purpose_key": "care.treatment",
        },
    },
    {
        "id": "care-notes-sql-clinical-pass",
        "tool": "validate_query_context",
        "bound_role": "clinical",
        "arguments": {
            "sql": "SELECT member_id, clinical_notes FROM care.public.member_records",
            "scenario_key": "purpose.allowed_use",
            "default_database": DATABASE,
            "default_schema": SCHEMA,
            "purpose_key": "care.treatment",
        },
    },
    {
        "id": "care-notes-sql-member-services-warn",
        "tool": "validate_query_context",
        "bound_role": "member_services",
        "arguments": {
            "sql": "SELECT member_id, clinical_notes FROM care.public.member_records",
            "scenario_key": "purpose.allowed_use",
            "default_database": DATABASE,
            "default_schema": SCHEMA,
            "purpose_key": "care.treatment",
        },
    },
    {
        "id": "explain_care_anonymize_authorization",
        "tool": "explain_why",
        "arguments": {
            "kind": "authorization",
            "authorization_id": "@care-research-anonymize-conditional.authorization_id",
        },
    },
    # Government: the fields are there, the program rules aren't.
    {
        "id": "gov-determination-statute-2025-allow",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("applicants"),
            "scenario_key": "compliance.regulatory",
            "use": "determine benefits eligibility for an application",
            "purpose_key": "benefits.determination",
        },
    },
    {
        "id": "gov-statute-as-of-2027-conditional",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("applicants"),
            "scenario_key": "compliance.regulatory",
            "use": "determine benefits eligibility for an application",
            "purpose_key": "benefits.determination",
            "data_access_context": {"as_of": "2027-02-01T00:00:00Z"},
        },
    },
    {
        "id": "gov-qualifying-conditions-not-yet-effective",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("qualifying_conditions"),
            "scenario_key": "compliance.regulatory",
            "use": "apply the modernized categorical checklist",
            "purpose_key": "benefits.determination",
        },
    },
    {
        "id": "gov-categorical-precedence-conditional",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("applicants"),
            "scenario_key": "ai.automated_decisioning",
            "use": "run an automated benefits determination",
            "purpose_key": "benefits.determination",
        },
    },
    {
        "id": "gov-conflict-verification-review",
        "tool": "authorize_use",
        "arguments": {
            "asset": asset("applicants"),
            "scenario_key": "purpose.allowed_use",
            "use": "run verification outreach against applicants",
        },
    },
    {
        "id": "gov-determination-2025-pass",
        "tool": "validate_query_context",
        "arguments": {
            "sql": "SELECT applicant_id, categorical_flag FROM benefits.public.applicants",
            "scenario_key": "compliance.regulatory",
            "default_database": DATABASE,
            "default_schema": SCHEMA,
            "purpose_key": "benefits.determination",
        },
    },
    {
        "id": "gov-determination-as-of-2027-warn",
        "tool": "validate_query_context",
        "arguments": {
            "sql": "SELECT applicant_id, categorical_flag FROM benefits.public.applicants",
            "scenario_key": "compliance.regulatory",
            "default_database": DATABASE,
            "default_schema": SCHEMA,
            "purpose_key": "benefits.determination",
            "data_access_context": {"as_of": "2027-02-01T00:00:00Z"},
        },
    },
    {
        "id": "explain_gov_statute_authorization",
        "tool": "explain_why",
        "arguments": {
            "kind": "authorization",
            "authorization_id": "@gov-statute-as-of-2027-conditional.authorization_id",
        },
    },
]


def _norm(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _norm(v) for k, v in sorted(value.items()) if v is not None}
    if isinstance(value, str):
        return value.strip()
    return value


def signature(tool: str, arguments: dict[str, Any], bound_role: str | None = None) -> str:
    """A stable matching signature for (tool, arguments, credential role).

    `bound_role` is part of the signature because the CREDENTIAL selects the
    answer: two byte-identical calls under different role-bound tokens are
    different questions with different recordings (the healthcare role-flip
    SQL pair). `None` keeps every pre-existing identity-neutral signature
    byte-identical.
    """
    import json

    payload: dict[str, Any] = {"tool": tool, "arguments": _norm(arguments)}
    if bound_role is not None:
        payload["bound_role"] = bound_role
    return json.dumps(payload, sort_keys=True)


def case_for(
    tool: str, arguments: dict[str, Any], bound_role: str | None = None
) -> dict[str, Any] | None:
    """Find the canonical case matching a call (exact normalized match).

    The caller's credential role must equal the case's `bound_role` — a
    role-bound case is unreachable from an identity-neutral client, exactly
    like live (the token carries the role, never the arguments).
    """
    wanted = signature(tool, arguments, bound_role)
    for case in CASES:
        if case["tool"] != tool:
            continue
        if signature(tool, case["arguments"], case.get("bound_role")) == wanted:
            return case
    return None
