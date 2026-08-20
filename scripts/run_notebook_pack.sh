#!/usr/bin/env bash
set -euo pipefail

: "${METATATE_EXAMPLES_MODE:=offline}"
: "${METATATE_NOTEBOOK_OUTPUT_DIR:=/private/tmp/metatate-examples-${METATATE_EXAMPLES_MODE}-executed}"
: "${JUPYTER_BIN:=jupyter}"

NOTEBOOKS=(
  notebooks/00_setup_live_or_offline.ipynb
  notebooks/01_decision_layer_cookbook.ipynb
  notebooks/02_governed_sql_agent_langgraph.ipynb
  notebooks/03_transfer_governance_before_export.ipynb
  notebooks/04_governed_text_to_sql_agent.ipynb
  notebooks/05_agent_red_team_evaluation_harness.ipynb
  notebooks/06_ci_gate_for_data_ai_changes.ipynb
  notebooks/07_governed_rag_embedding_ingestion_gate.ipynb
  notebooks/08_openai_agents_tool_guard_pattern.ipynb
  notebooks/09_human_approval_packet_for_conditional_export.ipynb
  notebooks/10_llamaindex_governed_retrieval_pattern.ipynb
  notebooks/12_governance_states_and_the_wider_estate.ipynb
  notebooks/13_sql_gauntlet_validate_query_context.ipynb
  notebooks/15_audit_evidence_packet.ipynb
  notebooks/16_purpose_bound_agent_data_windows.ipynb
  notebooks/17_adtech_consent_three_permissions_one_field.ipynb
  notebooks/18_payments_local_data_is_not_the_source_of_truth.ipynb
  notebooks/19_healthcare_one_person_four_concepts.ipynb
  notebooks/20_government_rules_outside_the_record.ipynb
)

if [[ "${METATATE_EXAMPLES_MODE}" == "live" ]]; then
  : "${METATATE_MCP_URL:?METATATE_MCP_URL is required in live mode}"
  : "${METATATE_MCP_PAT_ENV:=METATATE_SAAS_MCP_TOKEN}"
  token_value="${!METATATE_MCP_PAT_ENV:-}"
  if [[ -z "${token_value}" ]]; then
    echo "${METATATE_MCP_PAT_ENV} must contain the Metatate MCP access token in live mode" >&2
    exit 1
  fi
fi

"${JUPYTER_BIN}" nbconvert \
  --to notebook \
  --execute "${NOTEBOOKS[@]}" \
  --output-dir "${METATATE_NOTEBOOK_OUTPUT_DIR}"

printf 'Executed %s notebook pack into %s\n' "${METATATE_EXAMPLES_MODE}" "${METATATE_NOTEBOOK_OUTPUT_DIR}"
