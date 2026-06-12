#!/usr/bin/env bash
set -euo pipefail

: "${METATATE_CI_GATE_OUTPUT:=/private/tmp/metatate-cicd-policy-gate-report.json}"

set +e
python3 -m cicd_policy_gate.cli \
  --output "${METATATE_CI_GATE_OUTPUT}" \
  "$@"
status=$?
set -e

printf 'Wrote CI/CD policy gate report to %s\n' "${METATATE_CI_GATE_OUTPUT}"
exit "${status}"
