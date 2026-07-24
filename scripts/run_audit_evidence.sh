#!/usr/bin/env bash
set -euo pipefail

: "${METATATE_EVIDENCE_OUTPUT:=${TMPDIR:-/tmp}/metatate-evidence-packet.json}"
: "${METATATE_EVIDENCE_MARKDOWN:=${TMPDIR:-/tmp}/metatate-evidence-packet.md}"

set +e
python3 -m audit_evidence.cli \
  --output "${METATATE_EVIDENCE_OUTPUT}" \
  --markdown "${METATATE_EVIDENCE_MARKDOWN}" \
  "$@"
status=$?
set -e

exit "${status}"
