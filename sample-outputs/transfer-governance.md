# Expected Output — Transfer Governance Before Export

Captured from the executed OFFLINE notebook (`notebooks/03_transfer_governance_before_export.ipynb`), which replays
recorded Metatate Cloud answers — live mode against a workspace serving the
AcmeCloud demo publication produces the same decisions.


```text
state:    answered
decision: conditional
reason:   Transfer to SALESFORCE (US) for consumer jurisdiction EU requires approval and anonymization and role PRIVACY_ADMIN (policy AcmeCloud transfer guardrails).
condition [anonymize_first]: This data must be anonymized before the transfer.
condition [approval_required]: Transfer to SALESFORCE (US) for consumer jurisdiction EU requires approval and anonymization and role PRIVACY_ADMIN (policy AcmeCloud transfer guardrails).
can_proceed_now: False
```

```text
ADS_PLATFORM        -> deny
EXTERNAL_LLM_VENDOR -> deny
```

```text
state:    answered
decision: conditional
reason:   No transfer rule matched to INTERNAL_WAREHOUSE (US) for consumer jurisdiction US; default effect conditional applies (policy AcmeCloud transfer guardrails).
condition [approval_required]: No transfer rule matched to INTERNAL_WAREHOUSE (US) for consumer jurisdiction US; default effect conditional applies (policy AcmeCloud transfer guardrails).
can_proceed_now: False
```

```text
current: True
Decision 'conditional' on acmecloud_demo.public.customers was produced by policy 'AcmeCloud transfer guardrails' v1 (instruction 'transfer_governance:spec.transferGovernance', scenario 'residency.cross_border_transfer', current publication): acme-transfer v1 transfer_governance:spec.transferGovernance → conditional on acmecloud_demo.public.customers
```
