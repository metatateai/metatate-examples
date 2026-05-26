# Live Mode

Offline mode uses committed JSON response fixtures. Live mode calls the
Snowflake-managed Metatate MCP server.

This is intentional: the notebooks demonstrate the same MCP tool surface used
by Claude Code, Cortex Code, and custom agents.

## Prerequisites

- Metatate installed as a Snowflake Native App
- the app initialized and granted required references
- the managed MCP server registered from the app
- a Snowflake role that can use the MCP server
- a role-restricted Snowflake programmatic access token (PAT)
- Python dependencies from `requirements-live.txt`

## Configure

```bash
cp .env.example .env
```

Set:

```text
METATATE_EXAMPLES_MODE=live
METATATE_MCP_URL=https://<account-url>/api/v2/databases/METATATE_APP/schemas/CORE/mcp-servers/METATATE_MCP
SNOWFLAKE_ROLE=<role-with-metatate-mcp-access>
METATATE_MCP_PAT_ENV=METATATE_EXAMPLES_PAT
```

Then export the PAT in the shell where you run Jupyter:

```bash
export METATATE_EXAMPLES_PAT='<snowflake-pat-secret>'
```

Do not write the PAT secret into `.env`.

If you prefer constructing the endpoint from parts, omit `METATATE_MCP_URL` and
set:

```text
METATATE_MCP_ACCOUNT_URL=https://<account-url>
METATATE_APP_NAME=METATATE_APP
METATATE_MCP_SCHEMA=CORE
METATATE_MCP_SERVER_NAME=METATATE_MCP
```

## MCP Tools Used

The Python helper calls the managed MCP server through JSON-RPC:

- `discover-context`
- `get-decision-context`
- `inspect-data-meaning`
- `inspect-governance-rules`
- `authorize-use`
- `validate-query-context`
- `explain-why`

The notebooks keep a small Python API for readability, but live mode translates
those calls into MCP tool invocations.

## Seed Demo Data

Live mode does not require AcmeCloud if your account already has governed
tables. To run the notebooks exactly as written, seed the AcmeCloud fixture:

```bash
snow sql -f sql/setup_acmecloud_demo.sql -c <profile>
```

Review the placeholders at the top of the SQL file before running it.

## Network Policy Errors

If Snowflake returns an IP allowlist or network-policy error, the notebooks are
reaching the managed MCP endpoint but the PAT/user is blocked by account policy.
Keep the fix narrow: ask a Snowflake administrator to allow only the current
public IP for the user or dedicated PAT user used by the examples.

Example administrator SQL:

```sql
USE ROLE ACCOUNTADMIN;

CREATE OR REPLACE NETWORK POLICY METATATE_EXAMPLES_NETWORK_POLICY
  ALLOWED_IP_LIST = ('<CURRENT_PUBLIC_IP>/32')
  COMMENT = 'Narrow allowlist for Metatate examples live notebook testing';

ALTER USER <SNOWFLAKE_USER>
  SET NETWORK_POLICY = METATATE_EXAMPLES_NETWORK_POLICY;
```

For short-lived demo PATs, an administrator can also issue a PAT with a
temporary network-policy bypass:

```sql
ALTER USER <SNOWFLAKE_USER>
  ADD PROGRAMMATIC ACCESS TOKEN metatate_examples_pat
  ROLE_RESTRICTION = '<ROLE_WITH_METATATE_MCP_ACCESS>'
  DAYS_TO_EXPIRY = 7
  MINS_TO_BYPASS_NETWORK_POLICY_REQUIREMENT = 60
  COMMENT = 'Temporary PAT for Metatate examples live notebook testing';
```

Do not use `0.0.0.0/0`, and do not broaden an account-level policy just to run
the examples.

## Security Notes

- Do not commit `.env`.
- Do not commit Snowflake passwords, PATs, OAuth tokens, or refresh tokens.
- Use role-restricted PATs for examples.
- Keep `SNOWFLAKE_ROLE` aligned with the PAT `ROLE_RESTRICTION`.
- The fixture SQL is for demo/development accounts, not production policy
  deployment.
