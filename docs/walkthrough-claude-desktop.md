# Walkthrough: Governance Questions In Claude Desktop

The notebooks prove the decision layer from Python, and the
[Claude Code walkthrough](walkthrough-claude-code.md) proves it inside a coding
agent. This walkthrough wires a **conversational** client: Claude Desktop over
plain remote MCP — no plugin, no Python, no slash commands. Anyone who can type
a question gets typed governance answers back in chat.

## Setup (once, ~5 minutes)

1. A workspace serving the AcmeCloud demo publication
   ([README → Run It Live In 5 Minutes](../README.md#run-it-live-in-5-minutes)).
2. Your endpoint URL from **MCP Tools → Connect** and an access token from
   **MCP Tools → Tokens** (`mtt_…`, shown exactly once).
3. Node 18+ on your machine (the bridge runs via `npx`).
4. In Claude Desktop: **Settings → Developer → Edit Config**, add the server,
   then fully restart the app:

   ```json
   {
     "mcpServers": {
       "metatate": {
         "command": "npx",
         "args": [
           "-y",
           "mcp-remote",
           "<mcp-server-url>/mcp",
           "--header",
           "Authorization: Bearer ${METATATE_MCP_TOKEN}"
         ],
         "env": {
           "METATATE_MCP_TOKEN": "mtt_<your-access-token>"
         }
       }
     }
   }
   ```

After the restart, the connector's tool listing shows the seven governance
tools. The config file now contains a workspace secret — treat it like a
password, and revoke the token from the Tokens tab if the file is ever shared.

> **Why the bridge?** The workspace endpoint deliberately has no OAuth flow —
> a bearer token is the whole handshake ([docs → Connect an
> agent](https://docs.getmetatate.com/cloud/mcp/connect)). Claude Desktop's
> local MCP config passes that header via `mcp-remote`. Web-based
> claude.ai custom connectors currently require an OAuth-capable server, so
> for browser use stick to the in-app **MCP Tools → Tools** preview; for
> terminal agents use the [Claude Code plugin](walkthrough-claude-code.md).

## The demo: plain questions, typed answers

No commands — just ask. Claude Desktop decides when to call the governed
tools and reasons over the TYPED answers instead of guessing from schema
names.

**1. "What does Metatate govern in this workspace? List the tables."**

Claude calls `discover_context` and lists the estate — the Customer 360
members, the PCI payment table, HR, the ML feature store — with instruction
counts and scenario keys.

**2. "Before we plan anything: what are ALL the active rules on
`acmecloud_demo.public.customers`?"**

Claude calls `inspect_governance_rules` and summarizes the rulebook —
masking on the email column, AI training denied, marketing prohibited, the
destination-aware transfer matrix — each rule with its policy and decision.
(Notebook 01 walks this same rulebook step from Python.)

**3. "Can we use customers for a marketing email campaign?"**

A typed **deny** (`purpose.prohibited_use`), the citing policy named — and
Claude declining to help draft the campaign, because the decision layer said
no.

**4. "So what CAN we do? Could we build a churn analytics dashboard on it?"**

**allow**, with a `decision_id` in the answer.

**5. "Why is that allowed? Prove it."**

Claude chains the `decision_id` into `explain_why`: the instruction, the
policy version, and whether the decision is still in the CURRENT publication.

**6. "Is this safe to run for analytics?
`SELECT customer_name, email FROM acmecloud_demo.public.customers WHERE region = 'EU'`"**

**warn** — a masked column is referenced — and Claude proposes the minimized
aggregate instead. The same guard the notebooks and the CI gate enforce, now
in a chat window.

**7. "What about `acmecloud_demo.public.legacy_customer_backup`?"**

`not_enough_published_state`: cataloged but ungoverned, and the agent is told
exactly that — no fabricated decision. The
[coverage-review walkthrough](walkthrough-coverage-review.md) picks up from
here.

## Why this matters

Every answer above is served from the workspace's CURRENT publication — the
same rows the notebooks replay offline, the same rows the CI gate and the
Claude Code plugin consume. A governance lead who never opens a terminal can
interrogate the decision layer in plain language, and the answers cite their
policies.

## Troubleshooting

- **Tools don't appear** — fully quit and reopen Claude Desktop after editing
  the config; check `npx -y mcp-remote --version` runs.
- **`unauthorized`** — the token was revoked, expired, or mistyped. Reissue
  from **MCP Tools → Tokens** (missing, malformed, and revoked tokens all
  produce the same response by design).
- **Wrong workspace answers** — the workspace is resolved entirely from the
  token; reissue a token from the workspace you mean.
