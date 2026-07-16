# Expected Output — CI Gate For Data And AI Changes

Captured from the executed OFFLINE notebook (`notebooks/06_ci_gate_for_data_ai_changes.ipynb`), which replays
recorded Metatate Cloud answers — live mode against a workspace serving the
AcmeCloud demo publication produces the same decisions.


```text
pass=1 needs_controls=2 fail=2
release_allowed: False
```

```text
chg-001: pass (pass)
  reason_codes: NO_RESTRICTED_USE_DETECTED
chg-002: needs_controls (warn)
  reason_codes: MASKING_REQUIRED
  controls: Mask or drop email before shipping this query.
chg-003: fail (fail)
  reason_codes: MASKING_REQUIRED, PROHIBITED_USE
  controls: Mask or drop email before shipping this query.
chg-004: needs_controls (conditional)
  reason_codes: TRANSFER_CONDITIONAL, ANONYMIZATION_REQUIRED, APPROVAL_REQUIRED
  controls: This data must be anonymized before the transfer.; Transfer to SALESFORCE (US) for consumer jurisdiction EU requires approval and anonymization and role PRIVACY_ADMIN (policy AcmeCloud transfer guardrails).
chg-005: fail (deny)
  reason_codes: AI_TRAINING_BLOCKED
```
