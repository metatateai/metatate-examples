# Snowflake Cortex Agent Tool Preflight Output

The Cortex-style preflight checks each proposed tool invocation before the agent receives data or runs an action.

Expected behavior:

- aggregate revenue SQL is allowed to proceed
- direct marketing access to customer names and emails is blocked

The example records the Metatate decision and action next to each tool request, creating an auditable boundary before execution.
