# Live Mode (Metatate Cloud)

Metatate Cloud exposes **nine** tools at a single `POST /mcp` endpoint with
plain bearer-token auth. **This pack exercises seven context and decision
tools: five pure reads and two advisory tools that record durable, citable
decision evidence** (`authorize_use`, `validate_query_context`). The B1 request
lane (`request_access`, `check_request`) is demonstrated separately by the
explicitly confirmed, live-only request lifecycle; it is never run by the
default notebook or CI pack.

All seven need only the `read` token scope — but **scope is not durable-effect
behaviour**, and the two are easy to conflate. `authorize_use` and
`validate_query_context` write decision records; that is not incidental, it is
the mechanism the audit-evidence example depends on. `explain_why` accepts
exactly one of `decision_id`, `authorization_id`, or `validation_id`, so the
serving-row decision and both durable call receipts can be explained without
conflating their identifiers.

> **If you build on the request lane:** asking the human to confirm before
> calling `request_access` is a **client-side obligation today**. The server
> enforces scope, eligibility, citation and idempotency — it does **not**
> perform elicitation or a two-phase commit, and it will not check that a human
> agreed. Nor is that satisfied by the caller passing something like
> `confirmed: true`: a client asserting its own compliance is not enforcement.
> Build the confirmation into your client.

This repo's live mode runs every notebook, gate, and acceptance script against
the endpoint — same `get_client()` seam, no notebook changes.

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
export METATATE_SAAS_MCP_TOKEN=mtt_...       # {read}; identity-neutral pack
export METATATE_SAAS_MCP_AGENT_TOKEN=mtt_... # {read}; bound role exactly `agent`
# Healthcare four-context notebook (19) — four more {read} tokens, bound
# roles exactly `clinical`, `member_services`, `research`, `marketing`:
export METATATE_SAAS_MCP_CLINICAL_TOKEN=mtt_...
export METATATE_SAAS_MCP_MEMBER_SERVICES_TOKEN=mtt_...
export METATATE_SAAS_MCP_RESEARCH_TOKEN=mtt_...
export METATATE_SAAS_MCP_MARKETING_TOKEN=mtt_...
```

`METATATE_MCP_BACKEND=saas` is the default (and the only backend in this
repo); exporting it is harmless but no longer required.

Notebook 16 and the live expected-decision gate use the second token because
the access-window policy is role-bound. Keeping it separate prevents the
agent identity from silently changing the older identity-neutral cases.
Notebook 19 extends the same pattern to four healthcare roles: each case's
`bound_role` selects the CREDENTIAL (never a tool argument), and the recorder
and parity gate fail closed when a role's token env is missing.

Optional: `METATATE_MCP_PAT_ENV` renames the default token variable;
`METATATE_SAAS_DEFAULT_DATABASE` / `METATATE_SAAS_DEFAULT_SCHEMA` (default
`master` / `public`) qualify 1- and 2-part table names.

## Demo state

The workspace must serve the Customer 360 demo publication.

**Self-serve (recommended):** create a free account at
[app.getmetatate.com/sign-up?ref=examples](https://app.getmetatate.com/sign-up?ref=examples)
and create a workspace. On the workspace dashboard, follow the **"New here?"
banner → Load the demo**, then click **Load the Customer 360 demo**. It
provisions the whole domain (a sample connector that never syncs, the
Customer 360 policies, and a live publication) and is fully reversible via
"Remove demo". Then issue two tokens in **MCP Tools → Tokens**: one ordinary
`{read}` token and one `{read}` token with bound role `agent`. Copy the endpoint
from **MCP Tools → Connect**, and export the environment above.

**Local stack (contributors / operators):** in the metatate-saas repo:

```bash
pnpm db:start                       # or pnpm db:reset for a clean slate
./scripts/customer-360-demo-fixtures.sh    # publishes the Customer 360 governed domain
export METATATE_SAAS_MCP_TOKEN="$(psql postgres://postgres:postgres@127.0.0.1:54322/postgres -Atc \
  "select 'mtt_' || encode(extensions.digest('metatate-seed-mcp-token:customer-360-demo-mcp','sha256'),'hex')")"
export METATATE_SAAS_MCP_AGENT_TOKEN="$(psql postgres://postgres:postgres@127.0.0.1:54322/postgres -Atc \
  "select 'mtt_' || encode(extensions.digest('metatate-seed-mcp-token:customer-360-demo-agent-mcp','sha256'),'hex')")"
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
scripts/run_request_lifecycle_acceptance.sh    # fake client; never files a request
scripts/run_framework_runtime_acceptance.sh    # needs Python 3.10+
scripts/run_notebook_pack.sh                   # notebooks 00–12, except 11
scripts/run_langgraph_runtime_notebook.sh      # notebook 11 (framework deps)
```

CI: `.github/workflows/live-saas-mcp-validation.yml` (workflow_dispatch;
secrets `METATATE_SAAS_MCP_URL`, `METATATE_SAAS_MCP_TOKEN`, and
`METATATE_SAAS_MCP_AGENT_TOKEN`).

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
  Customer 360 policy).
- **`explain_why` chains natively.** `decision_id` explains a cited serving
  decision, `authorization_id` explains the durable `authorize_use` evaluation,
  and `validation_id` explains the durable `validate_query_context` evaluation.
  The client requires exactly one identifier and sends the matching wire kind.
- **Query validation is server-verdict.** Validation is intent- and
  column-aware; the typed answer carries `verdict: pass | warn | fail` plus
  per-ref findings citing the participating instructions. Every call carries a
  durable `validation_id`, which is explainable server-side without returning
  raw SQL.
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
