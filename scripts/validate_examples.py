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
        "common/fixture_cases.py",
        "scripts/record_offline_fixtures.py",
        "docs/live-mode-saas.md",
        "README.md",
        "docs/demo-data-model.md",
        "docs/ci-cd-policy-gate.md",
        "docs/human-exception-workflow.md",
        "docs/release-process.md",
        "docs/validation-matrix.md",
        "sample-data/acmecloud/catalog.yaml",
        "sample-data/acmecloud/expected-decisions.yaml",
        "common/metatate_client.py",
        "cicd_policy_gate/__init__.py",
        "cicd_policy_gate/cli.py",
        "cicd_policy_gate/gate.py",
        "cicd_policy_gate/acceptance.py",
        "cicd_policy_gate/changes/pull_request_042.json",
        "cicd_policy_gate/dbt_adapter.py",
        "cicd_policy_gate/dbt_acceptance.py",
        "cicd_policy_gate/report_to_markdown.py",
        "cicd_policy_gate/dbt_project/dbt_project.yml",
        "cicd_policy_gate/dbt_project/artifacts/manifest.json",
        "cicd_policy_gate/dbt_project/artifacts/manifest_previous.json",
        "action.yml",
        "docs/ci-cd-policy-gate-dbt.md",
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
        "audit_evidence/__init__.py",
        "audit_evidence/evidence.py",
        "audit_evidence/cli.py",
        "audit_evidence/acceptance.py",
        "docs/audit-evidence-packet.md",
        "scripts/run_audit_evidence.sh",
        "scripts/run_audit_evidence_acceptance.sh",
        "governed_agent_arc/__init__.py",
        "governed_agent_arc/arc.py",
        "governed_agent_arc/planner.py",
        "governed_agent_arc/llm_planner.py",
        "governed_agent_arc/cli.py",
        "governed_agent_arc/acceptance.py",
        "docs/governed-agent-arc.md",
        "requirements-llm.txt",
        "scripts/build_readme_hero.py",
        "scripts/run_cicd_policy_gate.sh",
        "scripts/run_cicd_policy_gate_acceptance.sh",
        "scripts/run_cicd_dbt_adapter_acceptance.sh",
        "scripts/run_human_exception_workflow.sh",
        "scripts/run_human_exception_workflow_acceptance.sh",
        "scripts/run_governed_agent_arc.sh",
        "scripts/run_governed_agent_arc_acceptance.sh",
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
    validate_dbt_adapter_files()
    validate_audit_evidence_files()
    validate_human_exception_workflow_files()
    validate_governed_agent_arc_files()
    validate_readme_hero()
    validate_ci_workflows()
    validate_framework_runtime_files()
    validate_python_imports()
    print("metatate-examples validation passed")


def validate_json_files() -> None:
    # Recorded typed answers: every file is {case_id, tool, arguments, answer}
    # and every case in common/fixture_cases.py has a recording.
    sys.path.insert(0, str(ROOT))
    from common.fixture_cases import CASES

    fixture_dir = ROOT / "sample-data" / "acmecloud" / "metatate-responses"
    recorded = set()
    for path in fixture_dir.glob("*.json"):
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        for key in ("case_id", "tool", "arguments", "answer"):
            assert key in payload, f"{path} missing {key}"
        assert payload["case_id"] == path.stem, f"{path} case_id mismatch"
        recorded.add(path.stem)
    missing = {str(case["id"]) for case in CASES} - recorded
    assert not missing, f"cases without recordings: {sorted(missing)}"


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
    assert len(notebooks) == 16, "expected sixteen starter notebooks"
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


def validate_dbt_adapter_files() -> None:
    adapter = (ROOT / "cicd_policy_gate" / "dbt_adapter.py").read_text(encoding="utf-8")
    for marker in (
        "meta.metatate",
        "compiled_code",
        "changed_resource_ids",
        "build_change_set",
        "purpose.allowed_use",
        "skip",
    ):
        assert marker in adapter, f"dbt adapter missing {marker}"

    acceptance = (ROOT / "cicd_policy_gate" / "dbt_acceptance.py").read_text(encoding="utf-8")
    for marker in (
        "build_change_set",
        "evaluate_changes",
        "dbt-exposure-salesforce_customer_sync",
        "AI_TRAINING_BLOCKED",
        "release_allowed",
    ):
        assert marker in acceptance, f"dbt acceptance missing {marker}"

    action = (ROOT / "action.yml").read_text(encoding="utf-8")
    for marker in (
        "cicd_policy_gate.dbt_adapter",
        "cicd_policy_gate.cli",
        "cicd_policy_gate.report_to_markdown",
        "metatate-policy-gate",
        "release-allowed",
    ):
        assert marker in action, f"action.yml missing {marker}"

    runner = (ROOT / "scripts" / "run_cicd_dbt_adapter_acceptance.sh").read_text(encoding="utf-8")
    assert "cicd_policy_gate/dbt_acceptance.py" in runner, "dbt acceptance runner missing script"


