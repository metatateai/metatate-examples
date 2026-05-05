# Metatate Examples

Metatate is a programmable decision layer for Snowflake data. It turns policies, classifications, data meaning, retention guidance, and transfer controls into structured context that agents and workflows can query before they use data.

This repository contains examples for making governed Snowflake data agent-ready with Metatate.

## Snowflake-native Examples

These examples focus on the Snowflake-native path:

- Snowflake Intelligence custom tools through Metatate's `core.agent_*` wrapper layer
- MCP cookbook workflows that compose discovery, meaning, authorization, validation, and explanation
- Transfer governance decisions for external data movement
- Sanitized sample evidence generated from a repeatable demo reliability gate

Later releases will add Claude Code, Claude Desktop, pipeline gates, Cortex Code, policy-as-code, and playground examples.

## What this proves

When data carries its own instructions, agents do not need to guess whether a use is safe. They can ask Metatate:

- Which governed tables are available?
- What does this table or column mean?
- What policies and transfer controls apply?
- Is this use allowed, denied, conditional, or unknown?
- Is this generated SQL safe to run?
- Why did Metatate make that decision?

## Repository map

```text
snowflake-intelligence/   Snowflake Intelligence setup, wrapper map, and prompts
mcp-cookbook/             Five validated decision workflows
demo-evidence/            Sanitized generated evidence examples
```

## Prerequisites

To run the SQL examples against your own account, you need:

- Metatate installed as a Snowflake Native App
- The app initialized and granted the required references
- An app warehouse reference configured for MCP and wrapper execution
- At least one deployed policy or the demo fixture described in the examples
- A Snowflake role that can use the Metatate app objects

If you do not have Metatate installed yet, you can still read the sample outputs in `demo-evidence/` to understand the decision flow.

## Demo control tags

The sample flows use customer-defined controls, not named external compliance catalogs:

- `privacy_sensitive`
- `restricted_transfer`
- `retention_required`
- `ai_training_blocked`

## Start here

1. Read `snowflake-intelligence/setup-guide.md`.
2. Review the wrapper map in `snowflake-intelligence/wrapper-tool-map.md`.
3. Run or inspect the cookbook in `mcp-cookbook/recipes.sql`.
4. Review sanitized outputs in `demo-evidence/sample-json/`.

## Links

- Metatate docs: https://docs.getmetatate.com
- MCP cookbook: https://docs.getmetatate.com/mcp/cookbook
- Learn use cases: https://www.getmetatate.com/learn
- Snowflake Marketplace listing: https://app.snowflake.com/marketplace/listing/GZ2FTZU03OAS
