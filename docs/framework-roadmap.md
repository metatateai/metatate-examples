# Framework Roadmap

The examples are use-case first. Frameworks are included when they make the Metatate decision-layer story clearer.

## Implemented Pack

- Metatate Cloud MCP live-mode client
- LangGraph-compatible governed SQL agent pattern
- LangGraph StateGraph runtime acceptance
- LangGraph governed SQL agent runtime with conditional routing
- Governed text-to-SQL agent pattern
- Agent red-team evaluation harness
- CI/CD data and AI policy gate package with acceptance coverage
- Governed RAG and embedding ingestion gate
- OpenAI Agents SDK-style tool guard pattern
- OpenAI Agents SDK FunctionTool runtime acceptance
- Human-in-the-loop exception workflow with acceptance coverage
- LlamaIndex governed retrieval pattern
- LlamaIndex FunctionTool runtime acceptance
- Governed agent arc — one brief end to end on a LangGraph runtime (rulebook-first
  planning, bounded SQL self-revision, exception-packet reuse, deny-reroute,
  explain chaining) with acceptance coverage pinning the exact decision sequence
  and an optional provider-neutral LLM planner for live mode

Snowflake Native App integrations (Cortex Agent preflight and hosted runtime
acceptance) are maintained in
[metatate-snowflake-examples](https://github.com/metatateai/metatate-snowflake-examples).

## Validation Scope

All notebooks are executed in offline mode and in live mode against a Metatate
Cloud workspace's MCP endpoint.

Framework runtime coverage is separate:

- LangGraph has a deterministic runtime acceptance script that invokes the real `StateGraph` runtime without calling an LLM.
- LangGraph also has a multi-node governed SQL agent runtime example that proves approve, revise, and block routing.
- OpenAI Agents SDK and LlamaIndex have deterministic runtime acceptance scripts that invoke the real framework `FunctionTool` object without calling an LLM.
- A framework is not considered fully integrated until a runtime test proves the Metatate tool is invoked by that framework and the framework response changes based on the Metatate decision.

## Next Candidates

- OpenAI Agents SDK model-loop smoke test
- LlamaIndex FunctionAgent or AgentWorkflow LLM-planning smoke test
- LangChain or CrewAI multi-agent handoff
- Pydantic AI
- dbt or Airflow adapters that generate change sets for the CI/CD policy gate
- evaluation dashboards for red-team and CI gate history

## Later Exploration

- Claude Desktop or other conversational MCP clients
- multi-agent collaboration examples

Avoid adding empty framework folders. Each new example should prove a specific decision workflow before it introduces another framework.
