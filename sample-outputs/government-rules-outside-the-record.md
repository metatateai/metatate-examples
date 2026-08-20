# Expected Output — Government: The Rules Live Outside the Record

Captured from the executed offline notebook
(`notebooks/20_government_rules_outside_the_record.ipynb`). Offline mode
replays native Metatate Cloud responses recorded from the Customer 360 sample
publication. Program mechanics are illustrative by design.

The statute in force today answers, and its effective window is visible in the
cited instruction:

```text
today -> allow
  Benefits statute 2025        effective_until=2027-01-01T00:00:00+00:00
```

The as-of flip: the same call evaluated at a declared instant answers under
the successor statute, with the partition instant stated in the provenance:

```text
as of 2027-02-01 -> conditional
  requirement: Statute 2026 §4: determinations on or after 2027-01-01 must apply the modernized categorical checklist before any income test.
  validity_evaluated_at: 2027-02-01T00:00:00Z
```

Coverage that exists but is not yet in force is a typed answer, never a
fabricated decision:

```text
qualifying_conditions -> not_enough_published_state / not_currently_effective
```

Managed precedence — the categorical permit (critical band) outranks the
income test (high band) in the ranked instructions, while the income-test
condition still surfaces on the answer:

```text
determination -> conditional
  priority=3 Benefits categorical eligibility allow
  priority=2 Benefits income test             conditional
```

Unmanaged disagreement is surfaced, never silently resolved — both sources
cited:

```text
verification outreach -> review_required / conflicted_published_state
  conflicting: Benefits verification block
  conflicting: Benefits verification permit
```

The as-of instant flips the SQL verdict too:

```text
today          -> pass / answered
as of 2027     -> warn / answered
```

"Which rule version applied?" is answerable after the fact:

```text
decision  : conditional / answered
cited rows: 1
evaluated : 2026-07-30T00:00:00.000Z
```
