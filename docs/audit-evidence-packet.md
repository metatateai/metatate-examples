# The Audit Evidence Packet

"Advisory" does not mean unaccountable. Every Metatate answer carries a
`decision_id`, publication provenance, and cited policy versions —
`audit_evidence/` (and notebook `15_audit_evidence_packet.ipynb`) turns a day
of governed questions into a single audit-ready report:

- **Decisions with receipts.** Each answered question lists the asset,
  scenario, typed decision, the citing policy BY NAME AND VERSION, the
  instruction key, conditions/obligations, and the `decision_id` — then
  chains `explain_why` to prove the decision resolves and is still CURRENT
  in the live publication. A decision superseded by a later publish shows
  `current: false` — historical, honestly labeled, never rewritten (see the
  publish-flip walkthrough).
- **Honest corners, on the record.** The packet's second section lists every
  question the estate refused to guess at — the ungoverned legacy table
  (`not_enough_published_state`) and the monitored custom mask
  (`review_required`). An evidence trail that hides its gaps isn't evidence.
- **The server keeps its own ledger.** Every call also lands in the
  workspace's request log — MCP Tools → Tokens → **View requests** — so the
  packet and the server-side trail corroborate each other.

## Run it

```bash
scripts/run_audit_evidence.sh              # JSON packet + audit-ready markdown
scripts/run_audit_evidence_acceptance.sh   # pins the packet structure
```

Offline (default) the packet replays recorded answers; in live mode
(`docs/live-mode-saas.md`) it collects real evidence from your workspace.
`collect_evidence(client, questions=…)` accepts your own question list — the
same shape as `DEFAULT_QUESTIONS` — so a team can codify ITS recurring
data-use questions and regenerate the packet on a schedule. The governed
agent arc's report (`scripts/run_governed_agent_arc.sh`) is the same raw
material from an agent run: decision ids in, explanations out.
