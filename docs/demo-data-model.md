# AcmeCloud Demo Data Model

AcmeCloud is a synthetic B2B SaaS company. The dataset is intentionally small so the examples stay readable, but it includes enough variety to demonstrate policy-aware agent behavior.

The machine-readable estate spec lives in `sample-data/acmecloud/`
(`catalog.yaml`, fifteen policy DSL documents in `policies/`, and
`expected-decisions.yaml`); this page is the narrative companion.

## Tables

### `ACMECLOUD_DEMO.PUBLIC.CUSTOMERS`

Customer master data used by revenue operations, support, analytics, and approved reporting workflows.

Key governance points:

- contains PII columns such as `CUSTOMER_NAME` and `EMAIL`
- supports analytics and reporting
- blocks direct marketing and advertising use in the base policy
- blocks model training
- has transfer rules for exports

### `ACMECLOUD_DEMO.PUBLIC.SUBSCRIPTIONS`

Subscription and ARR facts used by revenue reporting and renewal planning.

Key governance points:

- commercially sensitive but not PII-heavy
- usable for finance analytics and internal reporting
- has retention context

### `ACMECLOUD_DEMO.PUBLIC.PRODUCT_USAGE_EVENTS`

Product event data used for product analytics and support diagnostics.

Key governance points:

- includes device identifiers
- monitored for privacy-sensitive use
- usable for product analytics and support

### `ACMECLOUD_DEMO.PUBLIC.SUPPORT_TICKETS`

Support text and case metadata.

Key governance points:

- ticket text can contain personal or confidential customer information
- support workflows and internal analytics are allowed
- model training is blocked

### `ACMECLOUD_DEMO.PUBLIC.CUSTOMER_EXPORTS`

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
