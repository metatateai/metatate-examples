# Expected Output — LlamaIndex Governed Retrieval Pattern

Captured from the executed OFFLINE notebook (`notebooks/10_llamaindex_governed_retrieval_pattern.ipynb`), which replays
recorded Metatate Cloud answers — live mode against a workspace serving the
AcmeCloud demo publication produces the same decisions.


```text
{'question': 'What is ARR by region?', 'retrieved': 'SELECT region, SUM(arr) FROM customers GROUP BY region', 'verdict': 'pass'}
{'question': 'Show EU customers and their email addresses.', 'retrieved': 'SELECT region, SUM(arr) FROM customers GROUP BY region', 'verdict': 'warn'}
{'question': 'Pull the marketing outreach list.', 'retrieved': None, 'verdict': 'fail'}
```