def validate_audit_evidence_files() -> None:
    evidence = (ROOT / "audit_evidence" / "evidence.py").read_text(encoding="utf-8")
    for marker in (
        "DEFAULT_QUESTIONS",
        "explain_why",
        "publication_id",
        "honest_corners",
        "render_markdown",
        "View requests",
    ):
        assert marker in evidence, f"audit evidence missing {marker}"

    acceptance = (ROOT / "audit_evidence" / "acceptance.py").read_text(encoding="utf-8")
    for marker in (
        "collect_evidence",
        "not_enough_published_state",
        "review_required",
        "honest_corners == 2",
    ):
        assert marker in acceptance, f"audit evidence acceptance missing {marker}"

    runner = (ROOT / "scripts" / "run_audit_evidence.sh").read_text(encoding="utf-8")
    assert "python3 -m audit_evidence.cli" in runner, "evidence runner does not call the CLI"
    acceptance_runner = (ROOT / "scripts" / "run_audit_evidence_acceptance.sh").read_text(
        encoding="utf-8"
    )
    assert "audit_evidence/acceptance.py" in acceptance_runner, "evidence acceptance runner missing script"


def validate_governed_agent_arc_files() -> None:
    arc = (ROOT / "governed_agent_arc" / "arc.py").read_text(encoding="utf-8")
    for marker in (
        "inspect_governance_rules",
        "authorize_use",
        "validate_query_context",
        "explain_why",
        "item_from_answer",
        "reroute_to_governed_training",
        "resume_with_controls",
        "MAX_REVISIONS",
    ):
        assert marker in arc, f"governed agent arc missing {marker}"

    planner = (ROOT / "governed_agent_arc" / "planner.py").read_text(encoding="utf-8")
    for marker in ("ScriptedPlanner", "METATATE_EXAMPLES_LLM", "requirements-llm.txt"):
        assert marker in planner, f"arc planner missing {marker}"

    acceptance = (ROOT / "governed_agent_arc" / "acceptance.py").read_text(encoding="utf-8")
    for marker in (
        "EXPECTED_SEQUENCE",
        "resumed_with_controls",
        "rerouted_to_governed_alternative",
        "ScriptedPlanner",
    ):
        assert marker in acceptance, f"arc acceptance missing {marker}"

    runner = (ROOT / "scripts" / "run_governed_agent_arc.sh").read_text(encoding="utf-8")
    assert "python3 -m governed_agent_arc.cli" in runner, "arc runner does not call the CLI"
    acceptance_runner = (ROOT / "scripts" / "run_governed_agent_arc_acceptance.sh").read_text(
        encoding="utf-8"
    )
    assert "governed_agent_arc/acceptance.py" in acceptance_runner, "arc acceptance runner missing script"


def validate_readme_hero() -> None:
    # The hero SVG is a generated artifact quoting recorded arc answers; like
    # the notebooks, drift from its generator is a validation failure.
    check = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_readme_hero.py"), "--check"],
        capture_output=True,
        text=True,
    )
    assert check.returncode == 0, (
        "docs/assets/readme-hero.svg drifted from scripts/build_readme_hero.py:\n"
        f"{check.stdout}{check.stderr}"
    )


def validate_ci_workflows() -> None:
    offline = (ROOT / ".github" / "workflows" / "offline-ci.yml").read_text(encoding="utf-8")
    for marker in (
        "scripts/validate_examples.py",
        "scripts/run_cicd_policy_gate_acceptance.sh",
        "scripts/run_cicd_dbt_adapter_acceptance.sh",
        "scripts/run_human_exception_workflow_acceptance.sh",
        "scripts/run_audit_evidence_acceptance.sh",
        "scripts/run_governed_agent_arc_acceptance.sh",
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
        "scripts/run_cicd_dbt_adapter_acceptance.sh",
        "scripts/run_human_exception_workflow_acceptance.sh",
        "scripts/run_audit_evidence_acceptance.sh",
        "scripts/run_governed_agent_arc_acceptance.sh",
        "scripts/run_framework_runtime_acceptance.sh",
        "scripts/run_notebook_pack.sh",
        "scripts/run_langgraph_runtime_notebook.sh",
    ):
        assert marker in saas, f"live SaaS MCP workflow missing {marker}"

    client = (ROOT / "common" / "saas_client.py").read_text(encoding="utf-8")
    for marker in ("MetatateCloudClient", "residency.cross_border_transfer"):
        assert marker in client, f"saas client missing {marker}"
    transport = (ROOT / "common" / "metatate_client.py").read_text(encoding="utf-8")
    assert "structuredContent" in transport, "transport missing structuredContent handling"
    factory = (ROOT / "common" / "metatate_client.py").read_text(encoding="utf-8")
    assert "METATATE_MCP_BACKEND" in factory, "get_client missing the backend selector"


def validate_python_imports() -> None:
    sys.path.insert(0, str(ROOT))
    common = importlib.import_module("common")
    for name in ("OfflineMetatateClient", "ManagedMCPMetatateClient", "MetatateCloudClient", "get_client"):
        assert hasattr(common, name), f"common missing {name}"
    cicd_policy_gate = importlib.import_module("cicd_policy_gate")
    for name in ("evaluate_changes", "load_changes", "DEFAULT_CHANGESET_PATH"):
        assert hasattr(cicd_policy_gate, name), f"cicd_policy_gate missing {name}"
    human_exception_workflow = importlib.import_module("human_exception_workflow")
    for name in ("run_workflow", "DEFAULT_REQUESTS", "DEFAULT_REVIEWS", "item_from_answer"):
        assert hasattr(human_exception_workflow, name), f"human_exception_workflow missing {name}"
    governed_agent_arc = importlib.import_module("governed_agent_arc")
    for name in ("run_arc", "build_governed_agent_arc", "ScriptedPlanner", "ARC_BRIEF"):
        assert hasattr(governed_agent_arc, name), f"governed_agent_arc missing {name}"


if __name__ == "__main__":
    main()
