#!/usr/bin/env bash
set -euo pipefail

: "${PYTHON_BIN:=python3}"

"${PYTHON_BIN}" cortex_agent_runtime/acceptance.py
