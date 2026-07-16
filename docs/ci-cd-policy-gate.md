# CI/CD Policy Gate

This example shows how to put Metatate in the delivery path for data and AI changes.

The gate reads a pull-request-style JSON change set, calls Metatate for each change, and emits a machine-readable report with the decision, required controls, rationale, and evidence ID.

## What It Checks

The sample change set is `cicd_policy_gate/changes/pull_request_042.json`.

It includes:

- an aggregate SQL model that should pass
- an analytics SQL model that selects identifiers and should require controls
- a direct marketing SQL model that should fail
- a Salesforce export job that should require controls
- an AI training job on support tickets that should fail

SQL changes call `validate-query-context`. Export, training, and tool-use changes call `authorize-use`.

## Run Locally

```bash
scripts/run_cicd_policy_gate.sh
```

The default run prints a summary and writes a JSON report to the system temporary directory, for example `/tmp/metatate-cicd-policy-gate-report.json`.

To use a different change set:

```bash
scripts/run_cicd_policy_gate.sh --changes path/to/changes.json
```

## Strict CI Mode

Strict mode returns a non-zero exit code when denied or unknown-review changes are present.

```bash
scripts/run_cicd_policy_gate.sh --strict
```

To also block conditional decisions until controls are resolved:

```bash
scripts/run_cicd_policy_gate.sh --strict --fail-on-controls
```

Equivalent environment variables:

```bash
export METATATE_CI_GATE_STRICT=1
export METATATE_CI_GATE_FAIL_ON_CONTROLS=1
```

## Live MCP Mode

Offline mode uses committed fixtures. Live mode sends every decision request to your Metatate Cloud workspace's MCP endpoint.

```bash
export METATATE_EXAMPLES_MODE=live
export METATATE_MCP_URL=https://<your-workspace-mcp-endpoint>/mcp
export METATATE_SAAS_MCP_TOKEN=mtt_...

scripts/run_cicd_policy_gate.sh --strict
```

Use a workspace-issued MCP access token (MCP module → Tokens). See `docs/live-mode-saas.md`.

## GitHub Actions Shape

```yaml
name: Metatate policy gate

on:
  pull_request:
    paths:
      - "models/**/*.sql"
      - "jobs/**/*.yaml"
      - "pipelines/**/*.yaml"

jobs:
  policy-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements-live.txt
      - run: scripts/run_cicd_policy_gate.sh --strict
        env:
          METATATE_EXAMPLES_MODE: live
          METATATE_MCP_URL: ${{ secrets.METATATE_MCP_URL }}
          METATATE_SAAS_MCP_TOKEN: ${{ secrets.METATATE_SAAS_MCP_TOKEN }}
```

Teams usually generate the change-set JSON from dbt model diffs, migration files, export-job definitions, or agent workflow manifests before this step runs.

## Report Fields

Each result includes:

- `change_id`
- `kind`
- `source_path`
- `decision`
- `gate`
- `evidence_id`
- `reason_codes`
- `required_controls`
- `action`
- `rationale`

Store the report as a CI artifact so release decisions can be traced back to the Metatate evidence ID.
