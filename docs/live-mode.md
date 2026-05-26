# Live Mode

Offline mode uses committed JSON response fixtures. Live mode calls a Metatate Native App installed in your Snowflake account.

## Prerequisites

- Metatate installed as a Snowflake Native App
- the app initialized and granted required references
- the MCP/tool layer registered
- a Snowflake role that can use the app objects
- Python dependencies from `requirements-live.txt`

## Configure

```bash
cp .env.example .env
```

Set:

```text
METATATE_EXAMPLES_MODE=live
METATATE_APP_NAME=METATATE_APP
```

Then choose one authentication path.

### Preferred: Snowflake Connection Profile

The notebooks can reuse a Snowflake Python connector / Snow CLI connection
profile:

```text
SNOWFLAKE_CONNECTION_NAME=<profile-name>
SNOWFLAKE_ROLE=<role-with-metatate-access>
```

If your `connections.toml` is not in the connector default location, set its
absolute path:

```text
SNOWFLAKE_CONNECTIONS_FILE=/absolute/path/to/connections.toml
```

This keeps account, user, role, warehouse, and authentication settings in one
Snowflake profile instead of copying them into the examples `.env`. If the
profile does not define a role or warehouse, set `SNOWFLAKE_ROLE` or
`SNOWFLAKE_WAREHOUSE` in `.env`; the helper passes those through as connection
overrides.

### Direct Connector Values

You can also set connector values directly:

```text
SNOWFLAKE_ACCOUNT=<org-account>
SNOWFLAKE_USER=<user>
SNOWFLAKE_ROLE=<role-with-metatate-access>
SNOWFLAKE_WAREHOUSE=<warehouse>
SNOWFLAKE_AUTHENTICATOR=externalbrowser
```

For PAT-based testing, keep the PAT in your shell and reference it by env var:

```bash
export METATATE_EXAMPLES_PAT='<snowflake-pat-secret>'
```

```text
SNOWFLAKE_PAT_ENV=METATATE_EXAMPLES_PAT
SNOWFLAKE_AUTHENTICATOR=programmatic_access_token
```

Do not write the PAT secret into `.env`.

## Network Policy Errors

If live mode opens a browser or starts a PAT connection and Snowflake returns an
IP allowlist error, the notebooks are reaching Snowflake but the account policy
is blocking the machine running the examples. Keep the fix narrow: ask a
Snowflake administrator to allow only the current public IP for the user or
dedicated PAT user used by the examples.

Example administrator SQL:

```sql
USE ROLE ACCOUNTADMIN;

CREATE OR REPLACE NETWORK POLICY METATATE_EXAMPLES_NETWORK_POLICY
  ALLOWED_IP_LIST = ('<CURRENT_PUBLIC_IP>/32')
  COMMENT = 'Narrow allowlist for Metatate examples live notebook testing';

ALTER USER <SNOWFLAKE_USER>
  SET NETWORK_POLICY = METATATE_EXAMPLES_NETWORK_POLICY;
```

Do not use `0.0.0.0/0`, and do not broaden an account-level policy just to run
the examples.

The Python helper calls:

- `METATATE_APP.CORE.DISCOVER_CONTEXT`
- `METATATE_APP.CORE.GET_DECISION_CONTEXT`
- `METATATE_APP.CORE.INSPECT_DATA_MEANING`
- `METATATE_APP.CORE.INSPECT_GOVERNANCE_RULES`
- `METATATE_APP.CORE.AUTHORIZE_USE`
- `METATATE_APP.CORE.VALIDATE_QUERY_CONTEXT`
- `METATATE_APP.CORE.EXPLAIN_WHY`

If your app is named differently, set `METATATE_APP_NAME`.

## Seed Demo Data

Live mode does not require AcmeCloud if your account already has governed tables. To run the notebooks exactly as written, seed the AcmeCloud fixture:

```bash
snow sql -f sql/setup_acmecloud_demo.sql -c <profile>
```

Review the placeholders at the top of the SQL file before running it.

## Security Notes

- Do not commit `.env`.
- Do not commit Snowflake passwords, PATs, or OAuth tokens.
- Use role-scoped credentials for examples.
- The fixture SQL is for demo/development accounts, not production policy deployment.
