# Snowflake Setup

The examples support two setup paths.

## Option 1: Offline

Use the notebooks as-is. They read from:

```text
sample-data/acmecloud/metatate-responses/
```

No Snowflake account is required.

## Option 2: Live AcmeCloud Fixture

Use this when you want the notebooks to call a live Metatate Native App.

1. Confirm Metatate is installed and initialized in Snowflake.
2. Confirm your role can use the application objects.
3. Review `sql/setup_acmecloud_demo.sql`.
4. Replace the setup variables if your role, warehouse, app, database, or schema names differ.
5. Run the setup script.

```bash
snow sql -f sql/setup_acmecloud_demo.sql -c <profile>
```

The setup script creates physical AcmeCloud tables and seeds the Metatate serving tables used by the MCP tools.

Run the smoke test:

```bash
snow sql -f sql/smoke_acmecloud_demo.sql -c <profile>
```

Expected results:

- five AcmeCloud governed tables
- zero non-AcmeCloud governed rows if the demo account has been reset for examples
- `discover_context` returns five tables
- `agent_discover_context` returns five tables
- export to Salesforce returns a conditional transfer decision
- analytics SQL touching `EMAIL` returns governance findings

## Why The Script Seeds Serving Tables

The public examples need deterministic behavior. In production, Metatate materializes these rows when policies are deployed through the app. For demos, the SQL fixture writes the same serving-table shape directly so notebooks can produce stable results.

The seeded app tables are:

```text
app_data.governed_tables
app_data.deployed_instructions
app_data.deployed_usage_rules
app_data.deployed_transfer_rules
app_data.deployed_validation_rules
app_data.deployed_column_details
app_data.deployed_data_meaning
```

This mirrors the Native App model used by the canonical `core.*` MCP tools and Snowflake Intelligence `core.agent_*` wrappers.

The Cortex Agent runtime acceptance check also uses these Snowflake Intelligence wrappers. It creates an examples-only stored procedure that delegates to `core.agent_validate_query_context`, then exposes that procedure as a Cortex Agent generic custom tool. See [cortex-agent-runtime-acceptance.md](cortex-agent-runtime-acceptance.md).

## Cleanup

```bash
snow sql -f sql/cleanup_acmecloud_demo.sql -c <profile>
```

The cleanup script removes AcmeCloud demo metadata from the Metatate app and drops the demo database.
