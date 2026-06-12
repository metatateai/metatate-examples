#!/usr/bin/env python3
"""Validate the public examples repo without external services."""

from __future__ import annotations

import csv
import importlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    required = [
        "README.md",
        "docs/demo-data-model.md",
        "docs/ci-cd-policy-gate.md",
        "docs/validation-matrix.md",
        "docs/live-mode.md",
        "docs/snowflake-setup.md",
        "common/metatate_client.py",
        "cicd_policy_gate/__init__.py",
        "cicd_policy_gate/cli.py",
        "cicd_policy_gate/gate.py",
        "cicd_policy_gate/acceptance.py",
        "cicd_policy_gate/changes/pull_request_042.json",
        "cortex_agent_runtime/acceptance.py",
        "cortex_agent_runtime/__init__.py",
        "framework_runtime/langgraph_acceptance.py",
        "framework_runtime/langgraph_agent_acceptance.py",
        "framework_runtime/langgraph_governed_sql_agent.py",
        "framework_runtime/scenarios.py",
        "framework_runtime/openai_agents_acceptance.py",
        "framework_runtime/llamaindex_acceptance.py",
        "docs/cortex-agent-runtime-acceptance.md",
        "scripts/create_mcp_pat_user.sh",
        "scripts/run_cortex_agent_runtime_acceptance.sh",
        "scripts/run_cortex_agent_runtime_notebook.sh",
        "scripts/run_cicd_policy_gate.sh",
        "scripts/run_cicd_policy_gate_acceptance.sh",
        "scripts/run_framework_runtime_acceptance.sh",
        "scripts/run_langgraph_runtime_notebook.sh",
        "scripts/run_notebook_pack.sh",
        "sql/setup_acmecloud_demo.sql",
        "sql/smoke_acmecloud_demo.sql",
        "sql/cleanup_acmecloud_demo.sql",
        "requirements-framework.txt",
    ]
    for relative in required:
        assert (ROOT / relative).exists(), f"missing {relative}"

    validate_json_files()
    validate_csv_files()
    validate_policy_files()
    validate_notebooks()
    validate_sql_fixture()
    validate_cortex_agent_runtime_files()
    validate_cicd_policy_gate_files()
    validate_framework_runtime_files()
    validate_python_imports()
    print("metatate-examples validation passed")


def validate_json_files() -> None:
    for path in (ROOT / "sample-data" / "acmecloud" / "metatate-responses").glob("*.json"):
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        assert "status" in payload, f"{path} missing status"
        assert "data" in payload, f"{path} missing data"


def validate_csv_files() -> None:
    for path in (ROOT / "sample-data" / "acmecloud" / "tables").glob("*.csv"):
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert rows, f"{path} has no rows"


def validate_policy_files() -> None:
    for path in (ROOT / "sample-data" / "acmecloud" / "policies").glob("*.yaml"):
        text = path.read_text(encoding="utf-8")
        for marker in ("apiVersion: metatate.io/v1", "kind: DataPolicy", "spec:", "selector:"):
            assert marker in text, f"{path} missing {marker}"


def validate_notebooks() -> None:
    notebooks = sorted((ROOT / "notebooks").glob("*.ipynb"))
    assert len(notebooks) == 14, "expected fourteen starter notebooks"
    for path in notebooks:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        assert payload["nbformat"] == 4, f"{path} is not nbformat 4"
        assert payload["cells"], f"{path} has no cells"
        for cell in payload["cells"]:
            assert cell.get("id"), f"{path} has a cell without an id"


def validate_sql_fixture() -> None:
    setup_sql = (ROOT / "sql" / "setup_acmecloud_demo.sql").read_text(encoding="utf-8")
    for table in (
        "app_data.governed_tables",
        "app_data.deployed_instructions",
        "app_data.deployed_usage_rules",
        "app_data.deployed_transfer_rules",
        "app_data.deployed_validation_rules",
        "app_data.deployed_column_details",
        "app_data.deployed_data_meaning",
    ):
        assert table in setup_sql, f"setup SQL missing {table}"

    for rule_type in ("permitted_use", "prohibited_use", "ai_governance", "column_masking"):
        assert rule_type in setup_sql, f"setup SQL missing rule type {rule_type}"


