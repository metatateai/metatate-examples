# Metatate Examples

Metatate is a programmable decision layer for data. It turns policies, classifications, business meaning, transfer rules, and access decisions into structured context that agents and workflows can query before they use data.

This repo is a public cookbook for showing that value in concrete examples. The examples use one synthetic B2B SaaS company, AcmeCloud, so every notebook builds on the same data, policies, and decisions.

## What This Repo Is

This is the demo and examples repo. It is not the source of truth for installable plugins.

Plugin repos stay separate:

- `metatate-claude-plugins` for the Claude Code plugin
- `metatate-cortex-code-plugin` for the Cortex Code plugin

This repo carries notebooks, sample data, SQL fixtures, expected outputs, and framework-specific walkthroughs.

## Demo Domain

AcmeCloud is a fictional B2B SaaS company. The sample data covers customer operations, revenue, product usage, support, and prepared exports.

The first examples focus on these governed tables:

- `ACMECLOUD_DEMO.PUBLIC.CUSTOMERS`
- `ACMECLOUD_DEMO.PUBLIC.SUBSCRIPTIONS`
- `ACMECLOUD_DEMO.PUBLIC.PRODUCT_USAGE_EVENTS`
- `ACMECLOUD_DEMO.PUBLIC.SUPPORT_TICKETS`
- `ACMECLOUD_DEMO.PUBLIC.CUSTOMER_EXPORTS`

The demo policies are intentionally practical:

- customer PII can be used for analytics and reporting only when sensitive columns are minimized or masked
- direct marketing and advertising use are blocked unless a consent-specific workflow is added
- customer records and support tickets cannot be used for model training
- prepared customer exports require transfer approval
- approved CRM exports are conditional; advertising-platform exports are denied

## Repository Map

```text
common/                         Shared Python client helpers
docs/                           Setup, demo model, and troubleshooting
notebooks/                      Notebook-first walkthroughs
sample-data/acmecloud/tables/   Small synthetic CSV tables
sample-data/acmecloud/policies/ Example policy YAML
sample-data/acmecloud/metatate-responses/
                                Offline Metatate response fixtures
sample-outputs/                 Curated expected output summaries
scripts/                        Validation and notebook rendering helpers
sql/                            Snowflake demo table and Metatate fixture SQL
```

## Notebook Pack

Start here:

1. `notebooks/00_setup_live_or_offline.ipynb`
2. `notebooks/01_decision_layer_cookbook.ipynb`
3. `notebooks/02_governed_sql_agent_langgraph.ipynb`
4. `notebooks/03_transfer_governance_before_export.ipynb`

The notebooks default to offline mode and use committed sample Metatate responses. That means a reader can understand the decision flow without Snowflake credentials.

Live mode is optional. It calls the Snowflake-managed Metatate MCP server, the same surface used by Claude Code, Cortex Code, and other MCP clients.

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
jupyter notebook notebooks
```

Offline mode works with no additional configuration.

For live mode:

```bash
cp .env.example .env
# Configure METATATE_MCP_URL and METATATE_MCP_PAT_ENV.
pip install -r requirements-live.txt
```

Then set:

```bash
export METATATE_EXAMPLES_MODE=live
```

Live mode requires a role-restricted Snowflake PAT for the managed MCP server.
See [docs/live-mode.md](docs/live-mode.md).

## Snowflake Fixture

To create the AcmeCloud demo tables and seed Metatate's serving-table fixture in a development or demo account, review:

- [docs/snowflake-setup.md](docs/snowflake-setup.md)
- [sql/setup_acmecloud_demo.sql](sql/setup_acmecloud_demo.sql)
- [sql/smoke_acmecloud_demo.sql](sql/smoke_acmecloud_demo.sql)
- [sql/cleanup_acmecloud_demo.sql](sql/cleanup_acmecloud_demo.sql)

The fixture SQL mirrors the Metatate Native App serving tables used by the MCP tools:

- `app_data.governed_tables`
- `app_data.deployed_instructions`
- `app_data.deployed_usage_rules`
- `app_data.deployed_transfer_rules`
- `app_data.deployed_validation_rules`
- `app_data.deployed_column_details`
- `app_data.deployed_data_meaning`

For production use, deploy policies through Metatate. The SQL fixture is for examples, demos, and repeatable local validation.

## Core Message

When your data carries its own instructions, agents do not just access it. They understand what they are allowed to do, what controls apply, and why a decision was made.

## Links

- Metatate docs: https://docs.getmetatate.com
- MCP cookbook: https://docs.getmetatate.com/mcp/cookbook
- Learn use cases: https://www.getmetatate.com/learn
- Snowflake Marketplace listing: https://app.snowflake.com/marketplace/listing/GZ2FTZU03OAS
