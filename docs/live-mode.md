# Live Mode

> Looking for the Metatate SaaS (cross-platform) endpoint instead? See
> [live-mode-saas.md](live-mode-saas.md) — same notebooks, `METATATE_MCP_BACKEND=saas`.

Live mode calls the Snowflake-managed Metatate MCP server. The notebooks do not open a direct SQL connector session for Metatate tool calls.

Use live mode when you want the examples to exercise the same MCP surface used by external agents and MCP clients.

## Prerequisites

- Metatate installed and initialized as a Snowflake Native App
- the managed MCP server registered in the app
- a Snowflake role that can use the MCP server, for example `NAC`
- a role-restricted Snowflake programmatic access token (PAT)
- Python dependencies from `requirements-live.txt`

## Recommended PAT Setup

Use a dedicated service user for examples. Do not attach network policies to a human/admin user just to run notebooks.

The helper script creates or refreshes:

- a service user, default `METATATE_EXAMPLES_MCP_USER`
- a narrow user-level network policy for the current public IP
- a short-lived PAT role-restricted to the MCP role

```bash
SNOW_CONNECTION=<snowflake-cli-profile> \
METATATE_PAT_ROLE=NAC \
METATATE_PAT_WAREHOUSE=WH_NAC \
scripts/create_mcp_pat_user.sh
```

The script writes the PAT secret to `/private/tmp/metatate_examples_mcp_pat` by default and prints the export command. The secret is not written to `.env`.

Optional overrides:

```bash
METATATE_PAT_USER=METATATE_EXAMPLES_MCP_USER
METATATE_PAT_ALLOWED_IP=<current-public-ip-or-cidr>
METATATE_PAT_DAYS_TO_EXPIRY=7
METATATE_PAT_SECRET_FILE=/private/tmp/metatate_examples_mcp_pat
METATATE_PAT_TOKEN_NAME=METATATE_EXAMPLES_MCP_<suffix>
```

## Manual PAT SQL

If you prefer to run SQL manually, keep it scoped to a dedicated service user:

```sql
USE ROLE ACCOUNTADMIN;

CREATE USER IF NOT EXISTS METATATE_EXAMPLES_MCP_USER
  TYPE = SERVICE
  DEFAULT_ROLE = NAC
  DEFAULT_WAREHOUSE = WH_NAC
  COMMENT = 'Dedicated service user for Metatate examples managed MCP live testing';

GRANT ROLE NAC TO USER METATATE_EXAMPLES_MCP_USER;

CREATE NETWORK POLICY IF NOT EXISTS METATATE_EXAMPLES_MCP_NETWORK_POLICY
  ALLOWED_IP_LIST = ('<CURRENT_PUBLIC_IP>/32')
  COMMENT = 'Narrow allowlist for Metatate examples managed MCP live testing';

ALTER NETWORK POLICY METATATE_EXAMPLES_MCP_NETWORK_POLICY
  SET ALLOWED_IP_LIST = ('<CURRENT_PUBLIC_IP>/32')
  COMMENT = 'Narrow allowlist for Metatate examples managed MCP live testing';

ALTER USER METATATE_EXAMPLES_MCP_USER
  SET NETWORK_POLICY = METATATE_EXAMPLES_MCP_NETWORK_POLICY;

ALTER USER METATATE_EXAMPLES_MCP_USER
  ADD PROGRAMMATIC ACCESS TOKEN metatate_examples_mcp_pat
  ROLE_RESTRICTION = 'NAC'
  DAYS_TO_EXPIRY = 7
  COMMENT = 'Temporary PAT for Metatate examples live MCP validation';
```

Snowflake shows the PAT secret only once. Store it outside the repository.

## Configure The Notebook Environment

```bash
cp .env.example .env
```

Set:

```text
METATATE_EXAMPLES_MODE=live
METATATE_MCP_URL=https://<account-url>/api/v2/databases/METATATE_APP/schemas/CORE/mcp-servers/METATATE_MCP
SNOWFLAKE_ROLE=<role-matching-the-pat-role-restriction>
METATATE_MCP_PAT_ENV=METATATE_EXAMPLES_PAT
```

Then export the PAT in the shell where you run Jupyter:

```bash
export METATATE_EXAMPLES_PAT="$(cat /private/tmp/metatate_examples_mcp_pat)"
```

Do not commit `.env` or PAT secrets.

If you prefer constructing the endpoint from parts, omit `METATATE_MCP_URL` and set:

```text
METATATE_MCP_ACCOUNT_URL=https://<account-url>
METATATE_APP_NAME=METATATE_APP
METATATE_MCP_SCHEMA=CORE
METATATE_MCP_SERVER_NAME=METATATE_MCP
```

## Execute The Notebook Pack

```bash
export METATATE_EXAMPLES_PAT="$(cat /private/tmp/metatate_examples_mcp_pat)"

METATATE_EXAMPLES_MODE=live \
METATATE_MCP_URL=https://<account-url>/api/v2/databases/METATATE_APP/schemas/CORE/mcp-servers/METATATE_MCP \
SNOWFLAKE_ROLE=NAC \
METATATE_MCP_PAT_ENV=METATATE_EXAMPLES_PAT \
scripts/run_notebook_pack.sh
```

## MCP Tools Used

The Python helper translates notebook calls into JSON-RPC MCP tool calls:

- `discover-context`
- `get-decision-context`
- `inspect-data-meaning`
- `inspect-governance-rules`
- `authorize-use`
- `validate-query-context`
- `explain-why`

The live client retries transient MCP disconnects and retryable HTTP responses. You can tune that behavior with:

```text
METATATE_MCP_RETRY_ATTEMPTS=4
METATATE_MCP_RETRY_BACKOFF_SECONDS=1
METATATE_MCP_TIMEOUT_SECONDS=120
```

## Seed Demo Data

Live mode can use any governed tables already deployed in your account. To run the notebooks exactly as written, seed the AcmeCloud fixture:

```bash
snow sql -f sql/setup_acmecloud_demo.sql -c <profile>
snow sql -f sql/smoke_acmecloud_demo.sql -c <profile>
```

## Network Policy Errors

If Snowflake returns an IP allowlist or network-policy error, the notebooks reached the managed MCP endpoint but the PAT user is blocked by Snowflake policy.

Keep the fix narrow:

- allow only the current public IP or CIDR
- attach the policy only to the dedicated PAT user
- do not use `0.0.0.0/0`
- do not attach notebook policies to a human/admin user

## Remove A Test PAT

Remove tokens when they are no longer needed:

```sql
USE ROLE ACCOUNTADMIN;
ALTER USER METATATE_EXAMPLES_MCP_USER
  REMOVE PROGRAMMATIC ACCESS TOKEN <token_name>;
```
