#!/usr/bin/env bash
set -euo pipefail

: "${METATATE_GOVERNED_ARC_OUTPUT:=${TMPDIR:-/tmp}/metatate-governed-agent-arc-report.json}"

set +e
python3 -m governed_agent_arc.cli \
  --output "${METATATE_GOVERNED_ARC_OUTPUT}" \
  "$@"
status=$?
set -e

exit "${status}"
