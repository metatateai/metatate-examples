# Framework Runtime Acceptance

The notebook pack proves the Metatate decision workflow in offline mode and against a live Metatate Cloud workspace. The framework runtime acceptance scripts add a narrower proof: the framework's actual tool object invokes the Metatate-backed callable and changes its output when Metatate returns a restrictive decision.

These checks are deterministic. They do not call an LLM and do not require an OpenAI API key.

## Install Dependencies

Use Python 3.10 or newer. The current framework runtime dependencies require it.

```bash
python3 --version  # confirm Python 3.10+
python3 -m venv .venv-framework
source .venv-framework/bin/activate
pip install -r requirements-framework.txt
```

## Run Offline

```bash
scripts/run_framework_runtime_acceptance.sh
```

Offline mode uses committed Metatate response fixtures.

## Run Live Through MCP

Live mode uses the same environment as the notebooks: a workspace serving the AcmeCloud demo publication, its MCP endpoint, and a workspace-issued access token.

```bash
METATATE_EXAMPLES_MODE=live \
METATATE_MCP_URL=https://<your-workspace-mcp-endpoint>/mcp \
METATATE_SAAS_MCP_TOKEN=mtt_... \
scripts/run_framework_runtime_acceptance.sh
```

See [live-mode-saas.md](live-mode-saas.md) for the full setup. Keep the token in your shell, never in `.env` or the repository.

## What Is Covered

- OpenAI Agents SDK: registers a Metatate-backed function tool on an `Agent`, invokes the SDK `FunctionTool` runtime, and asserts safe, revised, and blocked outcomes.
- LangGraph: builds and invokes a real `StateGraph` with a Metatate validation node and asserts safe, revised, and blocked outcomes.
- LangGraph governed SQL agent: invokes a multi-node `StateGraph` that plans SQL, validates with Metatate, and conditionally routes to approve, revise, or block.
- LlamaIndex: registers a Metatate-backed `FunctionTool`, invokes the LlamaIndex tool runtime, and asserts safe, revised, and blocked outcomes.

Each script verifies that:

- a safe analytics query is approved
- a query that selects direct identifiers is revised before use
- a direct-marketing request is blocked
- Metatate was called by the framework-wrapped tool

## What Is Not Covered

- OpenAI model loop execution. The OpenAI check proves the tool runtime, not model behavior.
- LLM-generated LangGraph planning. The LangGraph checks prove graph runtime invocation and deterministic conditional routing, not model planning quality.
- LlamaIndex agent LLM planning. The LlamaIndex check proves the tool runtime, not LLM tool selection.
- Snowflake Cortex Agent object runtime. That check lives in the
  [metatate-snowflake-examples](https://github.com/metatateai/metatate-snowflake-examples)
  repository.
