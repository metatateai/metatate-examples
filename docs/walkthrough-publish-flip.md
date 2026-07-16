# Walkthrough: Publish, And The Answer Changes

The sharpest property of Metatate's serving model: **live MCP answers change
only when a publication changes.** Drafts don't leak. Approvals don't leak.
The answer flips at publish — and `explain_why` tells you whether a cited
decision is still current.

This is a product-UI walkthrough (the MCP tools are read-only by design — no
tool can author or publish), so run it against your own workspace with the
AcmeCloud demo loaded and a terminal beside the app.

## 0. Baseline: a typed "I don't know"

`legacy_customer_backup` is cataloged but deliberately ungoverned:

```python
from common import get_client
client = get_client()  # METATATE_EXAMPLES_MODE=live

answer = client.authorize_use(
    {"database": "acmecloud_demo", "schema": "public", "table": "legacy_customer_backup"},
    use="report on the legacy customer backup",
    scenario_key="purpose.allowed_use",
)
print(answer["state"], answer.get("reason_code"))
# -> not_enough_published_state no_published_instruction_state
```

Metatate does not guess. No policy row is published for this asset, so the
answer is a typed insufficient-state — never a silent pass, never a
fabricated decision.

## 1. Author a policy (nothing changes)

In the app: **Policies → New policy**. Target
`acmecloud_demo.public.legacy_customer_backup`, permit `analytics` and
`reporting`, and save the draft.

Re-run the call above: **still `not_enough_published_state`.** Drafts are
authoring state, not serving state.

## 2. Approve it (still nothing changes)

Review and approve the policy version. Re-run the call:
**still `not_enough_published_state`.** An approved-but-unpublished version
never affects live answers — the serving boundary is the publication, not
the approval.

## 3. Publish (the answer flips)

**Deployments → generate a plan** including the new policy → review the
serving bundle preview → **publish**. Re-run the call:

```text
answered allow
```

The flip happened at exactly one moment: publication. The answer now carries
the citing instruction with full provenance and a `decision_id`.

## 4. Explain it — and watch `current`

```python
explanation = client.explain_why(answer["decision_id"])
print(explanation["current"])   # -> True
```

Now edit the policy (say, prohibit `reporting`), approve, and publish again.
The authorize answer changes with the new publication — and explaining the
OLD `decision_id` still works, with `current: False`: the decision is
historical, honestly labeled, never rewritten.

## Why this matters

Agents and CI gates can trust that a decision they were served corresponds to
a specific published state, that pending governance work can't half-apply,
and that every answer is reconstructible after the fact. That is the
difference between "the model said so" and a governed decision.
