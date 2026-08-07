# Expected Output — Governed RAG And Embedding Ingestion Gate

Captured from the executed OFFLINE notebook (`notebooks/07_governed_rag_embedding_ingestion_gate.ipynb`), which replays
recorded Metatate Cloud answers — live mode against a workspace serving the
Customer 360 demo publication produces the same decisions.


```text
SKIP support ticket bodies (fine-tune) -> deny
  customer-use-guardrails v1 ai_governance:spec.aiGovernance:training → deny on master.public.support_tickets
INGEST customer account summaries (LLM inference) -> allow
  customer-use-guardrails v1 ai_governance:spec.aiGovernance:inference → allow on master.public.customers
```

```text
retrieval query verdict: pass
```
