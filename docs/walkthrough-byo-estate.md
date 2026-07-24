# Walkthrough: Your Estate, Governed By Friday

Everything else in this repo runs against AcmeCloud. This walkthrough is the
bridge to YOUR data: connect a real source, let classification find the
personal data, publish four estate-agnostic starter policies, and watch the
same typed answers the notebooks demonstrate come back about your own tables.
Works identically for any of the six connector kinds — Postgres, MySQL,
BigQuery, Redshift, Databricks, Snowflake.

## 0. Baseline: measure the gap

With a workspace and token ([docs/live-mode-saas.md](live-mode-saas.md)):

```bash
export METATATE_EXAMPLES_MODE=live METATATE_MCP_URL=... METATATE_SAAS_MCP_TOKEN=...
python3 scripts/bootstrap_check.py
```

On a fresh workspace this reports nothing governed — the honest starting
point. (Each row is one governed call and counts toward your plan's
MCP-call quota.)

## 1. Connect a source

**Data Sources → New**: pick your platform, enter connection details
(credentials go to the platform's vault; they are decrypted only in worker
processes and never returned to a browser). Test the connection, use
**Choose what to sync** to scope databases/schemas, then run the sync.

## 2. Let classification work, then review it

The sync classifies columns deterministically by name/type patterns (with
optional AI-assisted classification on sampled values). In **Catalog**,
review what it found — emails, names, government ids — and correct or add
classifications where you know better. Classification is the lever
everything below pulls on: the starter policies target TAXONOMY TYPES, not
table lists.

## 3. Publish the starter pack

For each file in [`starter-policies/`](../starter-policies):

1. **Policies → New policy → Raw YAML**, paste the template, save the draft.
2. Review — the Coverage tab previews which of YOUR columns/tables the
   taxonomy targets will resolve to at deploy time.
3. Submit and approve.

Then **Deployments → review and publish**. The four templates:

| Template | What it does, estate-wide |
| --- | --- |
| `starter-email-masking.yaml` | Partial masking wherever a column is classified `pii.contact.email`. |
| `starter-pii-usage-guardrails.yaml` | Analytics/reporting/support permitted, marketing/advertising prohibited, wherever personal data lives. |
| `starter-ai-training-default-deny.yaml` | Model training denied by default on personal data; inference allowed with anonymization. |
| `starter-transfer-default-conditional.yaml` | Any export of personal data is conditional on recorded approval. |

No placeholders to edit: taxonomy targeting makes them estate-agnostic
(add `databases:`/`schemas:` under a selector to narrow scope). They are
DEFAULTS — replace them with asset-specific policies as your governance
matures; the AcmeCloud policy corpus (`sample-data/acmecloud/policies/`)
shows what the mature versions look like.

## 4. Measure the delta

```bash
python3 scripts/bootstrap_check.py
```

Tables with classified personal data now answer the baseline question from
published policy; everything else still answers honestly with
`not_enough_published_state` — your remaining-coverage worklist, exactly the
loop the [coverage-review walkthrough](walkthrough-coverage-review.md) runs
for the demo estate.

## 5. Point your tools at it

Everything in this repo now works against YOUR workspace: the notebooks in
live mode, the CI gate and dbt Action on your repos, the Claude Code plugin
and Claude Desktop for conversational questions, the evidence packet for
your auditors. Same decision layer, your data.
