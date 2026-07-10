# Troubleshooting

## The notebooks show offline responses after I configured Snowflake

Set live mode in the same shell where Jupyter starts:

```bash
export METATATE_EXAMPLES_MODE=live
```

Restart the notebook kernel after changing environment variables.

## The MCP endpoint does not exist

Check `METATATE_MCP_URL`. The endpoint should look like:

```text
https://<account-url>/api/v2/databases/METATATE_APP/schemas/CORE/mcp-servers/METATATE_MCP
```

If your app, schema, or MCP server uses a different name, either set `METATATE_MCP_URL` directly or configure:

```text
METATATE_MCP_ACCOUNT_URL
METATATE_APP_NAME
METATATE_MCP_SCHEMA
METATATE_MCP_SERVER_NAME
```

## The PAT is invalid

Confirm:

- `METATATE_MCP_PAT_ENV` names the environment variable that contains the PAT
- the PAT is exported in the same shell where Jupyter starts
- `SNOWFLAKE_ROLE` matches the PAT `ROLE_RESTRICTION`
- the PAT belongs to the same Snowflake account as the MCP endpoint
- the PAT has not expired or been removed

Do not put the PAT secret in `.env`.

## Live notebook execution fails with a transient MCP connection error

The live client retries temporary disconnects and retryable HTTP responses. If failures continue, confirm the MCP endpoint is healthy and rerun with a longer timeout:

```bash
export METATATE_MCP_TIMEOUT_SECONDS=180
scripts/run_notebook_pack.sh
```

## Snowflake says network policy is required or the IP/token is not allowed

The request reached Snowflake, but the PAT user is blocked by network policy.

Use the dedicated service-user flow:

```bash
SNOW_CONNECTION=<profile> scripts/create_mcp_pat_user.sh
```

That script creates a user-level `/32` allowlist for the current public IP. Do not attach this policy to a human/admin user.

## The setup SQL cannot insert into `app_data.*`

The fixture script requires a role that can use the application and write demo fixture rows. For demos, run it with an administrative Snowflake profile or adjust the variables at the top of `sql/setup_acmecloud_demo.sql`.

Production policies should be deployed through Metatate, not direct fixture inserts.

## The examples return no governed tables

In live mode, either seed the AcmeCloud fixture or update the notebooks to use governed tables already deployed in your account.

```bash
snow sql -f sql/setup_acmecloud_demo.sql -c <profile>
snow sql -f sql/smoke_acmecloud_demo.sql -c <profile>
```

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

## SaaS backend (`METATATE_MCP_BACKEND=saas`)

- **401 unauthorized** — uniform for missing/expired/revoked tokens. Token
  format is `mtt_` + 64 hex characters; issue a fresh one in the workspace
  MCP module → Tokens (shown once).
- **429 rate limited** — per-token budget (default 120 calls/min); the client
  honors `Retry-After`. The discovery enrichment fan-out is bounded and
  cached, but tight loops in custom code can still trip it.
- **`asset_not_found`** — SaaS identifiers are lowercase normalized names in
  a structured reference; the client lowercases FQNs for you, so this
  usually means the AcmeCloud demo fixture was not applied to the workspace
  you are calling (metatate-saas: `./scripts/acmecloud-demo-fixtures.sh`).
- **`not_enough_published_state`** — the tenant has no current publication
  for that asset/scenario; publish the demo state first.
- **`UNKNOWN` decisions on custom intents** — the server never guesses an
  unmappable intent (`scenario_unresolved`); pass a supported
  `intended_use` (analytics/reporting/support/marketing/ml_training/…) or a
  canonical scenario key.
- **GET /mcp returns 405** — the endpoint is POST-only JSON-RPC; the client
  handles this, plain curl probes should POST.
