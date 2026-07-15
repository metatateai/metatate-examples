# Metatate Examples

![Animated terminal: the AcmeCloud examples asking Metatate for decisions — marketing use of customer PII is denied, an EU Salesforce export is conditional on approval and anonymization, and an aggregate analytics query passes.](docs/assets/readme-hero.svg)

Metatate is a programmable decision layer for governed data. It gives agents and workflows structured context about meaning, policy, allowed use, transfer rules, and decision rationale before they touch data.

This repository is the public examples cookbook. It uses one synthetic B2B SaaS company, AcmeCloud, so every notebook builds on the same tables, policies, and expected decisions.

Prefer these workflows inside your coding agent? Installable integration
plugins live in separate repositories:

- [metatate-claude-plugins](https://github.com/metatateai/metatate-claude-plugins) —
  Claude Code plugins: `metatate` for Metatate Cloud and `metatate-snow` for
  the Snowflake Native App.
- [metatate-cortex-code-plugin](https://github.com/metatateai/metatate-cortex-code-plugin) —
  the same decision workflows for Snowflake Cortex Code.

## Run It Live In 5 Minutes

Offline mode works with zero setup, but the fastest way to feel the decision
layer is to run these notebooks against a **live governed workspace of your
own**:

1. **Create a free Metatate account** at
   [app.getmetatate.com/sign-up?ref=examples](https://app.getmetatate.com/sign-up?ref=examples)
   and create a workspace (the free plan covers everything these examples do).
2. On your new workspace's dashboard, follow the **"New here?" banner → Load
   the demo**, then click **Load the AcmeCloud demo** — it provisions the
   exact governed domain this repo uses (five tables, three policies, one
   live publication).
3. Open **MCP Tools → Tokens** and issue an access token (shown once).
4. Point the notebooks at your workspace:

   ```bash
   export METATATE_EXAMPLES_MODE=live
   export METATATE_MCP_BACKEND=saas
   export METATATE_MCP_URL=https://<your-workspace-mcp-endpoint>/mcp   # MCP Tools → Connect
   export METATATE_SAAS_MCP_TOKEN=mtt_...
   export METATATE_MCP_PAT_ENV=METATATE_SAAS_MCP_TOKEN
   ```

Full details (and the local-stack path for contributors) are in
[docs/live-mode-saas.md](docs/live-mode-saas.md).

Running on Snowflake? The same pack runs against the Snowflake-managed
Metatate Native App instead — see [docs/live-mode.md](docs/live-mode.md).

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
| `06_ci_gate_for_data_ai_changes.ipynb` | A runnable CI/CD policy gate for SQL, export, and AI workflow changes. |
| `07_governed_rag_embedding_ingestion_gate.ipynb` | Pre-ingestion checks before data enters RAG or embedding workflows. |
| `08_snowflake_cortex_agent_tool_preflight.ipynb` | A Cortex-style custom-tool preflight pattern using Metatate decisions. |
| `09_openai_agents_tool_guard_pattern.ipynb` | A deterministic tool guard pattern for OpenAI Agents SDK-style apps. |
| `10_human_approval_packet_for_conditional_export.ipynb` | Human-in-the-loop exception workflow for safe, conditional, and denied requests. |
| `11_llamaindex_governed_retrieval_pattern.ipynb` | A governed retrieval function that can be wrapped as a LlamaIndex tool. |
| `12_snowflake_cortex_agent_runtime.ipynb` | Live-only Cortex Agent object with a server-side Metatate custom tool. |
| `13_langgraph_governed_sql_agent_runtime.ipynb` | LangGraph runtime SQL agent with approve, revise, and block routes. |

The core notebooks run in two modes:

- **Offline:** default; uses committed JSON fixtures and needs no Snowflake account.
- **Live:** calls the Snowflake-managed Metatate MCP server with a role-restricted PAT.
- **Live (SaaS):** the same pack against the Metatate SaaS cross-platform MCP endpoint with a workspace bearer token (`METATATE_MCP_BACKEND=saas` — see [docs/live-mode-saas.md](docs/live-mode-saas.md)).

Notebook `12_snowflake_cortex_agent_runtime.ipynb` is live-only because it creates and runs Snowflake Cortex Agent objects. Notebook `13_langgraph_governed_sql_agent_runtime.ipynb` requires the framework dependencies from `requirements-framework.txt`.

## Validation Scope

The notebook pack is fully executed in offline mode and live mode through the Snowflake-managed Metatate MCP server, and in live SaaS mode through the Metatate SaaS cross-platform MCP endpoint (manual workflow `.github/workflows/live-saas-mcp-validation.yml`).

Pull requests run the offline validation workflow in `.github/workflows/offline-ci.yml`. Release candidates should also run the manual live MCP workflow in `.github/workflows/live-mcp-validation.yml`.

Runtime coverage is separate from core notebook execution:

- `06_ci_gate_for_data_ai_changes.ipynb` is backed by the reusable `cicd_policy_gate` package and an acceptance script.
- `02_governed_sql_agent_langgraph.ipynb` is paired with a deterministic LangGraph `StateGraph` runtime acceptance script.
- `13_langgraph_governed_sql_agent_runtime.ipynb` is paired with a multi-node LangGraph agent runtime acceptance script.
- `08_snowflake_cortex_agent_tool_preflight.ipynb` is a Cortex-style custom-tool preflight pattern.
- `scripts/run_cortex_agent_runtime_acceptance.sh` creates and runs a live Cortex Agent object with a server-side Metatate custom tool.
- `09_openai_agents_tool_guard_pattern.ipynb` is paired with a deterministic OpenAI Agents SDK `FunctionTool` runtime acceptance script.
- `10_human_approval_packet_for_conditional_export.ipynb` is backed by the reusable `human_exception_workflow` package and an acceptance script.
- `11_llamaindex_governed_retrieval_pattern.ipynb` is paired with a deterministic LlamaIndex `FunctionTool` runtime acceptance script.

The LangGraph, OpenAI, and LlamaIndex runtime checks invoke real framework objects, but they intentionally do not call an LLM. Cortex Agent runtime acceptance is live-only and calls Snowflake Cortex Agents. Review [docs/validation-matrix.md](docs/validation-matrix.md), [docs/framework-runtime-acceptance.md](docs/framework-runtime-acceptance.md), and [docs/cortex-agent-runtime-acceptance.md](docs/cortex-agent-runtime-acceptance.md) for the exact coverage.

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

To run the CI/CD policy gate locally:

```bash
scripts/run_cicd_policy_gate.sh
scripts/run_cicd_policy_gate_acceptance.sh
```

Use `scripts/run_cicd_policy_gate.sh --strict` for a CI-style non-zero exit when denied changes are present. See [docs/ci-cd-policy-gate.md](docs/ci-cd-policy-gate.md).

To run the human-in-the-loop exception workflow locally:

```bash
scripts/run_human_exception_workflow.sh
scripts/run_human_exception_workflow_acceptance.sh
```

See [docs/human-exception-workflow.md](docs/human-exception-workflow.md).

Review [docs/release-process.md](docs/release-process.md) before tagging a public release.

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

To execute the live Cortex Agent notebook:

```bash
export METATATE_EXAMPLES_PAT="$(cat /private/tmp/metatate_examples_mcp_pat)"

METATATE_CORTEX_ACCOUNT_URL=https://<account-url> \
SNOWFLAKE_ROLE=NAC \
METATATE_CORTEX_WAREHOUSE=WH_NAC \
scripts/run_cortex_agent_runtime_notebook.sh
```

To execute the LangGraph runtime notebook:

```bash
python3 -m venv .venv-framework
source .venv-framework/bin/activate
pip install -r requirements-framework.txt
scripts/run_langgraph_runtime_notebook.sh
```

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
.github/workflows/               Offline PR CI and manual live MCP validation
common/                         Shared Python client helpers
cicd_policy_gate/               Reusable CI/CD policy gate example
docs/                           Setup, demo model, and troubleshooting
cortex_agent_runtime/           Live Cortex Agent object acceptance helpers
human_exception_workflow/       Human review and exception workflow example
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
- Metatate App: https://app.getmetatate.com
- Snowflake Marketplace listing: https://app.snowflake.com/marketplace/listing/GZ2FTZU03OAS
