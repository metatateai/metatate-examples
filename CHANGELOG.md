# Changelog

## Unreleased

- Added Wave 1 agent-governance examples: governed text-to-SQL, red-team evaluation, and CI-style data/AI release gates.
- Added Wave 2 integration examples: governed RAG/embedding ingestion, Cortex-style tool preflight, OpenAI-style tool guards, approval packets, and LlamaIndex-style governed retrieval.
- Added offline Metatate fixtures for safe analytics, marketing denial, and AI training denial query validation.
- Changed live notebook mode to call the Snowflake-managed Metatate MCP server
  over HTTP with a role-restricted PAT.
- Removed the direct Snowflake SQL connector live path from examples.

## 0.1.0

- Rebuilt the examples repo around the AcmeCloud synthetic B2B SaaS dataset.
- Added offline Metatate response fixtures.
- Added live Snowflake fixture SQL aligned with the Native App MCP serving-table model.
- Added four starter notebooks:
  - setup: live or offline
  - decision-layer cookbook
  - governed SQL agent with LangGraph
  - transfer governance before export
