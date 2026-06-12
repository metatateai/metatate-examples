# Metatate Examples

Metatate is a programmable decision layer for governed data. It gives agents and workflows structured context about meaning, policy, allowed use, transfer rules, and decision rationale before they touch data.

This repository is the public examples cookbook. It uses one synthetic B2B SaaS company, AcmeCloud, so every notebook builds on the same tables, policies, and expected decisions.

Installable integration plugins live in separate repositories:

- `metatate-claude-plugins` for the Claude Code plugin
- `metatate-cortex-code-plugin` for the Cortex Code plugin

## Demo Domain

AcmeCloud covers customer operations, revenue, product usage, support, and prepared exports.

Governed tables:

- `ACMECLOUD_DEMO.PUBLIC.CUSTOMERS`
- `ACMECLOUD_DEMO.PUBLIC.SUBSCRIPTIONS`
- `ACMECLOUD_DEMO.PUBLIC.PRODUCT_USAGE_EVENTS`
- `ACMECLOUD_DEMO.PUBLIC.SUPPORT_TICKETS`
- `ACMECLOUD_DEMO.PUBLIC.CUSTOMER_EXPORTS`

Demo policy behavior:

- customer PII can be used for analytics and reporting only with minimization or masking
- direct marketing and advertising are blocked unless a consent-specific workflow is added
- customer records and support tickets are blocked for model training
- customer exports require destination-aware authorization
- Salesforce exports are conditional; advertising-platform exports are denied

## Notebook Pack

| Notebook | What it shows |
| --- | --- |
| `00_setup_live_or_offline.ipynb` | Environment check and context discovery. |
| `01_decision_layer_cookbook.ipynb` | Core Metatate flow: discover, inspect, authorize, validate, explain. |
| `02_governed_sql_agent_langgraph.ipynb` | A small governed SQL-agent pattern with optional LangGraph. |
| `03_transfer_governance_before_export.ipynb` | Destination-aware transfer decisions before export. |
| `04_governed_text_to_sql_agent.ipynb` | Text-to-SQL that validates and revises SQL before returning it. |
| `05_agent_red_team_evaluation_harness.ipynb` | Repeatable risky-prompt checks for governed agents. |
| `06_ci_gate_for_data_ai_changes.ipynb` | A release-gate pattern for SQL, export, and AI workflow changes. |
| `07_governed_rag_embedding_ingestion_gate.ipynb` | Pre-ingestion checks before data enters RAG or embedding workflows. |
| `08_snowflake_cortex_agent_tool_preflight.ipynb` | A Cortex-style custom-tool preflight pattern using Metatate decisions. |
| `09_openai_agents_tool_guard_pattern.ipynb` | A deterministic tool guard pattern for OpenAI Agents SDK-style apps. |
| `10_human_approval_packet_for_conditional_export.ipynb` | Turning conditional export decisions into reviewer-ready approval packets. |
| `11_llamaindex_governed_retrieval_pattern.ipynb` | A governed retrieval function that can be wrapped as a LlamaIndex tool. |

The notebooks run in two modes:

- **Offline:** default; uses committed JSON fixtures and needs no Snowflake account.
- **Live:** calls the Snowflake-managed Metatate MCP server with a role-restricted PAT.

## Validation Scope

The notebook pack is fully executed in offline mode and live mode through the Snowflake-managed Metatate MCP server.

Framework runtime coverage is separate from notebook execution:

- `02_governed_sql_agent_langgraph.ipynb` uses LangGraph when `langgraph` is installed; otherwise it runs the same graph steps as plain Python.
- `08_snowflake_cortex_agent_tool_preflight.ipynb` is a Cortex-style custom-tool preflight pattern.
- `scripts/run_cortex_agent_runtime_acceptance.sh` creates and runs a live Cortex Agent object with a server-side Metatate custom tool.
- `09_openai_agents_tool_guard_pattern.ipynb` is paired with a deterministic OpenAI Agents SDK `FunctionTool` runtime acceptance script.
- `11_llamaindex_governed_retrieval_pattern.ipynb` is paired with a deterministic LlamaIndex `FunctionTool` runtime acceptance script.

The OpenAI and LlamaIndex runtime checks invoke real framework tool objects, but they intentionally do not call an LLM. Cortex Agent runtime acceptance is live-only and calls Snowflake Cortex Agents. Review [docs/framework-runtime-acceptance.md](docs/framework-runtime-acceptance.md) and [docs/cortex-agent-runtime-acceptance.md](docs/cortex-agent-runtime-acceptance.md) for the exact coverage.

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
jupyter notebook notebooks
```

To execute the full pack offline:

```bash
scripts/run_notebook_pack.sh
```

To run the framework runtime acceptance checks:

```bash
python3 --version  # confirm Python 3.10+
python3 -m venv .venv-framework
source .venv-framework/bin/activate
pip install -r requirements-framework.txt
scripts/run_framework_runtime_acceptance.sh
```

Use Python 3.10 or newer for framework runtime acceptance.

To run the live Cortex Agent object acceptance check:

```bash
export METATATE_EXAMPLES_PAT="$(cat /private/tmp/metatate_examples_mcp_pat)"

METATATE_CORTEX_ACCOUNT_URL=https://<account-url> \
SNOWFLAKE_ROLE=NAC \
METATATE_CORTEX_WAREHOUSE=WH_NAC \
scripts/run_cortex_agent_runtime_acceptance.sh
```

Review [docs/cortex-agent-runtime-acceptance.md](docs/cortex-agent-runtime-acceptance.md) before running it. This check creates scratch Snowflake objects and has no offline mode.

## Live Mode

Live mode uses the Snowflake-managed Metatate MCP server. The notebooks still run locally, but every Metatate decision call goes through MCP.

```bash
pip install -r requirements-live.txt
cp .env.example .env
```

Configure `.env` with your MCP endpoint and role. Then export a role-restricted PAT in the shell where Jupyter starts:

```bash
export METATATE_EXAMPLES_MODE=live
export METATATE_EXAMPLES_PAT='<snowflake-pat-secret>'
scripts/run_notebook_pack.sh
```

Use a dedicated Snowflake service user for the PAT. The recommended setup is in [docs/live-mode.md](docs/live-mode.md).

## Snowflake Fixture

To run the notebooks exactly as written against a live Metatate Native App, seed the AcmeCloud demo fixture:

```bash
snow sql -f sql/setup_acmecloud_demo.sql -c <profile>
snow sql -f sql/smoke_acmecloud_demo.sql -c <profile>
```

Review [docs/snowflake-setup.md](docs/snowflake-setup.md) before running the setup script.

For production use, deploy policies through Metatate. The SQL fixture is only for examples, demos, and repeatable validation.

## Repository Map

```text
common/                         Shared Python client helpers
docs/                           Setup, demo model, and troubleshooting
cortex_agent_runtime/           Live Cortex Agent object acceptance helper
notebooks/                      Notebook-first walkthroughs
sample-data/acmecloud/tables/   Small synthetic CSV tables
sample-data/acmecloud/policies/ Example policy YAML
sample-data/acmecloud/metatate-responses/
                                Offline Metatate response fixtures
sample-outputs/                 Curated expected output summaries
scripts/                        Validation and notebook execution helpers
sql/                            Snowflake demo table and Metatate fixture SQL
```

## Links

- Metatate docs: https://docs.getmetatate.com
- MCP cookbook: https://docs.getmetatate.com/mcp/cookbook
- Learn use cases: https://www.getmetatate.com/learn
- Snowflake Marketplace listing: https://app.snowflake.com/marketplace/listing/GZ2FTZU03OAS
