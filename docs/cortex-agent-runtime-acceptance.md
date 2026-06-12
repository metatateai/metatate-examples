# Cortex Agent Runtime Acceptance

This live-only check proves that a Snowflake Cortex Agent object can call Metatate from a server-side custom tool.

It creates a scratch Cortex Agent, attaches a generic custom tool, runs the agent through the Cortex Agents REST API, and asserts that the agent response contains:

- a `tool_use` for the Metatate validation tool
- a server-side `tool_result`
- a Metatate `CONDITIONAL` decision for a governed AcmeCloud SQL query
- `can_execute_query = false` because the query selects direct identifiers

There is no offline fallback for this check.

## Prerequisites

- Metatate installed and initialized as a Snowflake Native App
- the AcmeCloud fixture seeded with `sql/setup_acmecloud_demo.sql`
- Cortex Agents enabled in the Snowflake account
- a role-restricted PAT for a dedicated service user
- a role that can create the scratch database, schema, stored procedure, and agent
- a warehouse available to execute the custom tool
- Python dependencies from `requirements-live.txt`

Use the PAT setup in [live-mode.md](live-mode.md). Do not attach examples network policies to a human/admin user.

## Objects Created

By default the runner creates or replaces:

```text
METATATE_EXAMPLES_RUNTIME.CORTEX_AGENT.METATATE_VALIDATE_QUERY_TOOL
METATATE_EXAMPLES_RUNTIME.CORTEX_AGENT.METATATE_GOVERNED_SQL_AGENT
```

The wrapper procedure delegates to:

```text
METATATE_APP.CORE.AGENT_VALIDATE_QUERY_CONTEXT
```

The procedure and agent are safe to replace. They are examples-only runtime objects, not Metatate product objects.

## Run

```bash
export METATATE_EXAMPLES_PAT="$(cat /private/tmp/metatate_examples_mcp_pat)"

METATATE_CORTEX_ACCOUNT_URL=https://<account-url> \
SNOWFLAKE_ROLE=NAC \
METATATE_CORTEX_WAREHOUSE=WH_NAC \
scripts/run_cortex_agent_runtime_acceptance.sh
```

If `METATATE_MCP_URL`, `METATATE_MCP_ACCOUNT_URL`, or `SNOWFLAKE_ACCOUNT_URL` is already set, `METATATE_CORTEX_ACCOUNT_URL` is optional.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `METATATE_CORTEX_PAT_ENV` | `METATATE_MCP_PAT_ENV` or `METATATE_EXAMPLES_PAT` | Environment variable containing the PAT secret. |
| `METATATE_CORTEX_ACCOUNT_URL` | derived from MCP/Snowflake env vars | Snowflake account URL. |
| `METATATE_CORTEX_ROLE` | `SNOWFLAKE_ROLE` or `NAC` | Role used by SQL API setup calls. |
| `METATATE_CORTEX_WAREHOUSE` | `WH_NAC` | Warehouse used by the custom tool. |
| `METATATE_CORTEX_DATABASE` | `METATATE_EXAMPLES_RUNTIME` | Scratch database for acceptance objects. |
| `METATATE_CORTEX_SCHEMA` | `CORTEX_AGENT` | Scratch schema for acceptance objects. |
| `METATATE_CORTEX_AGENT_MODEL` | `auto` | Cortex Agent orchestration model. |
| `METATATE_APP_NAME` | `METATATE_APP` | Installed Metatate Native App name. |

## What Is Covered

- Cortex Agent object creation through Snowflake REST APIs.
- Generic custom tool configuration with a warehouse execution environment.
- Server-side custom tool execution.
- Delegation from the custom tool to the Metatate Snowflake Intelligence wrapper.
- A live Metatate decision returned inside the Cortex Agent response.

## What Is Not Covered

- Broad model quality or planning evaluation.
- Multi-turn agent memory.
- Cortex Analyst semantic views.
- Cortex Search services.
- Direct access to customer data. The test validates a SQL string; it does not execute the governed SQL.
