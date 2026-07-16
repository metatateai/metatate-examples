#!/usr/bin/env bash
set -euo pipefail

: "${METATATE_NOTEBOOK_OUTPUT_DIR:=/private/tmp/metatate-examples-langgraph-runtime-executed}"
: "${JUPYTER_BIN:=jupyter}"

"${JUPYTER_BIN}" nbconvert \
  --to notebook \
  --execute notebooks/11_langgraph_governed_sql_agent_runtime.ipynb \
  --output-dir "${METATATE_NOTEBOOK_OUTPUT_DIR}"

printf 'Executed LangGraph runtime notebook into %s\n' "${METATATE_NOTEBOOK_OUTPUT_DIR}"