def validate_framework_runtime_files() -> None:
    runner = (ROOT / "scripts" / "run_framework_runtime_acceptance.sh").read_text(encoding="utf-8")
    for command in (
        "python3 framework_runtime/langgraph_acceptance.py",
        "python3 framework_runtime/langgraph_agent_acceptance.py",
        "python3 framework_runtime/openai_agents_acceptance.py",
        "python3 framework_runtime/llamaindex_acceptance.py",
    ):
        assert command in runner, f"framework runner missing {command}"

    scenarios = (ROOT / "framework_runtime" / "scenarios.py").read_text(encoding="utf-8")
    for marker in (
        "RecordingMetatateClient",
        "validate_sql_for_agent",
        "assert_guard_behavior",
        "SAFE_ANALYTICS_SQL",
    ):
        assert marker in scenarios, f"framework scenarios missing {marker}"

    langgraph = (ROOT / "framework_runtime" / "langgraph_acceptance.py").read_text(encoding="utf-8")
    for marker in ("StateGraph", "validate_with_metatate", "assert_guard_behavior"):
        assert marker in langgraph, f"LangGraph acceptance missing {marker}"

    langgraph_agent = (ROOT / "framework_runtime" / "langgraph_agent_acceptance.py").read_text(encoding="utf-8")
    for marker in ("build_governed_sql_agent", "approve", "revise", "block"):
        assert marker in langgraph_agent, f"LangGraph agent acceptance missing {marker}"

    langgraph_notebook_runner = (ROOT / "scripts" / "run_langgraph_runtime_notebook.sh").read_text(encoding="utf-8")
    assert "13_langgraph_governed_sql_agent_runtime.ipynb" in langgraph_notebook_runner


def validate_cicd_policy_gate_files() -> None:
    fixture_path = ROOT / "cicd_policy_gate" / "changes" / "pull_request_042.json"
    with fixture_path.open("r", encoding="utf-8") as handle:
        change_set = json.load(handle)
    assert change_set["changes"], "CI/CD policy gate fixture has no changes"
    for change in change_set["changes"]:
        for marker in ("change_id", "kind", "description"):
            assert marker in change, f"CI/CD gate change missing {marker}: {change}"

    gate = (ROOT / "cicd_policy_gate" / "gate.py").read_text(encoding="utf-8")
    for marker in (
        "validate_query_context",
        "authorize_use",
        "DEFAULT_CHANGESET_PATH",
        "fail_on_controls",
        "METATATE_CI_GATE_STRICT",
    ):
        assert marker in gate, f"CI/CD policy gate missing {marker}"

    acceptance = (ROOT / "cicd_policy_gate" / "acceptance.py").read_text(encoding="utf-8")
    for marker in ("EXPECTED_GATES", "release_allowed is False", "evidence_id"):
        assert marker in acceptance, f"CI/CD gate acceptance missing {marker}"

    runner = (ROOT / "scripts" / "run_cicd_policy_gate.sh").read_text(encoding="utf-8")
    assert "python3 -m cicd_policy_gate.cli" in runner, "CI/CD gate runner does not call the gate CLI"

    acceptance_runner = (ROOT / "scripts" / "run_cicd_policy_gate_acceptance.sh").read_text(encoding="utf-8")
    assert "cicd_policy_gate/acceptance.py" in acceptance_runner, "CI/CD acceptance runner missing script"


def validate_cortex_agent_runtime_files() -> None:
    runner = (ROOT / "scripts" / "run_cortex_agent_runtime_acceptance.sh").read_text(encoding="utf-8")
    assert "cortex_agent_runtime/acceptance.py" in runner, "Cortex runner missing acceptance script"

    notebook_runner = (ROOT / "scripts" / "run_cortex_agent_runtime_notebook.sh").read_text(encoding="utf-8")
    assert "12_snowflake_cortex_agent_runtime.ipynb" in notebook_runner, "Cortex notebook runner missing notebook"

    acceptance = (ROOT / "cortex_agent_runtime" / "acceptance.py").read_text(encoding="utf-8")
    for marker in (
        "AGENT_VALIDATE_QUERY_CONTEXT",
        "validate_query_with_metatate",
        "METATATE_GOVERNED_SQL_AGENT",
        "/api/v2/statements",
        ":run",
    ):
        assert marker in acceptance, f"Cortex acceptance missing {marker}"


def validate_python_imports() -> None:
    sys.path.insert(0, str(ROOT))
    common = importlib.import_module("common")
    for name in ("OfflineMetatateClient", "ManagedMCPMetatateClient", "get_client"):
        assert hasattr(common, name), f"common missing {name}"
    cicd_policy_gate = importlib.import_module("cicd_policy_gate")
    for name in ("evaluate_changes", "load_changes", "DEFAULT_CHANGESET_PATH"):
        assert hasattr(cicd_policy_gate, name), f"cicd_policy_gate missing {name}"


if __name__ == "__main__":
    main()
