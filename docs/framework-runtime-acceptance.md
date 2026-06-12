# Framework Runtime Acceptance

The notebook pack proves the Metatate decision workflow in offline mode and through the Snowflake-managed MCP server. The framework runtime acceptance scripts add a narrower proof: the framework's actual tool object invokes the Metatate-backed callable and changes its output when Metatate returns a restrictive decision.

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

Live mode uses the same environment as the notebooks. Seed the AcmeCloud fixture, create a role-restricted PAT for the dedicated service user, and export the PAT before running the framework checks.

```bash
export METATATE_EXAMPLES_PAT="$(cat /private/tmp/metatate_examples_mcp_pat)"

METATATE_EXAMPLES_MODE=live \
METATATE_MCP_URL=https://<account-url>/api/v2/databases/METATATE_APP/schemas/CORE/mcp-servers/METATATE_MCP \
SNOWFLAKE_ROLE=NAC \
METATATE_MCP_PAT_ENV=METATATE_EXAMPLES_PAT \
scripts/run_framework_runtime_acceptance.sh
```

Use the PAT setup in [live-mode.md](live-mode.md). Do not attach notebook or examples network policies to a human/admin user.

## What Is Covered

- OpenAI Agents SDK: registers a Metatate-backed function tool on an `Agent`, invokes the SDK `FunctionTool` runtime, and asserts safe, revised, and blocked outcomes.
- LangGraph: builds and invokes a real `StateGraph` with a Metatate validation node and asserts safe, revised, and blocked outcomes.
- LlamaIndex: registers a Metatate-backed `FunctionTool`, invokes the LlamaIndex tool runtime, and asserts safe, revised, and blocked outcomes.

Each script verifies that:

- a safe analytics query is approved
- a query that selects direct identifiers is revised before use
- a direct-marketing request is blocked
- Metatate was called by the framework-wrapped tool

## What Is Not Covered

- OpenAI model loop execution. The OpenAI check proves the tool runtime, not model behavior.
- LangGraph multi-node planning or conditional edge routing. The LangGraph check proves graph runtime invocation of the Metatate validation node.
- LlamaIndex agent LLM planning. The LlamaIndex check proves the tool runtime, not LLM tool selection.
- Snowflake Cortex Agent object runtime. Use [cortex-agent-runtime-acceptance.md](cortex-agent-runtime-acceptance.md) for the live Cortex Agent check.
