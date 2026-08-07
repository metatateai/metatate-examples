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
        "scripts/purpose_contract_acceptance.py",
        "scripts/build_purpose_manifest.py",
        "scripts/live_expected_decision_parity.py",
        "sample-data/customer-360/purpose-mapping-manifest.json",
        "docs/b3-purpose-conversion.md",
        "scripts/run_purpose_contract_acceptance.sh",
        "docs/live-mode-saas.md",
        "README.md",
        "docs/demo-data-model.md",
        "docs/ci-cd-policy-gate.md",
        "docs/human-exception-workflow.md",
        "docs/release-process.md",
        "docs/validation-matrix.md",
        "sample-data/customer-360/catalog.yaml",
        "sample-data/customer-360/expected-decisions.yaml",
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
        "starter-policies/starter-email-masking.yaml",
        "starter-policies/starter-pii-usage-guardrails.yaml",
        "starter-policies/starter-ai-training-default-deny.yaml",
        "starter-policies/starter-transfer-default-conditional.yaml",
        "scripts/bootstrap_check.py",
        "docs/walkthrough-byo-estate.md",
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
        "request_lifecycle/__init__.py",
        "request_lifecycle/workflow.py",
        "request_lifecycle/cli.py",
        "request_lifecycle/acceptance.py",
        "docs/request-access-lifecycle.md",
        "scripts/run_request_lifecycle_acceptance.sh",
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
    validate_request_lifecycle_files()
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

    fixture_dir = ROOT / "sample-data" / "customer-360" / "metatate-responses"
    by_id = {str(case["id"]): case for case in CASES}
    recorded = set()
    for path in fixture_dir.glob("*.json"):
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        assert set(payload) == {"case_id", "tool", "arguments", "answer"}, (
            f"{path} must use the native Cloud recording wrapper; "
            f"got keys {sorted(payload)}"
        )
        assert payload["case_id"] == path.stem, f"{path} case_id mismatch"
        assert path.stem in by_id, f"orphan recording without canonical case: {path.stem}"
        assert payload["tool"] == by_id[path.stem]["tool"], f"{path} tool mismatch"
        serialized = json.dumps(payload, sort_keys=True)
        assert '"snapshot_id"' not in serialized, f"{path} uses the retired snapshot envelope"
        assert '"agent_action"' not in serialized, f"{path} uses the retired agent_action envelope"

        answer = payload["answer"]
        assert isinstance(answer, dict), f"{path} answer must be an object"

        def assert_pinned_evaluated_at(value: object) -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    if key == "evaluated_at" and isinstance(child, str):
                        assert child == "2026-07-30T00:00:00.000Z", (
                            f"{path} has an unnormalized evaluated_at"
                        )
                    assert_pinned_evaluated_at(child)
            elif isinstance(value, list):
                for child in value:
                    assert_pinned_evaluated_at(child)

        assert_pinned_evaluated_at(answer)
        tool = str(payload["tool"])
        required_by_tool = {
            "discover_context": {"state", "assets", "publication", "next_cursor"},
            "get_decision_context": {
                "state", "asset", "decisions", "effective_decision", "publication"
            },
            "inspect_data_meaning": {"ref", "meaning", "classification", "pii"},
            "inspect_governance_rules": {"state", "asset", "rules", "publication"},
            "authorize_use": {
                "state", "advisory", "asset", "authorization_id", "evaluated_at",
                "evaluated_purpose", "satisfied_conditions"
            },
            "validate_query_context": {
                "state", "advisory", "verdict", "validation_id", "findings",
                "publication", "evaluated_purpose"
            },
        }
        if tool in required_by_tool:
            missing_keys = required_by_tool[tool] - set(answer)
            assert not missing_keys, f"{path} missing current Cloud fields {sorted(missing_keys)}"
        elif tool == "explain_why":
            kind = payload["arguments"].get("kind")
            explain_required = {
                "decision": {"state", "current", "record", "publication", "explanation"},
                "authorization": {
                    "kind", "authorization_id", "answer_state", "evaluated",
                    "cited_decision_ids", "provenance"
                },
                "validation": {
                    "kind", "validation_id", "answer_state", "verdict", "findings",
                    "purpose_context", "provenance"
                },
            }
            assert kind in explain_required, f"{path} has unknown explain kind {kind!r}"
            missing_keys = explain_required[kind] - set(answer)
            assert not missing_keys, f"{path} missing {kind} explain fields {sorted(missing_keys)}"
            if kind != "decision":
                assert answer.get("kind") == kind, f"{path} explain discriminator mismatch"
        else:
            raise AssertionError(f"{path} records unknown tool {tool!r}")
        recorded.add(path.stem)
    missing = {str(case["id"]) for case in CASES} - recorded
    assert not missing, f"cases without recordings: {sorted(missing)}"
    assert len(recorded) == len(CASES), "recording count must equal canonical case count"


