# Expected Output — Healthcare: One Person as Four Concepts

Captured from the executed offline notebook
(`notebooks/19_healthcare_one_person_four_concepts.ipynb`). Offline mode
replays native Metatate Cloud responses recorded from the Customer 360 sample
publication; the four contexts are four role-bound credentials, never caller
claims. Field-level specifics are illustrative, not clinical guidance.

The table-grain role gate — only the clinical role reads the full record on a
treatment basis; every other verified identity fails closed:

```text
clinical         -> allow
member_services  -> review_required
research         -> review_required
marketing        -> review_required
```

The column-grain contrast — the SAME clinical-notes column answers differently
by verified role:

```text
clinical        -> allow
member_services -> mask_full
```

The member context reads through its purpose, with its own consent basis:

```text
eligibility purpose -> allow
eligibility consent -> conditional verify coverage_status
```

The subject context is conditional twice over (de-identify, and verify the
recorded research authorization) — while model training is blocked outright:

```text
research use      -> conditional
research consent  -> conditional
model training    -> deny
```

The consumer context is denied on its purpose lane; its consent question is
conditional on the recorded opt-in; and the treatment purpose — which has NO
consent rule by design — fails closed rather than inventing an answer:

```text
marketing use      -> deny
marketing consent  -> conditional
treatment consent  -> review_required consent_context_required
```

The verified role flips the SQL verdict on the same query:

```text
clinical        -> pass / answered
member_services -> warn / answered
```

Every access shape is a durable, citable decision:

```text
decision  : conditional / answered
cited rows: 1
evaluated : 2026-07-30T00:00:00.000Z
```
