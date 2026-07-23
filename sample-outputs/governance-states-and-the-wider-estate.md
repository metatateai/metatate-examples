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
sharing.internal on subscriptions -> allow
  cited via [collection]: AcmeCloud Customer 360 context
```

```text
card_last4 (analytics intent) -> warn (tokenized column referenced)
salary (NO stated intent)    -> fail (role-gated read applies to any SQL)
```

```text
marketing_prospects outreach -> review_required (conflicted_published_state)
  cited: AcmeCloud prospect outreach privacy block -> deny
  cited: AcmeCloud prospect outreach enablement -> allow
```

```text
state:    answered
decision: retain
reason:   acme-retention v1 retention:spec.retention → retain on acmecloud_demo.public.subscriptions
obligation [retain]: acmecloud_demo.public.subscriptions
can_proceed_now: False
```

```text
state:    answered
decision: conditional
reason:   acme-employee-rows v1 row_access:spec.rowFilter.rules → conditional on acmecloud_demo.public.employees
condition [role_restricted]: Row-level access is restricted to role(s): PEOPLE_OPS.
can_proceed_now: False
```

```text
compliance.regulatory -> log_only (regulatory context, not a permission)
state:    answered
decision: mask_full
reason:   acme-payment-protection v1 masking:spec.accessControl.masking → mask_full on acmecloud_demo.public.payment_methods.card_token
obligation [mask]: acmecloud_demo.public.payment_methods.card_token
can_proceed_now: False
```

```text
free text, no scenario_key -> answered / deny (mapped to ai.training)
ambiguous free text        -> not_enough_published_state (scenario_unresolved)
```

```text
finance.invoices reporting            -> allow
finance.revenue_ledger public sharing -> deny
```
