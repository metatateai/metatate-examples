# Framework Roadmap

The examples are use-case first. Frameworks are included when they make the Metatate decision-layer story clearer.

## Implemented Pack

- Snowflake Native App SQL tools
- Managed MCP live-mode client
- LangGraph-compatible governed SQL agent pattern
- LangGraph StateGraph runtime acceptance
- Governed text-to-SQL agent pattern
- Agent red-team evaluation harness
- CI-style data and AI release gate
- Governed RAG and embedding ingestion gate
- Snowflake Cortex Agent custom-tool preflight pattern
- Snowflake Cortex Agent custom-tool live runtime acceptance
- OpenAI Agents SDK-style tool guard pattern
- OpenAI Agents SDK FunctionTool runtime acceptance
- Human approval packet for conditional exports
- LlamaIndex governed retrieval pattern
- LlamaIndex FunctionTool runtime acceptance

## Validation Scope

All notebooks are executed in offline mode and live mode through the Snowflake-managed Metatate MCP server.

Framework runtime coverage is separate:

- LangGraph has a deterministic runtime acceptance script that invokes the real `StateGraph` runtime without calling an LLM.
- OpenAI Agents SDK and LlamaIndex have deterministic runtime acceptance scripts that invoke the real framework `FunctionTool` object without calling an LLM.
- Cortex has a live runtime acceptance script that creates a Cortex Agent object, runs a server-side generic custom tool, and asserts the Metatate decision returned through the agent response.
- A framework is not considered fully integrated until a runtime test proves the Metatate tool is invoked by that framework and the framework response changes based on the Metatate decision.

## Next Candidates

- Snowflake Cortex Agent multi-case evaluation suite
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
