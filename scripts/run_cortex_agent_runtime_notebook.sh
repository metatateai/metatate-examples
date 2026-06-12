#!/usr/bin/env bash
set -euo pipefail

: "${METATATE_NOTEBOOK_OUTPUT_DIR:=/private/tmp/metatate-examples-cortex-runtime-executed}"
: "${JUPYTER_BIN:=jupyter}"
: "${METATATE_CORTEX_PAT_ENV:=${METATATE_MCP_PAT_ENV:-METATATE_EXAMPLES_PAT}}"

token_value="${!METATATE_CORTEX_PAT_ENV:-}"
if [[ -z "${token_value}" ]]; then
  echo "${METATATE_CORTEX_PAT_ENV} must contain the Snowflake PAT secret" >&2
  exit 1
fi

"${JUPYTER_BIN}" nbconvert \
  --to notebook \
  --execute notebooks/12_snowflake_cortex_agent_runtime.ipynb \
  --output-dir "${METATATE_NOTEBOOK_OUTPUT_DIR}"

printf 'Executed Cortex Agent runtime notebook into %s\n' "${METATATE_NOTEBOOK_OUTPUT_DIR}"
