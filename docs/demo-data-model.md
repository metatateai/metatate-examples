# Customer 360 Demo Data Model

Customer 360 is a synthetic B2B SaaS company. The dataset is intentionally small so the examples stay readable, but it includes enough variety to demonstrate policy-aware agent behavior.

The machine-readable estate spec lives in `sample-data/customer-360/`
(`catalog.yaml`, thirty-seven policy DSL documents in `policies/`, and
`expected-decisions.yaml`); this page is the narrative companion.

## Tables

### `MASTER.PUBLIC.CUSTOMERS`

Customer master data used by revenue operations, support, analytics, and approved reporting workflows.

Key governance points:

- contains PII columns such as `CUSTOMER_NAME` and `EMAIL`
- supports analytics and reporting
- blocks direct marketing and advertising use in the base policy
- blocks model training
- has transfer rules for exports

### `MASTER.PUBLIC.SUBSCRIPTIONS`

Subscription and ARR facts used by revenue reporting and renewal planning.

Key governance points:

- commercially sensitive but not PII-heavy
- usable for finance analytics and internal reporting
- has retention context

### `PRODUCT.PUBLIC.PRODUCT_USAGE_EVENTS`

Product event data used for product analytics and support diagnostics.

Key governance points:

- includes device identifiers
- monitored for privacy-sensitive use
- usable for product analytics and support

### `PRODUCT.PUBLIC.SUPPORT_TICKETS`

Support text and case metadata.

Key governance points:

- ticket text can contain personal or confidential customer information
- support workflows and internal analytics are allowed
- model training is blocked

### `MASTER.PUBLIC.CUSTOMER_EXPORTS`

Prepared export table used to demonstrate outbound transfer governance.

Key governance points:

- contains prepared PII for outbound systems
- exports require approval and anonymization where required
- approved CRM export is conditional
- advertising platform export is denied

## Control Tags

The examples use customer-defined control tags instead of named legal articles:

- `privacy_sensitive`
- `restricted_transfer`
- `retention_required`
- `ai_training_blocked`
- `commercial_sensitive`

That keeps the examples focused on the decision layer rather than legal interpretation.

## Estate v2 additions

- `payment_methods` — PCI-scope payment instruments; `card_token`/`card_last4`
  classified `financial.credit_card` and tokenized at critical priority.
- `employees` — HR records: role-gated (`HR_ADMIN`/`PEOPLE_OPS` allowed,
  `PUBLIC` denied), regional row-level scoping, GDPR compliance + retention
  context, full masking on `salary`/`national_id`, and a monitored custom
  mask on `full_name` served as review-required.
- `ml_feature_store` — derived features with AI-lifecycle rules
  (training/retrieval/embedding permitted; vendor transfer and automated
  decisioning prohibited) and the `custom.churn_risk_score` type.
- `legacy_customer_backup` — cataloged but ungoverned on purpose: the
  `not_enough_published_state` answer and coverage-gap stories point here.
- Email masking is taxonomy-targeted (`pii.contact.email`): one policy, every
  email column, no per-column selector maintenance.

## Estate v3 additions

- `marketing_prospects` — the GOVERNANCE-DEBT corner: `prospect-outreach-permit`
  (Growth Marketing) permits the exact use `prospect-outreach-block` (Privacy
  Office) prohibits, at the same priority, on the same scenario — the block
  policy deliberately omits the prohibited-use scenario remap, so both rows
  land on `purpose.allowed_use` and the engine serves a typed
  `review_required(conflicted_published_state)` citing both sources. Isolated
  to this table so every other case stays clean; `contact_email` picks up the
  taxonomy email mask like any other classified email column.
- `finance.invoices` + `finance.revenue_ledger` — a SECOND SCHEMA under the
  same connector, governed by `finance-data-guardrails` (financial reporting
  and audit support permitted; external disclosure prohibited and remapped to
  `sharing.public`). Schema-qualified assets and cross-schema SQL answer
  exactly like `public` ones.
- The wider decision vocabulary is now served and recorded: an honest
  `retain` with a structured retain obligation (`retention.lifecycle` on
  subscriptions), a `conditional` row-access answer with a `role_restricted`
  condition (`access.row_filter` on employees), a `log_only` compliance
  context answer (`compliance.regulatory`), and a `mask_full` answer whose
  `mask` obligation names the tokenize method (`masking.display` on
  `payment_methods.card_token`).
- The free-text front door: `authorize_use` with no `scenario_key` maps
  plain-English uses deterministically ("fine-tune a model on this data" →
  `ai.training`), and text that names two canonical keys refuses with a typed
  `scenario_unresolved` instead of guessing.

## Vertical pack additions (2026-08)

Four industry scenario packs extend the estate without a second fabric:

- **AdTech** — `customers` gains three purpose-scoped consent bases beside the
  legacy `marketing_consent` boolean; `master.public.ad_audience_exports`
  carries the approved-partner activation transfer lane.
- **Payments** — `master.finance.payment_transactions`,
  `processor_settlements`, and `network_settlements` hold one transaction's
  distributed truth; the policies serve which source wins per question.
- **Healthcare** — `care.public.member_records` is one person as four
  concepts; access shapes follow four role-bound credentials, clinical
  columns are masked outside the clinical role, and consent bases are
  purpose-scoped. Field-level specifics are illustrative.
- **Government** — `benefits.public.applicants` and `qualifying_conditions`
  are governed by date-effective statute policies (the 2026 statute is
  published but not in force until 2027-01-01), band precedence, and the
  estate's SECOND sanctioned conflict pair (`verification_outreach`).
