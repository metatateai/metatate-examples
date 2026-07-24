#!/usr/bin/env python3
"""Acceptance checks for the dbt adapter + markdown renderer.

Pins the adapter's output on the committed fixture manifests and proves the
end-to-end flow reproduces the canonical pr-042 gate matrix from recorded
answers. The byte-equality assertions are the offline-replay canary: if a
fixture model's SQL drifts from the recorded case strings, offline mode would
raise the typed offline_fixture_missing error.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common import get_client  # noqa: E402
from cicd_policy_gate.dbt_adapter import build_change_set, load_manifest  # noqa: E402
from cicd_policy_gate.gate import evaluate_changes  # noqa: E402
from cicd_policy_gate.report_to_markdown import render, worst_gate  # noqa: E402
from framework_runtime.scenarios import (  # noqa: E402
    MARKETING_SQL,
    SAFE_ANALYTICS_SQL,
    UNSAFE_ANALYTICS_SQL,
)

ARTIFACTS = ROOT / "cicd_policy_gate" / "dbt_project" / "artifacts"


def main() -> int:
    current = load_manifest(ARTIFACTS / "manifest.json")
    previous = load_manifest(ARTIFACTS / "manifest_previous.json")

    # ---- full mode: every gateable model + annotated exposure ---------------
    change_set, skipped = build_change_set(current)
    ids = [change["change_id"] for change in change_set["changes"]]
    assert ids == [
        "dbt-customer_arr_by_region",
        "dbt-eu_customer_arr_detail",
        "dbt-active_customer_activation",
        "dbt-exposure-salesforce_customer_sync",
        "dbt-exposure-support_assistant_finetune",
    ], f"unexpected full-mode change ids: {ids}"

    by_id = {change["change_id"]: change for change in change_set["changes"]}
    # Byte-equality with the recorded fixture SQL — the offline-replay canary.
    assert by_id["dbt-customer_arr_by_region"]["sql"] == SAFE_ANALYTICS_SQL
    assert by_id["dbt-eu_customer_arr_detail"]["sql"] == UNSAFE_ANALYTICS_SQL
    assert by_id["dbt-active_customer_activation"]["sql"] == MARKETING_SQL
    assert by_id["dbt-active_customer_activation"]["scenario_key"] == "purpose.prohibited_use"
    assert by_id["dbt-eu_customer_arr_detail"]["scenario_key"] == "purpose.allowed_use"
    assert by_id["dbt-eu_customer_arr_detail"]["default_database"] == "acmecloud_demo"
    assert by_id["dbt-eu_customer_arr_detail"]["default_schema"] == "public"
    assert by_id["dbt-exposure-salesforce_customer_sync"]["kind"] == "export_job"
    assert by_id["dbt-exposure-salesforce_customer_sync"]["destination"] == {
        "system": "SALESFORCE",
        "jurisdiction": "US",
    }
    assert by_id["dbt-exposure-support_assistant_finetune"]["kind"] == "ai_training_job"

    # The skip report: the ephemeral model and the un-annotated exposure.
    skip_reasons = {entry["unique_id"]: entry["reason"] for entry in skipped}
    assert "model.acmecloud_analytics.stg_customers_ephemeral" in skip_reasons
    assert "ephemeral" in skip_reasons["model.acmecloud_analytics.stg_customers_ephemeral"]
    assert "exposure.acmecloud_analytics.weekly_kpi_email" in skip_reasons
    assert "meta.metatate" in skip_reasons["exposure.acmecloud_analytics.weekly_kpi_email"]
    assert len(skipped) == 2, f"unexpected skips: {skipped}"

    # ---- end to end: the adapter output reproduces the pr-042 gate matrix ---
    summary = evaluate_changes(get_client(), change_set)
    assert (summary.passed, summary.needs_controls, summary.failed, summary.needs_review) == (
        1,
        2,
        2,
        0,
    ), f"unexpected gate matrix: {summary}"
    assert summary.release_allowed is False

    codes = {result.change_id: set(result.reason_codes) for result in summary.results}
    assert codes["dbt-customer_arr_by_region"] == {"NO_RESTRICTED_USE_DETECTED"}
    assert codes["dbt-eu_customer_arr_detail"] == {"MASKING_REQUIRED"}
    # The marketing model earns BOTH codes: the prohibited use denies it, and
    # the referenced email column's mask row participates (ADR-0011).
    assert codes["dbt-active_customer_activation"] == {"PROHIBITED_USE", "MASKING_REQUIRED"}
    assert codes["dbt-exposure-salesforce_customer_sync"] == {
        "TRANSFER_CONDITIONAL",
        "APPROVAL_REQUIRED",
        "ANONYMIZATION_REQUIRED",
    }
    assert codes["dbt-exposure-support_assistant_finetune"] == {"AI_TRAINING_BLOCKED"}
    for result in summary.results:
        assert result.evidence_id, f"{result.change_id} has no evidence id"

    # ---- diff mode: exactly the changed models + the exposure they feed -----
    diff_set, _diff_skipped = build_change_set(current, previous=previous)
    diff_ids = sorted(change["change_id"] for change in diff_set["changes"])
    assert diff_ids == [
        "dbt-active_customer_activation",
        "dbt-eu_customer_arr_detail",
        "dbt-exposure-salesforce_customer_sync",
    ], f"unexpected diff-mode ids: {diff_ids}"

    # ---- changed-files mode --------------------------------------------------
    files_set, _files_skipped = build_change_set(
        current, changed_files=["models/marketing/active_customer_activation.sql"]
    )
    files_ids = [change["change_id"] for change in files_set["changes"]]
    assert files_ids == ["dbt-active_customer_activation"], f"unexpected ids: {files_ids}"

    # ---- markdown renderer ----------------------------------------------------
    markdown = render(summary.to_dict())
    assert "| `dbt-active_customer_activation` |" in markdown
    assert "release allowed: **false**" in markdown
    assert "PROHIBITED_USE" in markdown
    assert worst_gate(summary.to_dict()) == "fail"

    print("dbt adapter acceptance passed")
    print(f"  full: {ids}")
    print(f"  diff: {diff_ids}")
    print(
        f"  matrix: pass={summary.passed} needs_controls={summary.needs_controls} "
        f"fail={summary.failed} release_allowed={summary.release_allowed}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
