# Notebooks

These notebooks default to offline mode. They use committed Metatate response fixtures from `sample-data/acmecloud/metatate-responses`.

Set `METATATE_EXAMPLES_MODE=live` to call your Metatate Cloud workspace's MCP
endpoint instead (see `docs/live-mode-saas.md`).

## Order

1. `00_setup_live_or_offline.ipynb`
2. `01_decision_layer_cookbook.ipynb`
3. `02_governed_sql_agent_langgraph.ipynb`
4. `03_transfer_governance_before_export.ipynb`
5. `04_governed_text_to_sql_agent.ipynb`
6. `05_agent_red_team_evaluation_harness.ipynb`
7. `06_ci_gate_for_data_ai_changes.ipynb`
8. `07_governed_rag_embedding_ingestion_gate.ipynb`
9. `08_openai_agents_tool_guard_pattern.ipynb`
10. `09_human_approval_packet_for_conditional_export.ipynb`
11. `10_llamaindex_governed_retrieval_pattern.ipynb`
12. `11_langgraph_governed_sql_agent_runtime.ipynb`
13. `12_governance_states_and_the_wider_estate.ipynb`
14. `13_sql_gauntlet_validate_query_context.ipynb`

Notebook `06_ci_gate_for_data_ai_changes.ipynb` uses the reusable `cicd_policy_gate` package. The same gate can be run from CI with `scripts/run_cicd_policy_gate.sh`.

Notebook `09_human_approval_packet_for_conditional_export.ipynb` uses the reusable `human_exception_workflow` package. The same workflow can be run from a terminal with `scripts/run_human_exception_workflow.sh`.

Notebook `11_langgraph_governed_sql_agent_runtime.ipynb` requires `requirements-framework.txt` and is executed separately with `scripts/run_langgraph_runtime_notebook.sh`.

The notebooks are generated from `scripts/build_notebooks.py` so the JSON
remains reproducible. Do not hand-edit the `.ipynb` files: edit the generator
and rerun it. CI enforces this via `scripts/build_notebooks.py --check`.

Framework runtime acceptance for LangGraph, OpenAI Agents SDK, and LlamaIndex
lives outside the notebook pack in `framework_runtime/`. See
`docs/validation-matrix.md`.
