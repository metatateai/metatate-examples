# Validation Matrix

This repository separates examples from runtime acceptance tests.

- **Developer example:** a notebook or walkthrough a developer can read and run.
- **Offline notebook:** executes with committed fixture responses and no account.
- **Live notebook:** executes against a Metatate Cloud workspace's MCP endpoint
  (`METATATE_EXAMPLES_MODE=live`, see docs/live-mode-saas.md).
- **Framework/runtime acceptance:** invokes the real framework object and
  asserts that Metatate changes the outcome.

| Example | Developer example | Offline notebook | Live notebook | Runtime acceptance |
| --- | --- | --- | --- | --- |
| Setup and context discovery | `00_setup_live_or_offline.ipynb` | Yes | Yes | Not applicable |
| Decision layer cookbook | `01_decision_layer_cookbook.ipynb` | Yes | Yes | Not applicable |
| LangGraph governed SQL agent | `02_governed_sql_agent_langgraph.ipynb` | Yes | Yes | `framework_runtime/langgraph_acceptance.py` |
| Transfer governance before export | `03_transfer_governance_before_export.ipynb` | Yes | Yes | Covered by notebook execution |
| Governed text-to-SQL | `04_governed_text_to_sql_agent.ipynb` | Yes | Yes | Covered by notebook execution |
| Agent red-team evaluation | `05_agent_red_team_evaluation_harness.ipynb` | Yes | Yes | Covered by notebook execution |
| CI/CD policy gate for data and AI changes | `06_ci_gate_for_data_ai_changes.ipynb` | Yes | Yes | `cicd_policy_gate/acceptance.py` |
| Governed RAG ingestion gate | `07_governed_rag_embedding_ingestion_gate.ipynb` | Yes | Yes | Covered by notebook execution |
| OpenAI Agents SDK tool guard | `08_openai_agents_tool_guard_pattern.ipynb` | Yes | Yes | `framework_runtime/openai_agents_acceptance.py` |
| Human-in-the-loop exception workflow | `09_human_approval_packet_for_conditional_export.ipynb` | Yes | Yes | `human_exception_workflow/acceptance.py` |
| LlamaIndex governed retrieval | `10_llamaindex_governed_retrieval_pattern.ipynb` | Yes | Yes | `framework_runtime/llamaindex_acceptance.py` |
| LangGraph governed SQL agent runtime | `11_langgraph_governed_sql_agent_runtime.ipynb` | Yes; requires framework deps | Yes; requires framework deps and MCP env | `framework_runtime/langgraph_agent_acceptance.py` |
| Governance states and the wider estate | `12_governance_states_and_the_wider_estate.ipynb` | Yes | Yes | Covered by notebook execution |
| The SQL gauntlet | `13_sql_gauntlet_validate_query_context.ipynb` | Yes | Yes | Covered by notebook execution |
| Governed agent arc, end to end | `14_governed_agent_end_to_end.ipynb` | Yes; requires framework deps | Yes; requires framework deps and MCP env | `governed_agent_arc/acceptance.py` |
| Audit evidence packet | `15_audit_evidence_packet.ipynb` | Yes | Yes | `audit_evidence/acceptance.py` |

## Test Commands

GitHub Actions:

- `.github/workflows/offline-ci.yml` runs the offline PR gate.
- `.github/workflows/live-saas-mcp-validation.yml` runs the manual live release
  gate against a Metatate Cloud workspace (secrets `METATATE_SAAS_MCP_URL`,
  `METATATE_SAAS_MCP_TOKEN`; the workspace must serve the AcmeCloud demo
  publication).

Run the core notebook pack offline:

```bash
scripts/run_notebook_pack.sh
```

Run the core notebook pack live against your workspace:

```bash
METATATE_EXAMPLES_MODE=live \
METATATE_MCP_URL=https://<your-workspace-mcp-endpoint>/mcp \
METATATE_SAAS_MCP_TOKEN=mtt_... \
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

Run human exception workflow acceptance:

```bash
scripts/run_human_exception_workflow_acceptance.sh
```

Run the human exception workflow as a command:

```bash
scripts/run_human_exception_workflow.sh
```

Run the LangGraph runtime notebook:

```bash
scripts/run_langgraph_runtime_notebook.sh
```

Do not treat a framework as fully integrated until its runtime acceptance script passes.

## Snowflake Native App lane

The Snowflake-managed MCP validation lane (Cortex preflight and hosted Cortex
Agent runtime included) lives in the frozen
[metatate-snowflake-examples](https://github.com/metatateai/metatate-snowflake-examples)
repository.
