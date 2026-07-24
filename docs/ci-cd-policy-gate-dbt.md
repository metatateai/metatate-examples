# Governance In The Pull Request: dbt + The Metatate Gate Action

The CI/CD policy gate consumes a change-set JSON. For dbt projects you never
write that JSON by hand: `cicd_policy_gate/dbt_adapter.py` generates it from
`target/manifest.json`, and the repo root ships a reusable composite GitHub
Action (`action.yml`) that runs adapter → gate → job summary → PR comment in
one step. Platform engineers get typed governance verdicts where they already
work: the pull request.

## What the adapter maps

- **Models → `sql_model` changes.** Compiled SQL preferred (raw as fallback);
  the node's own `database`/`schema` become the validation defaults, so refs
  resolve exactly as the model would run. The default intent is
  `purpose.allowed_use`; a model can declare its honest intent via
  `meta.metatate.scenario_key` (the sample project's marketing model asks as
  `purpose.prohibited_use` — and fails, instead of passing under an analytics
  intent it doesn't have).
- **Exposures → authorize-kind changes, only when annotated.** dbt has no
  destination or jurisdiction concepts, so nothing is guessed: an exposure is
  gated only if it carries `meta.metatate` with `kind`
  (`export_job` / `ai_training_job` / `tool_use` / `data_job`), an `asset`,
  and whatever transfer context applies. The sample project's Salesforce sync
  earns its `conditional`; the fine-tune exposure earns its `deny`.
- **Nothing is skipped silently.** Disabled/ephemeral models, opted-out
  resources (`meta.metatate.skip: true`), and un-annotated exposures land in
  a skip report the adapter prints.

## Selection modes

```bash
# full manifest
python3 -m cicd_policy_gate.dbt_adapter --manifest target/manifest.json --output changes.json

# checksum diff against the previous run's manifest
python3 -m cicd_policy_gate.dbt_adapter --manifest target/manifest.json \
  --previous-manifest previous/manifest.json --output changes.json

# changed-files list (e.g. from git diff --name-only origin/main... > changed.txt)
python3 -m cicd_policy_gate.dbt_adapter --manifest target/manifest.json \
  --changed-files changed.txt --output changes.json
```

Diff mode also pulls in an annotated exposure when any model it depends on
changed — a design choice (an unchanged sync over changed data is still a
release decision), with `meta.metatate.skip` as the opt-out.

## The reusable GitHub Action

```yaml
name: metatate-gate
on: pull_request

permissions:
  contents: read
  pull-requests: write   # for the verdict comment

jobs:
  gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: dbt compile   # or restore target/manifest.json from your build
      - uses: metatateai/metatate-examples@main   # pin a release tag in practice
        with:
          dbt-manifest: target/manifest.json
          mcp-url: ${{ secrets.METATATE_MCP_URL }}
          mcp-token: ${{ secrets.METATATE_SAAS_MCP_TOKEN }}
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

What you get on every PR: a job-summary verdict table (gate, decision, reason
codes, Metatate evidence id per change), an upserted PR comment with the same
table, and — with `strict: "true"` (the default) — a failed job when the
release is not allowed. `fail-on-controls: "true"` additionally blocks on
`needs_controls` (conditional/masking) verdicts. The enforcement step runs
LAST, so the comment and summary always post before the job fails.

Notes:

- On forked PRs `GITHUB_TOKEN` is read-only — the comment step degrades
  (skip `github-token` there); the summary and strict gate still work.
- `mode: offline` replays the recorded AcmeCloud fixtures — demo/smoke only
  (the repo's own CI smoke-tests the action this way, asserting the sample
  project's release is refused).

## The sample project

`cicd_policy_gate/dbt_project/` is a tiny runnable dbt project over the
AcmeCloud schema whose models use bare table names, so raw SQL == compiled
SQL == the recorded fixture strings — the whole flow replays offline with
zero new fixtures. `artifacts/manifest.json` and
`artifacts/manifest_previous.json` are checked-in manifest fixtures (only the
keys the adapter reads), so CI needs no dbt install; regenerate them with
real dbt via `dbt compile` against any profile targeting
`acmecloud_demo.public`.

Acceptance: `scripts/run_cicd_dbt_adapter_acceptance.sh` pins the adapter's
full/diff/changed-files selections, the byte-equality of model SQL with the
recorded cases, the end-to-end gate matrix (1 pass · 2 needs_controls ·
2 fail · release refused), the skip report, and the markdown renderer.
