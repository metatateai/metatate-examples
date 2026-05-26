# Notebooks

These notebooks default to offline mode. They use committed Metatate response fixtures from `sample-data/acmecloud/metatate-responses`.

Set `METATATE_EXAMPLES_MODE=live` to call the Snowflake-managed Metatate MCP
server instead.

## Order

1. `00_setup_live_or_offline.ipynb`
2. `01_decision_layer_cookbook.ipynb`
3. `02_governed_sql_agent_langgraph.ipynb`
4. `03_transfer_governance_before_export.ipynb`

The notebooks are generated from `scripts/build_notebooks.py` so the JSON remains reproducible.
