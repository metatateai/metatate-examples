# Expected Output — The Audit Evidence Packet

Captured from the executed OFFLINE notebook (`notebooks/15_audit_evidence_packet.ipynb`), which replays
recorded Metatate Cloud answers — live mode against a workspace serving the
AcmeCloud demo publication produces the same decisions.


```text
decisions: 6
explained and current: 4/4
honest corners: 2
publication: accef000-0000-4000-8000-000000000001
```

```text
# Metatate evidence packet

Publication `accef000-0000-4000-8000-000000000001` (published 2026-07-16T00:00:00.000Z).
6 governed decisions; 4/4 explained and CURRENT; 2 honest corners (no fabricated answers).

## Decisions

### 1. Can we build a churn analytics dashboard on customers?
- Asset: `acmecloud_demo.public.customers` — scenario `purpose.allowed_use`
- Decision: **allow** (state answered)
- Evidence: `accef000-0000-4000-8000-000000000020`
- Cited policy: AcmeCloud customer use guardrails v1 (instruction `usage_guidance:spec.usage.permittedUses:permitted`)
- Explain chain: current = true

### 2. Can we sync approved customer fields to Salesforce for EU consumers?
- Asset: `acmecloud_demo.public.customers` — scenario `residency.cross_border_transfer`
- Decision: **conditional** (state answered)
- Evidence: `accef000-0000-4000-8000-000000000010`
- Cited policy: AcmeCloud transfer guardrails v1 (instruction `transfer_governance:spec.transferGovernance`)
- Conditions: anonymize_first, approval_required
- Explain chain: current = true

### 3. Can we fine-tune the support assistant on raw ticket text?
- Asset: `acmecloud_demo.public.support_tickets` — scenario `ai.training`
- Decision: **deny** (state answered)
- Evidence: `accef000-0000-4000-8000-000000000043`
- Cited policy: AcmeCloud customer use guardrails v1 (instruction `ai_governance:spec.aiGovernance:training`)
- Prohibitions cited: 1
- Explain chain: current = true

### 4. Can we train the churn model on derived features instead?
- Asset: `acmecloud_demo.public.ml_feature_store` — scenario `ai.training`
- Decision: **allow** (state answered)
- Evidence: `accef000-0000-4000-8000-000000000064`
- Cited policy: AcmeCloud ML feature AI lifecycle v1 (instruction `ai_governance:spec.aiGovernance:training`)
- Explain chain: current = true

## Honest corners

- `acmecloud_demo.public.legacy_customer_backup` (purpose.allowed_use): **not_enough_published_state** (no_published_instruction_state) — the estate refused to guess.
- `acmecloud_demo.public.employees.full_name` (masking.display): **review_required** (decision_requires_review) — the estate refused to guess.

## Ledger

Every call above is also in the workspace's server-side request log (MCP Tools → Tokens → View requests). Advisory answers, accountable trail: decision ids resolve via `explain_why` for as long as the history is retained, and `current` flags decisions superseded by a later publication.
```
