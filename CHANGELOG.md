# Changelog

## Unreleased

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

- Rebuilt the examples repo around the AcmeCloud synthetic B2B SaaS dataset.
- Added offline Metatate response fixtures.
- Added live Snowflake fixture SQL aligned with the Native App MCP serving-table model.
- Added four starter notebooks:
  - setup: live or offline
  - decision-layer cookbook
  - governed SQL agent with LangGraph
  - transfer governance before export
