# Expected Output — Governed Text-to-SQL Agent

Captured from the executed OFFLINE notebook (`notebooks/04_governed_text_to_sql_agent.ipynb`), which replays
recorded Metatate Cloud answers — live mode against a workspace serving the
AcmeCloud demo publication produces the same decisions.


```text
How does ARR break down by region?
  verdict: pass  sql: SELECT region, SUM(arr) FROM customers GROUP BY region
List EU customers with their email addresses.
  verdict: warn  sql: SELECT region, SUM(arr) FROM customers GROUP BY region
Build an email list for the marketing campaign.
  verdict: fail  sql: None
```
