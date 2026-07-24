#!/usr/bin/env python3
"""dbt adapter for the Metatate CI/CD policy gate — manifest in, change set out.

Consumes dbt artifacts as PLAIN JSON (no dbt dependency anywhere): point it at
``target/manifest.json`` and it emits the gate's change-set format
(`cicd_policy_gate.gate.load_changes`). Three selection modes:

* **full** (default): every enabled, non-ephemeral model and every annotated
  exposure;
* ``--previous-manifest``: checksum diff — models whose checksum changed or
  that are new, plus exposures that changed or whose upstream models did;
* ``--changed-files``: a newline-separated file list (e.g.
  ``git diff --name-only``) matched against ``original_file_path`` /
  ``patch_path``.

Models become ``sql_model`` changes (compiled SQL preferred, raw as fallback;
the node's own ``database``/``schema`` become the validation defaults; a
``meta.metatate.scenario_key`` overrides the analytics-intent default).
Exposures become authorize-kind changes ONLY when annotated with
``meta.metatate`` — dbt has no native destination or jurisdiction concepts,
so the adapter never guesses a transfer context. Every considered-but-not-
gated model or exposure lands in the skip report: no silent coverage holes.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

MODEL_DEFAULT_SCENARIO = "purpose.allowed_use"
AUTHORIZE_KINDS = {"export_job", "ai_training_job", "tool_use", "data_job"}
AUTHORIZE_PASSTHROUGH_KEYS = (
    "use",
    "scenario_key",
    "operation",
    "destination",
    "consumer_jurisdiction",
)


def load_manifest(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} is not a dbt manifest object")
    return payload


def _merged_meta(entry: dict[str, Any]) -> dict[str, Any]:
    """dbt has historically surfaced meta on the node and under config."""

    merged: dict[str, Any] = {}
    for source in (entry.get("meta"), (entry.get("config") or {}).get("meta")):
        if isinstance(source, dict):
            merged.update(source)
    return merged


def _metatate_meta(entry: dict[str, Any]) -> dict[str, Any]:
    value = _merged_meta(entry).get("metatate")
    return value if isinstance(value, dict) else {}


def _sql_of(node: dict[str, Any]) -> str | None:
    # Field names across manifest schema versions (v7-v12).
    for key in ("compiled_code", "compiled_sql", "raw_code", "raw_sql"):
        value = node.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _paths_of(entry: dict[str, Any]) -> set[str]:
    paths = set()
    for key in ("original_file_path", "patch_path"):
        value = entry.get(key)
        if isinstance(value, str) and value:
            # patch_path carries a project scheme ("project://models/x.yml").
            paths.add(value.split("://", 1)[1] if "://" in value else value)
    return paths


def _checksum_of(node: dict[str, Any]) -> str | None:
    checksum = node.get("checksum")
    if isinstance(checksum, dict):
        value = checksum.get("checksum")
        return str(value) if value else None
    return None


def changed_resource_ids(
    current: dict[str, Any],
    previous: dict[str, Any] | None = None,
    changed_files: list[str] | None = None,
) -> set[str] | None:
    """The unique_ids the diff selects; None means "gate everything"."""

    if previous is None and changed_files is None:
        return None

    selected: set[str] = set()
    previous_nodes = (previous or {}).get("nodes") or {}
    previous_exposures = (previous or {}).get("exposures") or {}
    files = {entry.strip() for entry in (changed_files or []) if entry.strip()}

    for unique_id, node in (current.get("nodes") or {}).items():
        if node.get("resource_type") != "model":
            continue
        if previous is not None:
            before = previous_nodes.get(unique_id)
            if before is None or _checksum_of(before) != _checksum_of(node):
                selected.add(unique_id)
        if files and files & _paths_of(node):
            selected.add(unique_id)

    for unique_id, exposure in (current.get("exposures") or {}).items():
        if previous is not None:
            before = previous_exposures.get(unique_id)
            if before is None or before != exposure:
                selected.add(unique_id)
            else:
                upstream = set((exposure.get("depends_on") or {}).get("nodes") or [])
                if upstream & selected:
                    # An exposure inherits change when its models changed —
                    # a design choice, not a dbt standard; meta.metatate.skip
                    # is the opt-out.
                    selected.add(unique_id)
        if files and files & _paths_of(exposure):
            selected.add(unique_id)

    return selected


def change_for_model(node: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    config = node.get("config") or {}
    if config.get("enabled") is False:
        return None, "model is disabled"
    if str(config.get("materialized") or "").lower() == "ephemeral":
        return None, "ephemeral model (no queryable relation to govern)"
    if _metatate_meta(node).get("skip") is True:
        return None, "meta.metatate.skip"
    sql = _sql_of(node)
    if sql is None:
        return None, "model without SQL"

    name = str(node.get("name") or node.get("unique_id") or "model")
    scenario_key = _metatate_meta(node).get("scenario_key") or MODEL_DEFAULT_SCENARIO
    change: dict[str, Any] = {
        "change_id": f"dbt-{name}",
        "kind": "sql_model",
        "source_path": node.get("original_file_path"),
        "description": str(node.get("description") or f"dbt model {name}"),
        "sql": sql,
        "scenario_key": scenario_key,
    }
    if node.get("database"):
        change["default_database"] = node["database"]
    if node.get("schema"):
        change["default_schema"] = node["schema"]
    return change, None


def change_for_exposure(exposure: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    annotation = _metatate_meta(exposure)
    if annotation.get("skip") is True:
        return None, "meta.metatate.skip"
    if not annotation:
        return None, "exposure without a meta.metatate annotation"
    kind = annotation.get("kind")
    if kind not in AUTHORIZE_KINDS:
        return None, f"unsupported meta.metatate.kind {kind!r}"
    asset = annotation.get("asset")
    if not isinstance(asset, dict):
        return None, "meta.metatate annotation without an asset reference"

    name = str(exposure.get("name") or exposure.get("unique_id") or "exposure")
    change: dict[str, Any] = {
        "change_id": f"dbt-exposure-{name}",
        "kind": kind,
        "source_path": exposure.get("original_file_path"),
        "description": str(exposure.get("description") or exposure.get("label") or name),
        "asset": asset,
    }
    for key in AUTHORIZE_PASSTHROUGH_KEYS:
        if annotation.get(key) is not None:
            change[key] = annotation[key]
    return change, None


def build_change_set(
    current: dict[str, Any],
    previous: dict[str, Any] | None = None,
    changed_files: list[str] | None = None,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Return (gate change set, skip report).

    The skip report covers models and exposures that were CONSIDERED but not
    gated (disabled/ephemeral/un-annotated/opted out); non-model resources
    (tests, seeds, snapshots, macros) are out of scope by definition.
    """

    selected = changed_resource_ids(current, previous, changed_files)
    changes: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []

    for unique_id, node in (current.get("nodes") or {}).items():
        if node.get("resource_type") != "model":
            continue
        if selected is not None and unique_id not in selected:
            continue
        change, reason = change_for_model(node)
        if change is None:
            skipped.append({"unique_id": unique_id, "reason": str(reason)})
        else:
            changes.append(change)

    for unique_id, exposure in (current.get("exposures") or {}).items():
        if selected is not None and unique_id not in selected:
            continue
        change, reason = change_for_exposure(exposure)
        if change is None:
            skipped.append({"unique_id": unique_id, "reason": str(reason)})
        else:
            changes.append(change)

    project = (current.get("metadata") or {}).get("project_name") or "dbt-project"
    mode = "full manifest" if selected is None else f"{len(selected)} changed resources"
    change_set = {
        "change_set_id": f"dbt-{project}",
        "description": f"dbt change set from {project} ({mode}).",
        "changes": changes,
    }
    return change_set, skipped


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a dbt manifest into a Metatate policy-gate change set."
    )
    parser.add_argument("--manifest", required=True, help="Path to dbt target/manifest.json.")
    parser.add_argument(
        "--previous-manifest",
        help="Optional previous manifest.json; only checksum-changed models (and their exposures) are gated.",
    )
    parser.add_argument(
        "--changed-files",
        help="Optional path to a newline-separated changed-file list (e.g. from git diff --name-only).",
    )
    parser.add_argument(
        "--output",
        default=str(Path(tempfile.gettempdir()) / "metatate-dbt-changes.json"),
        help="Where to write the gate change-set JSON.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    current = load_manifest(args.manifest)
    previous = load_manifest(args.previous_manifest) if args.previous_manifest else None
    changed_files = None
    if args.changed_files:
        changed_files = Path(args.changed_files).read_text(encoding="utf-8").splitlines()

    change_set, skipped = build_change_set(current, previous, changed_files)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(change_set, indent=2) + "\n", encoding="utf-8")

    models = sum(1 for change in change_set["changes"] if change["kind"] == "sql_model")
    exposures = len(change_set["changes"]) - models
    print(
        f"dbt adapter: {len(change_set['changes'])} gate changes "
        f"({models} models, {exposures} exposures), {len(skipped)} skipped"
    )
    for entry in skipped:
        print(f"  skipped {entry['unique_id']}: {entry['reason']}")
    print(f"Wrote gate change set to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
