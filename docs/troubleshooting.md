# Troubleshooting

## The notebooks show offline responses after I configured live mode

Set live mode in the same shell where Jupyter starts:

```bash
export METATATE_EXAMPLES_MODE=live
```

Restart the notebook kernel after changing environment variables.

## The MCP endpoint does not exist

Check `METATATE_MCP_URL`. It is the full endpoint from the workspace MCP
module's **Connect** tab and should look like:

```text
https://<your-workspace-mcp-host>/mcp
```

Plain `curl` probes should POST — `GET /mcp` returns 405 (the endpoint is
POST-only JSON-RPC); the client handles this for you.

## 401 unauthorized

The response is uniform for missing, malformed, expired, and revoked tokens.
Confirm:

- the token is exported in the same shell where Jupyter starts (default
  variable `METATATE_SAAS_MCP_TOKEN`; `METATATE_MCP_PAT_ENV` renames it)
- the token format is `mtt_` + 64 hex characters
- the token belongs to the workspace behind `METATATE_MCP_URL`

Issue a fresh token in the workspace MCP module → Tokens (shown once). Do not
put the token in `.env`.

## 429 rate limited

Per-token budget (default 120 calls/min); the client honors `Retry-After`.
The discovery enrichment fan-out is bounded and cached, but tight loops in
custom code can still trip it.

## Live notebook execution fails with a transient MCP connection error

The live client retries temporary disconnects and retryable HTTP responses. If failures continue, confirm the MCP endpoint is healthy and rerun with a longer timeout:

```bash
export METATATE_MCP_TIMEOUT_SECONDS=180
scripts/run_notebook_pack.sh
```

## The examples return no governed tables / `asset_not_found`

Identifiers are lowercase normalized names in a structured reference (the
client lowercases FQNs for you), so this usually means the workspace you are
calling does not serve the AcmeCloud demo publication. Load it with the
one-click **Load the AcmeCloud demo** action on the workspace dashboard;
contributors on the local `metatate-saas` stack run
`./scripts/acmecloud-demo-fixtures.sh` instead.

## `not_enough_published_state`

The workspace has no current publication for that asset or scenario. Live MCP
answers only change on publish: load the demo publication (or author, approve,
and publish your own policies) first.

## The transfer example returns UNKNOWN

Transfer authorization requires destination context:

```json
{
  "destination": {
    "system": "SALESFORCE",
    "jurisdiction": "US"
  },
  "consumer_jurisdiction": "EU"
}
```

If destination or consumer jurisdiction is missing, Metatate may ask for more context instead of returning a final transfer decision.

## `offline_fixture_missing`

Offline mode replays the recorded case set in `common/fixture_cases.py` — an
ad-hoc call that matches no recorded case raises this typed error instead of
inventing a governance answer. Use live mode for ad-hoc questions, or add the
case and re-run `scripts/record_offline_fixtures.py` against a live workspace.

## `scenario_unresolved` on custom intents

The server never guesses an unmappable free-text `use`; pass a canonical
`scenario_key` (`purpose.allowed_use`, `ai.training`,
`residency.cross_border_transfer`, …) for deterministic routing.

## Notebook edits disappear after regeneration

The `.ipynb` files are generated. Edit `scripts/build_notebooks.py` and rerun
it; `scripts/build_notebooks.py --check` (run by CI) fails while a notebook
and the generator disagree.
