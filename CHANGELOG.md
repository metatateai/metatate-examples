# Changelog

## Unreleased

- **Four vertical scenario packs — the estate speaks four industries.** AdTech
  (consent as three purpose-scoped permissions, served as typed
  `consent_required` conditions that are never caller-satisfiable), Payments
  (the settlement source-of-truth authority matrix), Healthcare (one person as
  four role-bound contexts — four new recording credentials with role-aware
  offline routing), and Government (date-effective statute policies with the
  `data_access_context.as_of` flip, band precedence, and the second sanctioned
  conflict pair, `verification_outreach`). Seven new governed tables across the
  new `care` and `benefits` logical databases, seventeen new policies (37
  total), forty-six appended canonical cases (118 recordings), and notebooks
  17-20 named after the use cases they model. The offline router now carries
  the credential's `bound_role` in the match signature — byte-identical calls
  under different role-bound tokens are different questions with different
  recordings, offline exactly as live.

- **B3 purposeful calls end to end.** Every governed call declares the
  `purpose_key` its canonical case declares, and the offline router matches on it
  **exactly** — no aliases, no approximate matching, no fallback between
  purposeful and purpose-blind recordings. `purpose_key` is now a parameter on
  `authorize_use` and `validate_query_context` on both clients; previously it
  existed in the canonical cases but **no client could emit it**, so nine cases
  were unreachable and one silently re-routed to its purpose-blind twin.

  All case ids, purposes and outcomes are **re-synced from `metatate-saas`
  `origin/main` (`00fed9f`)** and all 58 recordings **re-recorded live** against
  publication `7b10b30f`. Zero mismatches: **63 canonical scalar expectations
  matched by live output.** Nothing hand-edited.

  **Categories and keys.** A policy may grant a whole family (`analytics`) while a
  caller states one leaf (`analytics.reporting`); the leaf matches because it
  belongs to the family. This is intentional vocabulary design. Category-vs-key is
  decided mechanically — an entry is a category iff it byte-equals a registry
  family token, and the namespaces are disjoint because every key contains a dot
  and no family token does. Categories are asserted **never to be narrowed** to a
  single key, since collapsing `analytics` to `analytics.reporting` would silently
  shrink a family-wide grant.

  **The three-way boundary is now taught, not inferred:** a covered purpose →
  `allow`; a *valid* purpose the policy's legacy authoring cannot cover →
  `review_required`; no purpose at all → `review_required`. The sharpest case is
  `ml-embedding-storage-review`, which **declares** a valid `ai.inference` and
  *still* reviews, because the policy's authored `embedding_storage` entry says
  vectors may be STORED — which never established inference use. It carries a
  standing *do not map* ruling for exactly that reason.

  New gates in offline CI: `scripts/run_purpose_contract_acceptance.sh` (router
  exactness, consumer↔case exactness, both directions of the purpose boundary,
  cross-surface consistency, the stale-claim guard, the do-not-map tripwire, and
  the served-use inventory assertions) and a **release gate**
  `scripts/live_expected_decision_parity.py` in the live workflow.

- **Served-use inventory** (`sample-data/customer-360/served-use-inventory.json`,
  generated). The pack serves **18 distinct authored entries across 19
  (entry, list-kind) pairs**; the #374 change-set manifest covers 9, and had been
  read as a complete inventory. The inventory is generated from the canonical
  policy pack and cross-checked against live serving state in both directions,
  reading **only** structured `usage_guidance.parameters.uses` — never prose or
  serialized parameters, which is enforced by an assertion after a coarse
  substring sweep elsewhere matched an English sentence in a `log_only` row.

  Vocabulary disposition is modelled **separately** from occurrence inventory:
  occurrences retain policy, list kind, and entry, so `prospect_outreach` being
  permitted in one policy and prohibited in another cannot collapse. That pair is
  the deliberate governance-debt conflict fixture and is asserted to survive.

- **The finance divergence: diagnosed and resolved, not papered over.** Staging had
  been serving a publication from `2026-07-23T22:02Z` while the purpose vocabulary
  migrated on 07-29, so current B3 semantics were evaluating pre-B3P serving rows —
  under which an unmapped legacy entry correctly cannot prove coverage, turning
  `allow` into `require_review`. Neither implementation was at fault. After the
  staging reinstall and the canonical policy re-sync, live and offline agree;
  both finance cases are back in the matrix with `compliance.reporting`, and the
  notebook sections that demonstrated them are restored.

- BYO-estate bootstrap: `docs/walkthrough-byo-estate.md` bridges from the
  Customer 360 demo to YOUR data — connect any of the six connector kinds,
  review classification, publish the new `starter-policies/` pack (four
  estate-agnostic, TAXONOMY-targeted DataPolicy templates: email masking,
  PII usage guardrails, AI-training default-deny, transfers
  default-conditional — no placeholders to edit), and measure the coverage
  delta with `scripts/bootstrap_check.py` (live-only, estate-agnostic:
  discover → baseline authorize per governed table → typed-state summary).

