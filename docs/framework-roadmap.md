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
- OpenAI Agents SDK FunctionTool runtime acceptance
- Human approval packet for conditional exports
- LlamaIndex governed retrieval pattern
- LlamaIndex FunctionTool runtime acceptance

## Validation Scope

All notebooks are executed in offline mode and live mode through the Snowflake-managed Metatate MCP server.

Framework runtime coverage is separate:

- LangGraph is an optional import in the notebook pack; when it is absent, the notebook runs equivalent Python callables.
- OpenAI Agents SDK and LlamaIndex have deterministic runtime acceptance scripts that invoke the real framework `FunctionTool` object without calling an LLM.
- Cortex currently demonstrates the custom-tool boundary pattern. It does not create a deployed Cortex Agent object yet.
- A framework is not considered fully integrated until a runtime test proves the Metatate tool is invoked by that framework and the framework response changes based on the Metatate decision.

## Next Candidates

- Snowflake Cortex Agent REST object setup
- OpenAI Agents SDK model-loop smoke test
- LlamaIndex FunctionAgent or AgentWorkflow LLM-planning smoke test
- LangChain or CrewAI multi-agent handoff
- Pydantic AI
- dbt or Airflow policy gates beyond the notebook-first CI gate
- evaluation dashboards for red-team and CI gate history

## Later Exploration

- Claude Desktop or other conversational MCP clients
- multi-agent collaboration examples
- demo-only MCP endpoint for non-Snowflake playgrounds

Avoid adding empty framework folders. Each new example should prove a specific decision workflow before it introduces another framework.
