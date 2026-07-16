# Walkthrough: A Governed Agent In Claude Code

The notebooks prove the decision layer from Python. This walkthrough proves it
from inside a real agent: **Claude Code, with the `metatate` plugin, making
governed decisions against your workspace** — the Metatate Cloud counterpart
to a hosted-runtime proof.

## Setup (once, ~3 minutes)

1. A workspace serving the AcmeCloud demo publication
   ([README → Run It Live In 5 Minutes](../README.md#run-it-live-in-5-minutes)).
2. In Claude Code:

   ```text
   /plugin marketplace add metatateai/metatate-claude-plugins
   /plugin install metatate@metatate-claude-plugins
   ```

3. Register the MCP connection (endpoint from **MCP Tools → Connect**, token
   from **MCP Tools → Tokens**, shown once):

   ```bash
   claude mcp add-json --scope user metatate '{"type":"http","url":"<mcp-server-url>/mcp","headers":{"Authorization":"Bearer <your-access-token>"}}'
   ```

Full install docs live in
[metatate-claude-plugins](https://github.com/metatateai/metatate-claude-plugins).

## The demo: watch the agent defer to governance

Each step is a slash command plus a natural-language ask. Claude calls the
governed tools and reasons over the TYPED answers — it does not guess from
schema names or pasted policy text.

**1. Discover what's governed.**

```text
/metatate:discover-context
```

Claude lists the estate — the Customer 360 members, the PCI payment table,
HR, the ML feature store — each with instruction counts and scenario keys.

**2. Ask for something prohibited.**

```text
/metatate:authorize-use
Can we use acmecloud_demo.public.customers for a marketing email campaign?
```

Expect a typed **deny** (`purpose.prohibited_use`) with the citing policy —
and Claude declining to draft the campaign query, because the decision layer
said no.

**3. Ask for something allowed, then make Claude prove it.**

```text
/metatate:authorize-use
Can we build a churn analytics dashboard on customers?
```

Expect **allow**, with a `decision_id`. Then:

```text
/metatate:explain-decision
Explain decision <decision_id from the answer above>
```

The explanation names the instruction, the policy version, and whether the
decision is still current.

**4. Gate SQL the agent wrote itself.**

```text
/metatate:validate-query
Is this safe to run for analytics?
SELECT customer_name, email FROM acmecloud_demo.public.customers WHERE region = 'EU'
```

Expect **warn** — a masked column is referenced — and Claude proposing the
minimized aggregate instead. That is the guard pattern from notebooks 02/04,
running inside a production agent.

**5. Hit the honest states.**

```text
/metatate:authorize-use
Can we report on acmecloud_demo.public.legacy_customer_backup?
```

Expect `not_enough_published_state`: the table is cataloged but ungoverned,
and the agent is told exactly that — no fabricated decision. This is the
setup for the [coverage-review walkthrough](walkthrough-coverage-review.md).

## Why this is the hero demo

Every answer above is served from the workspace's CURRENT publication — the
same rows the notebooks replay offline, the same rows the CI gate enforces.
One decision layer, every consumer: Python, CI, and a live agent.
