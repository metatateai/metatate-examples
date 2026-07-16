# Live Mode (Metatate Cloud)

Metatate Cloud exposes the seven governance tools at a single `POST /mcp`
endpoint with plain bearer-token auth. This repo's live mode runs every
notebook, gate, and acceptance script against it — same `get_client()` seam,
no notebook changes.

The SaaS server speaks the v2 typed-answer contract (snake_case keys,
structured `asset {database, schema, table, column?}` references, typed
`answered / review_required / not_enough_published_state` states,
destination-aware transfer authorization). `common/saas_client.py` translates
the notebooks' v1-style calls onto that contract and maps the typed answers
back to the canonical payload shape. Decisions are always server-derived.

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
scripts/run_notebook_pack.sh                   # notebooks 00–10
scripts/run_langgraph_runtime_notebook.sh      # notebook 11 (framework deps)
```

CI: `.github/workflows/live-saas-mcp-validation.yml`
(workflow_dispatch; secrets `METATATE_SAAS_MCP_URL`, `METATATE_SAAS_MCP_TOKEN`).

## Semantics worth knowing

- **Scenario routing.** The client sends an explicit canonical scenario key
  derived from `operation`/`intended_use` (marketing → `purpose.prohibited_use`,
  train → `ai.training`, export/destination → `residency.cross_border_transfer`,
  analytics/reporting/support → `purpose.allowed_use`). Unmapped intents let
  the server's deterministic mapper decide; a use it cannot map is the typed
  `scenario_unresolved` answer (`UNKNOWN`), never a guess.
- **Destination-aware exports.** `destination {system, jurisdiction}`,
  `consumer_jurisdiction`, and `operation` flow to the server, which evaluates
  the authored transfer rules per destination (SALESFORCE → CONDITIONAL with
  approval + anonymization, ADS_PLATFORM / EXTERNAL_LLM_VENDOR → DENY on the
  AcmeCloud policy). On an older server without those inputs the client
  retries once without them and returns the collapsed transfer verdict.
- **`explain_why` chains natively.** `data.decision_id` on authorize answers
  is the real serving-row uuid; `explain_why(decision_id=...)` resolves it
  server-side. Validation records have no server-side explain surface.
- **Query validation is server-verdict.** The SaaS validate is intent- and
  column-aware; the client passes the intent and reads `pass`/`warn`/`fail`
  as ALLOW/CONDITIONAL/DENY. `validation_id` is client-minted (the server
  keeps no validation records).
- **Discovery enrichment.** `discover_context` / `get_decision_context`
  compose their table summaries from a small fan-out (`inspect_data_meaning`,
  `get_decision_context` per table, cached per client instance) — well under
  the default 120 calls/min token budget. Lineage is empty with a note (not
  part of the SaaS governed context yet).

## Errors

- `401 unauthorized` — token missing/expired/revoked (uniform response;
  re-issue in the MCP module). Token format: `mtt_` + 64 hex chars.
- `429` — per-token rate limit; the client honors `Retry-After`.
- `asset_not_found` — identifiers are lowercase normalized names; check the
  demo fixture was applied to the workspace you are calling.
- `not_enough_published_state` — no current publication for that asset;
  publish the demo state (or your own policies) first.
