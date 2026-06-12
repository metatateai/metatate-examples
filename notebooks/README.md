# Notebooks

These notebooks default to offline mode. They use committed Metatate response fixtures from `sample-data/acmecloud/metatate-responses`.

Set `METATATE_EXAMPLES_MODE=live` to call the Snowflake-managed Metatate MCP
server instead.

## Order

1. `00_setup_live_or_offline.ipynb`
2. `01_decision_layer_cookbook.ipynb`
3. `02_governed_sql_agent_langgraph.ipynb`
4. `03_transfer_governance_before_export.ipynb`
5. `04_governed_text_to_sql_agent.ipynb`
6. `05_agent_red_team_evaluation_harness.ipynb`
7. `06_ci_gate_for_data_ai_changes.ipynb`
8. `07_governed_rag_embedding_ingestion_gate.ipynb`
9. `08_snowflake_cortex_agent_tool_preflight.ipynb`
10. `09_openai_agents_tool_guard_pattern.ipynb`
11. `10_human_approval_packet_for_conditional_export.ipynb`
12. `11_llamaindex_governed_retrieval_pattern.ipynb`
13. `12_snowflake_cortex_agent_runtime.ipynb`
14. `13_langgraph_governed_sql_agent_runtime.ipynb`

Notebook `06_ci_gate_for_data_ai_changes.ipynb` uses the reusable `cicd_policy_gate` package. The same gate can be run from CI with `scripts/run_cicd_policy_gate.sh`.

Notebook `12_snowflake_cortex_agent_runtime.ipynb` is live-only. It creates and runs Snowflake Cortex Agent objects and is executed separately with `scripts/run_cortex_agent_runtime_notebook.sh`.

Notebook `13_langgraph_governed_sql_agent_runtime.ipynb` requires `requirements-framework.txt` and is executed separately with `scripts/run_langgraph_runtime_notebook.sh`.

The notebooks are generated from `scripts/build_notebooks.py` so the JSON remains reproducible.

Framework runtime acceptance for LangGraph, OpenAI Agents SDK, and LlamaIndex
lives outside the notebook pack in `framework_runtime/`. Cortex Agent hosted
runtime acceptance lives in `cortex_agent_runtime/`. See
`docs/validation-matrix.md`.