- The audit evidence packet (`audit_evidence/`, notebook
  `15_audit_evidence_packet.ipynb`): a day of governed questions rendered as
  an audit-ready report — decisions with policy-version citations and
  evidence ids, the `explain_why` chain proving each decision is CURRENT,
  and the honest corners (the ungoverned legacy table, the monitored custom
  mask) on the record instead of hidden. `collect_evidence(client,
  questions=…)` codifies a team's own recurring questions; the workspace's
  request log (MCP Tools → Tokens → View requests) corroborates the packet
  server-side.

- Governance in the pull request: `cicd_policy_gate/dbt_adapter.py` turns a
  dbt `target/manifest.json` into the gate's change set (full /
  checksum-diff / changed-files selection; models validated with their own
  database/schema defaults and an optional `meta.metatate.scenario_key`
  intent; exposures gated only when annotated with `meta.metatate` — never
  guessed; every skipped resource reported). The repo root now ships a
  reusable composite GitHub Action (`action.yml`): adapter → gate →
  job-summary verdict table → upserted PR comment → strict enforcement LAST,
  so the comment always posts before the job fails. A runnable sample dbt
  project + checked-in manifest fixtures replay the canonical pr-042 matrix
  offline with zero new recordings, and CI smoke-tests the action end to end.

- FLAGSHIP: the governed agent arc (`governed_agent_arc/`, notebook
  `14_governed_agent_end_to_end.ipynb`) — one realistic brief on a LangGraph
  runtime, visibly changing course because of governance: rulebook-first
  planning, a warned SQL draft self-revised to pass, a conditional Salesforce
  export resumed only with attested controls (reusing the human-exception
  packet machinery via the new `item_from_answer` export), a denied fine-tune
  REROUTED to the governed feature-store alternative, and `explain_why`
  chained over every collected decision id. Acceptance pins the exact
  eleven-call decision sequence; an optional provider-neutral LLM planner
  (`METATATE_EXAMPLES_LLM`, `requirements-llm.txt`) drafts SQL in live mode
  while governance calls stay identical. CI never calls an LLM.
- The README hero is now GENERATED (`scripts/build_readme_hero.py`,
  drift-gated like the notebooks) and tells the arc's story on the current
  typed-answer contract — the previous hand-authored SVG still demoed the
  pre-split positional-argument calls and stale estate counts.
- Offline recordings refreshed against current metatate-saas main: answers now
  carry the additive `authorization_id` / `validation_id` / `finding_id`
  fields (server request-log ids), plus the two explain recordings the arc
  chains (`explain_train_deny_decision`, `explain_ml_training_decision`).

- The pack is NATIVE to the Metatate Cloud typed-answer contract: notebooks,
  the CI/CD gate, the human-exception workflow, and the framework harness all
  send structured asset refs + canonical scenario keys and read typed answers
  (`state`, lowercase decisions, `verdict`, structured conditions/obligations,
  cited instructions, publication provenance). The client translation layer is
  gone.
- Offline fixtures are RECORDED from a live workspace
  (`scripts/record_offline_fixtures.py` over the canonical case set in
  `common/fixture_cases.py`), uuid-normalized but internally consistent —
  offline `explain_why` chains real recorded `decision_id`s.
- `sample-outputs/` is regenerated from the executed offline notebooks.
- Split the repository: this repo is now the Metatate Cloud examples cookbook.
  The Snowflake Native App pack (Cortex notebooks and runtime acceptance,
  `sql/` fixtures, PAT tooling, live managed-MCP validation) is frozen at
  [metatate-snowflake-examples](https://github.com/metatateai/metatate-snowflake-examples).
  Live mode now defaults to the Metatate Cloud backend; the notebook pack is
  renumbered `00`–`11`.
- Notebooks are validated against `scripts/build_notebooks.py` in CI
  (`--check`): hand edits to generated `.ipynb` files now fail validation
  instead of being silently lost on the next regeneration.
- Added a live "saas" backend (`METATATE_MCP_BACKEND=saas`) that runs the full
  notebook pack and acceptance scripts against the Metatate SaaS
  cross-platform MCP endpoint with a workspace bearer token, including
  destination-aware export decisions and native `explain_why` chaining
  (see docs/live-mode-saas.md).
- Added a manual live SaaS MCP validation workflow
  (`.github/workflows/live-saas-mcp-validation.yml`).
- Added GitHub Actions offline CI for pull requests.
- Added a manual live managed MCP validation workflow for release candidates.
- Added release process documentation for offline CI, live MCP validation, and public tags.
- Added Wave 1 agent-governance examples: governed text-to-SQL, red-team evaluation, and CI/CD data/AI policy gates.
- Added Wave 2 integration examples: governed RAG/embedding ingestion, Cortex-style tool preflight, OpenAI-style tool guards, human exception workflows, and LlamaIndex-style governed retrieval.
- Added offline Metatate fixtures for safe analytics, marketing denial, and AI training denial query validation.
- Changed live notebook mode to call the Snowflake-managed Metatate MCP server
  over HTTP with a role-restricted PAT.
- Removed the direct Snowflake SQL connector live path from examples.

## 0.1.0

- Rebuilt the examples repo around the Customer 360 synthetic B2B SaaS dataset.
- Added offline Metatate response fixtures.
- Added live Snowflake fixture SQL aligned with the Native App MCP serving-table model.
- Added four starter notebooks:
  - setup: live or offline
  - decision-layer cookbook
  - governed SQL agent with LangGraph
  - transfer governance before export
