# Expected Output — Payments: Local Data Is Not the Source of Truth

Captured from the executed offline notebook
(`notebooks/18_payments_local_data_is_not_the_source_of_truth.ipynb`). Offline
mode replays native Metatate Cloud responses recorded from the Customer 360
sample publication.

The catalog itself states the distributed-truth premise — each settlement
column declares its own authority:

```text
local  : Local mirror of settlement progress; the authoritative settlement state lives in network_settlements.
network: Network-confirmed settlement state — the reconciliation source of truth.
```

The same fraud question answers differently by SOURCE, and each question has
its own authoritative table — the purpose × asset authority matrix, served as
organizational judgment:

```text
fraud / network          -> allow
fraud / local ledger     -> review_required
balance / local ledger   -> allow
fees / processor         -> allow
```

Analytics on the raw ledger is conditional on reconciliation, with the
authored requirement served verbatim:

```text
conditional -> Analytics on raw payment transactions is reliable only for reconciled rows (settlement_state = 'reconciled'); network_settlements is the reconciliation source of truth.
```

Query review catches the wrong source before it runs:

```text
fraud on local ledger -> warn / review_required
fraud on network      -> pass / answered
```
