#!/usr/bin/env bash
set -euo pipefail

: "${METATATE_NOTEBOOK_OUTPUT_DIR:=/private/tmp/metatate-examples-langgraph-runtime-executed}"
: "${JUPYTER_BIN:=jupyter}"

"${JUPYTER_BIN}" nbconvert \
  --to notebook \
  --execute notebooks/11_langgraph_governed_sql_agent_runtime.ipynb \
    notebooks/14_governed_agent_end_to_end.ipynb \
  --output-dir "${METATATE_NOTEBOOK_OUTPUT_DIR}"

printf 'Executed LangGraph runtime notebooks into %s\n' "${METATATE_NOTEBOOK_OUTPUT_DIR}"
