#!/usr/bin/env bash
set -euo pipefail

python3 cicd_policy_gate/dbt_acceptance.py
