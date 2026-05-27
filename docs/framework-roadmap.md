# Framework Roadmap

The examples are use-case first. Frameworks are included when they make the Metatate decision-layer story clearer.

## Implemented Pack

- Snowflake Native App SQL tools
- Managed MCP live-mode client
- LangGraph-compatible governed SQL agent pattern
- Governed text-to-SQL agent pattern
- Agent red-team evaluation harness
- CI-style data and AI release gate
- Governed RAG and embedding ingestion gate
- Snowflake Cortex Agent custom-tool preflight pattern
- OpenAI Agents SDK-style tool guard pattern
- Human approval packet for conditional exports
- LlamaIndex governed retrieval pattern

## Validation Scope

All notebooks are executed in offline mode and live mode through the Snowflake-managed Metatate MCP server.

Framework runtime coverage is separate:

- LangGraph and LlamaIndex are optional imports in the notebook pack; when they are absent, the notebooks run equivalent Python callables.
- Cortex and OpenAI notebooks demonstrate tool-boundary patterns. They do not create deployed Cortex Agent objects or run OpenAI Agents SDK agent loops.
- A framework is not considered fully integrated until a runtime test proves the Metatate tool is invoked by that framework and the framework response changes based on the Metatate decision.

## Next Candidates

- Snowflake Cortex Agent REST object setup
- OpenAI Agents SDK runtime smoke test
- LlamaIndex FunctionAgent or AgentWorkflow runtime smoke test
- LangChain or CrewAI multi-agent handoff
- Pydantic AI
- dbt or Airflow policy gates beyond the notebook-first CI gate
- evaluation dashboards for red-team and CI gate history

## Later Exploration

- Claude Desktop or other conversational MCP clients
- multi-agent collaboration examples
- demo-only MCP endpoint for non-Snowflake playgrounds

Avoid adding empty framework folders. Each new example should prove a specific decision workflow before it introduces another framework.