def validate_csv_files() -> None:
    for path in (ROOT / "sample-data" / "customer-360" / "tables").glob("*.csv"):
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert rows, f"{path} has no rows"


def validate_policy_files() -> None:
    for path in (ROOT / "sample-data" / "customer-360" / "policies").glob("*.yaml"):
        text = path.read_text(encoding="utf-8")
        for marker in ("apiVersion: metatate.io/v1", "kind: DataPolicy", "spec:", "selector:"):
            assert marker in text, f"{path} missing {marker}"
    # The starter pack must stay valid DataPolicy documents AND estate-agnostic
    # (taxonomy-targeted — no databases/schemas/tables baked in).
    starter_paths = sorted((ROOT / "starter-policies").glob("*.yaml"))
    assert len(starter_paths) == 4, "expected four starter policies"
    for path in starter_paths:
        text = path.read_text(encoding="utf-8")
        for marker in (
            "apiVersion: metatate.io/v1",
            "kind: DataPolicy",
            "selector:",
            "taxonomyTypes:",
        ):
            assert marker in text, f"{path} missing {marker}"
        for forbidden in ("databases:", "schemas:", "tables:"):
            assert forbidden not in text, f"{path} must stay estate-agnostic ({forbidden})"


def validate_notebooks() -> None:
    notebooks = sorted((ROOT / "notebooks").glob("*.ipynb"))
    assert len(notebooks) == 17, "expected seventeen starter notebooks"
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
        "Activity → Audit trail",
        "Tokens → View requests",
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


def validate_request_lifecycle_files() -> None:
    workflow = (ROOT / "request_lifecycle" / "workflow.py").read_text(encoding="utf-8")
    for marker in (
        "Type START",
        "REQUEST {authorization_id}",
        "request_access",
        "check_request",
        "satisfied_conditions",
        "Activity > Review requests",
    ):
        assert marker in workflow, f"request lifecycle missing {marker!r}"
    acceptance = (ROOT / "request_lifecycle" / "acceptance.py").read_text(encoding="utf-8")
    for marker in (
        "client.calls == []",
        "not the bound confirmation",
        "explain_why must require exactly one reference",
    ):
        assert marker in acceptance, f"request lifecycle acceptance missing {marker!r}"


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
        "scripts/run_request_lifecycle_acceptance.sh",
        "scripts/run_governed_agent_arc_acceptance.sh",
        "scripts/run_framework_runtime_acceptance.sh",
        "scripts/run_notebook_pack.sh",
    ):
        assert marker in offline, f"offline CI workflow missing {marker}"
    framework_step = offline.index("scripts/run_framework_runtime_acceptance.sh")
    notebook_step = offline.index("scripts/run_notebook_pack.sh")
    action_runtime_step = offline.index("uses: ./")
    assert framework_step < action_runtime_step and notebook_step < action_runtime_step, (
        "the composite policy-gate action provisions Python 3.11 and must run after "
        "the Python 3.12 framework and notebook acceptance suites"
    )

    saas = (ROOT / ".github" / "workflows" / "live-saas-mcp-validation.yml").read_text(encoding="utf-8")
    for marker in (
        "workflow_dispatch",
        "METATATE_MCP_BACKEND: saas",
        "METATATE_SAAS_MCP_TOKEN",
        "scripts/run_cicd_policy_gate_acceptance.sh",
        "scripts/run_cicd_dbt_adapter_acceptance.sh",
        "scripts/run_human_exception_workflow_acceptance.sh",
        "scripts/run_audit_evidence_acceptance.sh",
        "scripts/run_request_lifecycle_acceptance.sh",
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
