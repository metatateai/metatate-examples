# Governed RAG And Embedding Ingestion Gate Output

The ingestion gate evaluates two candidate sources before indexing:

- support ticket text for model training is denied
- aggregate customer ARR by region is allowed for analytics retrieval

The safe retrieval scope contains only the aggregate customer context. Support ticket text is blocked before it can be embedded or copied into a retrieval index.
