#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
import sys

if sys.version_info < (3, 10):
    raise SystemExit(
        "Framework runtime acceptance requires Python 3.10+. "
        f"Current interpreter: {sys.version.split()[0]}"
    )
PY

python3 framework_runtime/openai_agents_acceptance.py
python3 framework_runtime/llamaindex_acceptance.py
