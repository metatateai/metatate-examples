# Validation Matrix

This repository separates examples from runtime acceptance tests.

- **Developer example:** a notebook or walkthrough a developer can read and run.
- **Offline notebook:** executes with committed fixture responses and no Snowflake account.
- **Live MCP notebook:** executes against the Snowflake-managed Metatate MCP server.
- **Framework/runtime acceptance:** invokes the real framework or hosted runtime surface and asserts that Metatate changes the outcome.

| Example | Developer example | Offline notebook | Live MCP notebook | Runtime acceptance |
| --- | --- | --- | --- | --- |
| Setup and context discovery | `00_setup_live_or_offline.ipynb` | Yes | Yes | Not applicable |
| Decision layer cookbook | `01_decision_layer_cookbook.ipynb` | Yes | Yes | Not applicable |
| LangGraph governed SQL agent | `02_governed_sql_agent_langgraph.ipynb` | Yes | Yes | `framework_runtime/langgraph_acceptance.py` |
| LangGraph governed SQL agent runtime | `13_langgraph_governed_sql_agent_runtime.ipynb` | Yes; requires framework deps | Yes; requires framework deps and MCP env | `framework_runtime/langgraph_agent_acceptance.py` |
| Transfer governance before export | `03_transfer_governance_before_export.ipynb` | Yes | Yes | Covered by notebook execution |
| Governed text-to-SQL | `04_governed_text_to_sql_agent.ipynb` | Yes | Yes | Covered by notebook execution |
| Agent red-team evaluation | `05_agent_red_team_evaluation_harness.ipynb` | Yes | Yes | Covered by notebook execution |
| CI/CD policy gate for data and AI changes | `06_ci_gate_for_data_ai_changes.ipynb` | Yes | Yes | `cicd_policy_gate/acceptance.py` |
| Governed RAG ingestion gate | `07_governed_rag_embedding_ingestion_gate.ipynb` | Yes | Yes | Covered by notebook execution |
| Cortex Agent custom-tool preflight | `08_snowflake_cortex_agent_tool_preflight.ipynb` | Yes | Yes | Pattern only; use the Cortex runtime notebook for hosted runtime proof |
| OpenAI Agents SDK tool guard | `09_openai_agents_tool_guard_pattern.ipynb` | Yes | Yes | `framework_runtime/openai_agents_acceptance.py` |
| Human approval packet | `10_human_approval_packet_for_conditional_export.ipynb` | Yes | Yes | Covered by notebook execution |
| LlamaIndex governed retrieval | `11_llamaindex_governed_retrieval_pattern.ipynb` | Yes | Yes | `framework_runtime/llamaindex_acceptance.py` |
| Cortex Agent hosted runtime | `12_snowflake_cortex_agent_runtime.ipynb` | Live-only | No; uses Snowflake Cortex Agents directly | `cortex_agent_runtime/acceptance.py` |

## Test Commands

Run the core notebook pack offline:

```bash
scripts/run_notebook_pack.sh
```

Run the core notebook pack live through the managed MCP server:

```bash
METATATE_EXAMPLES_MODE=live \
METATATE_MCP_URL=https://<account-url>/api/v2/databases/METATATE_APP/schemas/CORE/mcp-servers/METATATE_MCP \
SNOWFLAKE_ROLE=NAC \
METATATE_MCP_PAT_ENV=METATATE_EXAMPLES_PAT \
scripts/run_notebook_pack.sh
```

Run framework runtime acceptance:

```bash
scripts/run_framework_runtime_acceptance.sh
```

Run CI/CD policy gate acceptance:

```bash
scripts/run_cicd_policy_gate_acceptance.sh
```

Run the CI/CD policy gate as a CI command:

```bash
scripts/run_cicd_policy_gate.sh --strict
```

Run the LangGraph runtime notebook:

```bash
scripts/run_langgraph_runtime_notebook.sh
```

Run hosted Cortex Agent runtime acceptance:

```bash
scripts/run_cortex_agent_runtime_acceptance.sh
```

Run the hosted Cortex Agent notebook:

```bash
scripts/run_cortex_agent_runtime_notebook.sh
```

Do not treat a framework as fully integrated until its runtime acceptance script passes.
