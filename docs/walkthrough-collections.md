# Walkthrough: Group Once, Govern The Group (Collections)

AcmeCloud's "Customer 360" is a **collection**: five tables that mean one
thing to the business. One policy targets the collection by id — and at
deploy time, Metatate expands it to serving rows for every member, each
answer citing the collection as its resolution path. Membership changes are
a deployment, not a re-authoring exercise.

This is a product-UI walkthrough (the MCP tools are read-only by design), so
run it against your own workspace with the AcmeCloud demo loaded and a
terminal beside the app.

## 0. See the group

**Catalog → Collections → Customer 360.** Five members: `customers`,
`subscriptions`, `support_tickets`, `customer_exports`, `ml_feature_store`.

## 1. See the policy that targets it

**Policies → "AcmeCloud Customer 360 context."** The target is the
collection itself — not a list of tables. The policy permits
`customer_360_reporting` (served under the `sharing.internal` scenario) for
whatever the collection contains at publish time.

## 2. Ask about a member — the answer cites the collection

```python
from common import get_client
client = get_client()  # METATATE_EXAMPLES_MODE=live

answer = client.authorize_use(
    {"database": "acmecloud_demo", "schema": "public", "table": "subscriptions"},
    use="share account health summaries with the success team",
    scenario_key="sharing.internal",
)
winner = answer["instructions"][0]
print(answer["state"], answer["decision"])          # -> answered allow
print(winner["primary_resolution_source"])          # -> collection
print(winner["resolution_paths"])                   # -> [{"ref": "<collection-id>", "source": "collection"}]
```

The serving row exists on `subscriptions` **because** it is a Customer 360
member, and the answer says so — provenance down to the resolution path.

## 3. Ask about a non-member — the boundary is real

```python
answer = client.authorize_use(
    {"database": "acmecloud_demo", "schema": "public", "table": "product_usage_events"},
    use="share usage summaries with the success team",
    scenario_key="sharing.internal",
)
print(answer["state"], answer.get("reason_code"))
# -> not_enough_published_state no_published_instruction_state
```

`product_usage_events` is governed for other scenarios, but it is not in the
collection, so no internal-sharing row exists for it — a typed
insufficient-state, not a guessed yes.

## 4. Move the boundary (a deployment, not a rewrite)

In **Catalog → Collections → Customer 360**, add `product_usage_events` as a
member. Nothing changes yet — membership edits are catalog state.

Open **Deployments**: the membership change appears as a pending catalog
change. Review the plan (the preview shows the new member picking up the
collection-targeted instructions) and **publish**.

## 5. Ask again — the group followed the membership

Re-run the step-3 call: **`answered allow`**, with the same collection
citation as step 2. Nobody edited a policy. The group moved; governance
followed at publish.

## 6. Restore the spec

This workspace also serves the recorded expected-decisions the notebooks
replay, so put it back: remove `product_usage_events` from the collection
and publish again. The step-3 answer returns to the typed insufficient-state.

## Why this matters

- **Collections are deploy-time expansion.** Policies stay written against
  the business concept; deployment resolves the concept to concrete serving
  rows. That is why the MCP surface has no collections API — consumers see
  the *result*, with the collection cited in `resolution_paths`.
- **Membership is governance-bearing state** with a publication boundary:
  adding a table to Customer 360 is reviewed and published like any other
  serving change, and answers flip only at publish (see the
  [publish-flip walkthrough](walkthrough-publish-flip.md)).
- Notebook 12 replays the collection citation offline; this walkthrough is
  the live-product counterpart.
