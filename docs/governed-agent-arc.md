# The Governed Agent Arc

Every other example proves one decision at a time. The arc
(`governed_agent_arc/`, notebook `14_governed_agent_end_to_end.ipynb`) gives a
single LangGraph agent a realistic multi-part brief and lets governance
visibly change its course:

> "Build the EU churn dashboard, push the at-risk segment to Salesforce, and
> fine-tune the support assistant on ticket text."

## The five beats

1. **Rulebook first.** `inspect_governance_rules` on `customers` is a PLANNING
   input: the agent knows about the email mask, the AI-training deny, and the
   destination-aware transfer matrix before it drafts anything.
2. **The draft that had to change.** The first SQL references a masked column
   — `validate_query_context` says `warn`, the agent revises once (bounded by
   `MAX_REVISIONS`) and re-validates to `pass`. It never returns SQL Metatate
   has not passed; if the budget runs out it aborts that leg honestly.
3. **Conditional is a workflow, not a soft yes.** The Salesforce export comes
   back `conditional` (`approval_required` + `anonymize_first`,
   `can_proceed_now: false`). The arc reuses `human_exception_workflow`'s
   packet machinery (`item_from_answer` — no duplicate authorize call) and
   resumes only after the scripted reviewer attests BOTH controls.
4. **Deny becomes redirection.** Fine-tuning on raw ticket text is denied. The
   agent reroutes to the estate's sanctioned path — `ai.training` on
   `ml_feature_store` features — and that reroute is itself an evidenced
   `authorize_use`, never a workaround.
5. **The receipts.** `explain_why` chains over every collected `decision_id`;
   the acceptance asserts all four resolve and are `current`.

## Dual mode: planner vs governance

The planner seam (`governed_agent_arc/planner.py`) only drafts SQL, revises
after a verdict, and narrates. Governance calls and routing NEVER depend on
it.

- **Offline / CI (default):** the deterministic `ScriptedPlanner` walks the
  graph making only RECORDED fixture calls — the acceptance
  (`governed_agent_arc/acceptance.py`) pins the exact eleven-call sequence:
  `answered → allow → warn → pass → conditional → deny → allow → current ×4`.
- **Live LLM (opt-in):** set `METATATE_EXAMPLES_MODE=live` and
  `METATATE_EXAMPLES_LLM=<provider:model>` (anything LangChain's
  `init_chat_model` accepts; install `requirements-llm.txt` plus your
  provider extra). The model drafts and revises the SQL; every decision still
  comes from Metatate. Setting the LLM without live mode raises immediately —
  offline replay only answers recorded calls.

## Run it

```bash
# offline, deterministic
scripts/run_governed_agent_arc.sh
scripts/run_governed_agent_arc_acceptance.sh

# live against your workspace (docs/live-mode-saas.md), optional LLM drafting
export METATATE_EXAMPLES_MODE=live METATATE_MCP_URL=... METATATE_SAAS_MCP_TOKEN=...
export METATATE_EXAMPLES_LLM=anthropic:claude-sonnet-5   # optional
scripts/run_governed_agent_arc.sh
```

The CLI writes a machine-readable report (`ArcReport.to_dict()`): the decision
sequence, the exception packet, the resume payload, the reroute, and the
explain chain — the raw material for audit evidence.

## Why this is the flagship

The decision layer's pitch is not "agents can ask questions" — it is that an
agent BEHAVES DIFFERENTLY with governance in the loop: it plans from the
rulebook, revises instead of arguing, escalates instead of guessing, reroutes
instead of working around, and can prove every step afterwards. The arc is
that pitch, executable, in one file.
