# Troubleshooting

## The notebooks show offline responses even after I configured Snowflake

Set:

```bash
export METATATE_EXAMPLES_MODE=live
```

Restart the notebook kernel after changing environment variables.

## Snowflake says the MCP endpoint does not exist

Check `METATATE_MCP_URL`. The endpoint should look like:

```text
https://<account-url>/api/v2/databases/METATATE_APP/schemas/CORE/mcp-servers/METATATE_MCP
```

If your Native App, schema, or MCP server uses a different name, either update
`METATATE_MCP_URL` directly or set `METATATE_MCP_ACCOUNT_URL`,
`METATATE_APP_NAME`, `METATATE_MCP_SCHEMA`, and `METATATE_MCP_SERVER_NAME`.

## Snowflake says the PAT is invalid

Live notebooks use a Snowflake PAT against the managed MCP endpoint. Confirm:

- `METATATE_MCP_PAT_ENV` names the environment variable that contains the PAT
- the PAT is exported in the same shell where Jupyter starts
- `SNOWFLAKE_ROLE` matches the PAT `ROLE_RESTRICTION`
- the PAT has not expired or been removed

Do not put the PAT secret in `.env`.

## Snowflake says network policy is required

The notebook reached the managed MCP endpoint, but the PAT/user is blocked by
Snowflake network policy. Use a narrow `/32` allowlist for the current public
IP, or issue a short-lived PAT with
`MINS_TO_BYPASS_NETWORK_POLICY_REQUIREMENT` for demo testing.

## The setup SQL cannot insert into `app_data.*`

The fixture script requires a role that can use the application and write the demo fixture rows. In normal production use, policies should be deployed through Metatate instead of direct fixture inserts.

For demos, run the script with an administrative Snowflake profile. The
notebooks themselves do not use this SQL connection; they use the managed MCP
endpoint.

## The examples return no governed tables

In live mode, either:

- seed the AcmeCloud fixture with `sql/setup_acmecloud_demo.sql`, or
- edit notebook table names to match governed tables already deployed in your account.

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

If destination or consumer jurisdiction is missing, Metatate may ask for more context rather than returning a final transfer decision.
