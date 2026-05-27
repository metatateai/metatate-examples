# Framework Roadmap

The examples are use-case first. Frameworks are included when they make the Metatate decision-layer story clearer.

## Implemented Pack

- Snowflake Native App SQL tools
- Managed MCP live-mode client
- LangGraph governed SQL agent
- Governed text-to-SQL agent pattern
- Agent red-team evaluation harness
- CI-style data and AI release gate
- Governed RAG and embedding ingestion gate
- Snowflake Cortex Agent custom-tool preflight pattern
- OpenAI Agents SDK-style tool guard pattern
- Human approval packet for conditional exports
- LlamaIndex governed retrieval pattern

## Next Candidates

- Snowflake Cortex Agent REST object setup
- LangChain or CrewAI multi-agent handoff
- Pydantic AI
- dbt or Airflow policy gates beyond the notebook-first CI gate
- evaluation dashboards for red-team and CI gate history

## Later Exploration

- Claude Desktop or other conversational MCP clients
- multi-agent collaboration examples
- demo-only MCP endpoint for non-Snowflake playgrounds

Avoid adding empty framework folders. Each new example should prove a specific decision workflow before it introduces another framework.
