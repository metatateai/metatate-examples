# OpenAI Agents Tool Guard Pattern Output

The tool guard evaluates proposed export tool calls:

- Salesforce export returns `CONDITIONAL` and is deferred until controls are completed
- advertising-platform export returns `DENY` and is blocked

The pattern keeps the agent free to plan, but Metatate decides whether data-moving tools can execute.
