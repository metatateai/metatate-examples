# Changelog

## Unreleased

- Added a live "saas" backend (`METATATE_MCP_BACKEND=saas`) that runs the full
  notebook pack and acceptance scripts against the Metatate SaaS
  cross-platform MCP endpoint with a workspace bearer token, including
  destination-aware export decisions and native `explain_why` chaining
  (see docs/live-mode-saas.md).
- Added a manual live SaaS MCP validation workflow
  (`.github/workflows/live-saas-mcp-validation.yml`).
- Added GitHub Actions offline CI for pull requests.
- Added a manual live managed MCP validation workflow for release candidates.
- Added release process documentation for offline CI, live MCP validation, and public tags.
- Added Wave 1 agent-governance examples: governed text-to-SQL, red-team evaluation, and CI/CD data/AI policy gates.
- Added Wave 2 integration examples: governed RAG/embedding ingestion, Cortex-style tool preflight, OpenAI-style tool guards, human exception workflows, and LlamaIndex-style governed retrieval.
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
