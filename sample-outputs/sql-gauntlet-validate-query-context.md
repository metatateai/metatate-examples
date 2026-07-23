# Expected Output — The SQL Gauntlet

Captured from the executed OFFLINE notebook (`notebooks/13_sql_gauntlet_validate_query_context.ipynb`), which replays
recorded Metatate Cloud answers — live mode against a workspace serving the
AcmeCloud demo publication produces the same decisions.


```text
customers JOIN subscriptions -> pass
  customers: evaluated (allow)
  subscriptions: evaluated (allow)
```

```text
SELECT *                    -> warn (both tokenized card columns participate)
SELECT payment_method_id    -> pass (no masked column referenced)
```

```text
CTE aggregate -> pass
findings: ['subscriptions']
```

```text
governed JOIN ungoverned -> warn
  customers: evaluated (None)
  legacy_customer_backup: not_enough_published_state (no_published_instruction_state)
```

```text
analytics intent -> pass
marketing intent -> fail (same SQL, different question)
```

```text
finance.invoices JOIN finance.revenue_ledger -> pass
  finance.invoices: allow
  finance.revenue_ledger: allow
```
