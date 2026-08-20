# Expected Output — AdTech: Consent as Three Permissions in One Field

Captured from the executed offline notebook
(`notebooks/17_adtech_consent_three_permissions_one_field.ipynb`). Offline mode
replays native Metatate Cloud responses recorded from the Customer 360 sample
publication.

The consent question answers per declared purpose: the same record yields three
different verification requirements, each naming the exact basis column the
agent must check. The condition is never satisfiable by caller assertion.

```text
measurement      -> conditional  verify consent_measurement
personalization  -> conditional  verify consent_personalization
activation       -> conditional  verify consent_activation
```

Consent recorded is not use permitted — personalization of the raw record
fails closed on the allowed-use lane and is denied outright on its
prohibited-use lane:

```text
allowed-use lane    -> review_required
prohibited-use lane -> deny
```

A consent question with no declared purpose fails closed with its typed
reason code:

```text
missing purpose -> review_required consent_context_required
```

Activation is a destination-aware transfer on its own governed table — an
approved demand-side partner is conditional on approval; everything else is
denied by default:

```text
approved partner -> conditional
unlisted partner -> deny
```

Byte-identical SQL, two verdicts — the declared purpose is the
decision-bearing input:

```text
measurement     -> pass / answered
personalization -> warn / review_required
```

Every determination is a durable, citable record:

```text
decision  : conditional / answered
cited rows: 1
evaluated : 2026-07-30T00:00:00.000Z
```
