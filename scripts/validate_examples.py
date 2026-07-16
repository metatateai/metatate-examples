#!/usr/bin/env python3
"""Validate the public examples repo without external services."""

from __future__ import annotations

import csv
import importlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    required = [
        ".github/CODEOWNERS",
        ".github/workflows/offline-ci.yml",
        ".github/workflows/live-saas-mcp-validation.yml",
        "common/saas_client.py",
        "docs/live-mode-saas.md",
        "README.md",
        "docs/demo-data-model.md",
        "docs/ci-cd-policy-gate.md",
        "docs/human-exception-workflow.md",
        "docs/release-process.md",
        "docs/validation-matrix.md",
        "common/metatate_client.py",
        "cicd_policy_gate/__init__.py",
        "cicd_policy_gate/cli.py",
        "cicd_policy_gate/gate.py",
        "cicd_policy_gate/acceptance.py",
        "cicd_policy_gate/changes/pull_request_042.json",
        "framework_runtime/langgraph_acceptance.py",
        "framework_runtime/langgraph_agent_acceptance.py",
        "framework_runtime/langgraph_governed_sql_agent.py",
        "framework_runtime/scenarios.py",
        "framework_runtime/openai_agents_acceptance.py",
        "framework_runtime/llamaindex_acceptance.py",
        "human_exception_workflow/__init__.py",
        "human_exception_workflow/cli.py",
        "human_exception_workflow/workflow.py",
        "human_exception_workflow/acceptance.py",
        "scripts/run_cicd_policy_gate.sh",
        "scripts/run_cicd_policy_gate_acceptance.sh",
        "scripts/run_human_exception_workflow.sh",
        "scripts/run_human_exception_workflow_acceptance.sh",
        "scripts/run_framework_runtime_acceptance.sh",
        "scripts/run_langgraph_runtime_notebook.sh",
        "scripts/run_notebook_pack.sh",
        "requirements-framework.txt",
    ]
    for relative in required:
        assert (ROOT / relative).exists(), f"missing {relative}"

    validate_json_files()
    validate_csv_files()
    validate_policy_files()
    validate_notebooks()
    validate_cicd_policy_gate_files()
    validate_human_exception_workflow_files()
    validate_ci_workflows()
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
    assert len(notebooks) == 12, "expected twelve starter notebooks"
    for path in notebooks:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        assert payload["nbformat"] == 4, f"{path} is not nbformat 4"
        assert payload["cells"], f"{path} has no cells"
        for cell in payload["cells"]:
            assert cell.get("id"), f"{path} has a cell without an id"

    # Notebooks are generated artifacts: hand edits get silently lost on the
    # next regeneration, so drift from the generator is a validation failure.
    check = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_notebooks.py"), "--check"],
        capture_output=True,
        text=True,
    )
    assert check.returncode == 0, (
        "notebooks drifted from scripts/build_notebooks.py:\n"
        f"{check.stdout}{check.stderr}"
    )


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
    assert "11_langgraph_governed_sql_agent_runtime.ipynb" in langgraph_notebook_runner


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


def validate_human_exception_workflow_files() -> None:
    workflow = (ROOT / "human_exception_workflow" / "workflow.py").read_text(encoding="utf-8")
    for marker in (
        "validate_query_context",
        "authorize_use",
        "DEFAULT_REQUESTS",
        "DEFAULT_REVIEWS",
        "resumed_with_controls",
        "blocked_by_policy",
    ):
        assert marker in workflow, f"human exception workflow missing {marker}"

    acceptance = (ROOT / "human_exception_workflow" / "acceptance.py").read_text(encoding="utf-8")
    for marker in ("run_workflow", "ready_without_exception", "resumed_with_controls", "blocked_by_policy"):
        assert marker in acceptance, f"human exception acceptance missing {marker}"

    runner = (ROOT / "scripts" / "run_human_exception_workflow.sh").read_text(encoding="utf-8")
    assert "python3 -m human_exception_workflow.cli" in runner, "human exception runner does not call the CLI"

    acceptance_runner = (ROOT / "scripts" / "run_human_exception_workflow_acceptance.sh").read_text(
        encoding="utf-8"
    )
    assert "human_exception_workflow/acceptance.py" in acceptance_runner, "human exception acceptance runner missing script"


def validate_ci_workflows() -> None:
    offline = (ROOT / ".github" / "workflows" / "offline-ci.yml").read_text(encoding="utf-8")
    for marker in (
        "scripts/validate_examples.py",
        "scripts/run_cicd_policy_gate_acceptance.sh",
        "scripts/run_human_exception_workflow_acceptance.sh",
        "scripts/run_framework_runtime_acceptance.sh",
        "scripts/run_notebook_pack.sh",
    ):
        assert marker in offline, f"offline CI workflow missing {marker}"

    saas = (ROOT / ".github" / "workflows" / "live-saas-mcp-validation.yml").read_text(encoding="utf-8")
    for marker in (
        "workflow_dispatch",
        "METATATE_MCP_BACKEND: saas",
        "METATATE_SAAS_MCP_TOKEN",
        "scripts/run_cicd_policy_gate_acceptance.sh",
        "scripts/run_human_exception_workflow_acceptance.sh",
        "scripts/run_framework_runtime_acceptance.sh",
        "scripts/run_notebook_pack.sh",
        "scripts/run_langgraph_runtime_notebook.sh",
    ):
        assert marker in saas, f"live SaaS MCP workflow missing {marker}"

    client = (ROOT / "common" / "saas_client.py").read_text(encoding="utf-8")
    for marker in ("SaasMcpMetatateClient", "structuredContent", "residency.cross_border_transfer"):
        assert marker in client, f"saas client missing {marker}"
    factory = (ROOT / "common" / "metatate_client.py").read_text(encoding="utf-8")
    assert "METATATE_MCP_BACKEND" in factory, "get_client missing the backend selector"


def validate_python_imports() -> None:
    sys.path.insert(0, str(ROOT))
    common = importlib.import_module("common")
    for name in ("OfflineMetatateClient", "ManagedMCPMetatateClient", "get_client"):
        assert hasattr(common, name), f"common missing {name}"
    cicd_policy_gate = importlib.import_module("cicd_policy_gate")
    for name in ("evaluate_changes", "load_changes", "DEFAULT_CHANGESET_PATH"):
        assert hasattr(cicd_policy_gate, name), f"cicd_policy_gate missing {name}"
    human_exception_workflow = importlib.import_module("human_exception_workflow")
    for name in ("run_workflow", "DEFAULT_REQUESTS", "DEFAULT_REVIEWS"):
        assert hasattr(human_exception_workflow, name), f"human_exception_workflow missing {name}"


if __name__ == "__main__":
    main()
