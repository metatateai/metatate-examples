# Expected Output — Governance States And The Wider Estate

Captured from the executed OFFLINE notebook (`notebooks/12_governance_states_and_the_wider_estate.ipynb`), which replays
recorded Metatate Cloud answers — live mode against a workspace serving the
AcmeCloud demo publication produces the same decisions.


```text
legacy_customer_backup -> not_enough_published_state (no_published_instruction_state)
  next: No published instruction covers this asset and scenario — extend a policy to cover it and publish.
  next: Treat this use as review-required until published coverage exists.
```

```text
employees.full_name masking -> review_required (decision_requires_review)
```

```text
state:    answered
decision: deny
reason:   acme-employee-access v1 role_grant:spec.accessControl.deniedRoles:public:deny → deny on acmecloud_demo.public.employees
prohibition: acme-employee-access v1 role_grant:spec.accessControl.deniedRoles:public:deny → deny on acmecloud_demo.public.employees
can_proceed_now: False
  cited: role_grant:spec.accessControl.deniedRoles:public:deny -> deny
  cited: role_grant:spec.accessControl.allowedRoles:hr_admin:allow -> allow
  cited: role_grant:spec.accessControl.allowedRoles:people_ops:allow -> allow
```

```text
sharing.public -> deny
```

```text
raw tickets, ai.training                 -> deny
features, ai.training                    -> allow
features, ai.retrieval_context           -> allow
features, ai.embedding_storage           -> allow
features, ai.vendor_transfer             -> deny
features, ai.automated_decisioning       -> deny
```

```text
SELECT work_email -> warn
  mask_partial via [taxonomy] acme-email-masking v1 masking:spec.accessControl.masking → mask_partial on acmecloud_demo.public.employees.work_email
  allow via [selector] acme-employee-access v1 usage_guidance:spec.usage.permittedUses:permitted → allow on acmecloud_demo.public.employees
```

```text
card_last4 (analytics intent) -> warn (tokenized column referenced)
salary (NO stated intent)    -> fail (role-gated read applies to any SQL)
```
