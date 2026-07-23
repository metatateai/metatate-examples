# Live Mode (Metatate Cloud)

Metatate Cloud exposes the seven governance tools at a single `POST /mcp`
endpoint with plain bearer-token auth. This repo's live mode runs every
notebook, gate, and acceptance script against it — same `get_client()` seam,
no notebook changes.

Metatate Cloud speaks the typed-answer contract (snake_case keys, structured
`asset {database, schema, table, column?}` references, typed
`answered / review_required / not_enough_published_state` states,
destination-aware transfer authorization). `common/saas_client.py` is NATIVE:
it passes those arguments through verbatim and returns each tool's typed
answer untouched — and the offline recordings replay the same shapes, so
offline output is byte-shaped like the live endpoint's.

## Environment

```bash
export METATATE_EXAMPLES_MODE=live
export METATATE_MCP_URL=https://<your-workspace-mcp-host>/mcp   # full path incl. /mcp
export METATATE_SAAS_MCP_TOKEN=mtt_...    # MCP module → Tokens (shown once)
```

`METATATE_MCP_BACKEND=saas` is the default (and the only backend in this
repo); exporting it is harmless but no longer required.

Optional: `METATATE_MCP_TOKEN_ENV` renames the token variable;
`METATATE_SAAS_DEFAULT_DATABASE` / `METATATE_SAAS_DEFAULT_SCHEMA` (default
`acmecloud_demo` / `public`) qualify 1- and 2-part table names.

## Demo state

The workspace must serve the AcmeCloud demo publication.

**Self-serve (recommended):** create a free account at
[app.getmetatate.com/sign-up?ref=examples](https://app.getmetatate.com/sign-up?ref=examples)
and create a workspace. On the workspace dashboard, follow the **"New here?"
banner → Load the demo**, then click **Load the AcmeCloud demo**. It
provisions the whole domain (a sample connector that never syncs, the three
AcmeCloud policies, and a live publication) and is fully reversible via
"Remove demo". Then issue a token in **MCP Tools → Tokens**, copy the
endpoint from **MCP Tools → Connect**, and export the environment above.

**Local stack (contributors / operators):** in the metatate-saas repo:

```bash
pnpm db:start                       # or pnpm db:reset for a clean slate
./scripts/acmecloud-demo-fixtures.sh    # publishes the AcmeCloud governed domain
export METATATE_SAAS_MCP_TOKEN="$(psql postgres://postgres:postgres@127.0.0.1:54322/postgres -Atc \
  "select 'mtt_' || encode(extensions.digest('metatate-seed-mcp-token:acmecloud-demo-mcp','sha256'),'hex')")"
PORT=3200 pnpm --filter mcp-server dev  # needs SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY
export METATATE_MCP_URL=http://localhost:3200/mcp
```

For staging, an operator applies the same fixture script once against the
staging database and a workspace admin issues a real token — never reuse the
deterministic local one.

## Run

```bash
scripts/run_cicd_policy_gate_acceptance.sh
scripts/run_human_exception_workflow_acceptance.sh
scripts/run_framework_runtime_acceptance.sh    # needs Python 3.10+
scripts/run_notebook_pack.sh                   # notebooks 00–12, except 11
scripts/run_langgraph_runtime_notebook.sh      # notebook 11 (framework deps)
```

CI: `.github/workflows/live-saas-mcp-validation.yml`
(workflow_dispatch; secrets `METATATE_SAAS_MCP_URL`, `METATATE_SAAS_MCP_TOKEN`).

## Semantics worth knowing

- **Scenario routing.** The notebooks pass canonical scenario keys explicitly
  (`purpose.allowed_use`, `ai.training`, `residency.cross_border_transfer`, …).
  Omit `scenario_key` and the SERVER's deterministic mapper resolves your
  free-text `use`; a use it cannot map is the typed `scenario_unresolved`
  answer — never a guess.
- **Destination-aware exports.** `destination {system, jurisdiction}`,
  `consumer_jurisdiction`, and `operation` flow to the server, which evaluates
  the authored transfer rules per destination (SALESFORCE → CONDITIONAL with
  approval + anonymization, ADS_PLATFORM / EXTERNAL_LLM_VENDOR → deny on the
  AcmeCloud policy).
- **`explain_why` chains natively.** `data.decision_id` on authorize answers
  is the real serving-row uuid; `explain_why(decision_id=...)` resolves it
  server-side. Validation records have no server-side explain surface.
- **Query validation is server-verdict.** Validation is intent- and
  column-aware; the typed answer carries `verdict: pass | warn | fail` plus
  per-ref findings citing the participating instructions. The server keeps no
  validation records (only authorize `decision_id`s are explainable).
- **Offline parity.** `scripts/record_offline_fixtures.py` replays the
  canonical case set (`common/fixture_cases.py`) against a live workspace and
  commits the typed answers — uuid-normalized but internally consistent, so
  `decision_id` chaining into `explain_why` works offline too.

## Errors

- `401 unauthorized` — token missing/expired/revoked (uniform response;
  re-issue in the MCP module). Token format: `mtt_` + 64 hex chars.
- `429` — per-token rate limit; the client honors `Retry-After`.
- `asset_not_found` — identifiers are lowercase normalized names; check the
  demo fixture was applied to the workspace you are calling.
- `not_enough_published_state` — no current publication for that asset;
  publish the demo state (or your own policies) first.
