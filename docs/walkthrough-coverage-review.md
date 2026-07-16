# Walkthrough: Coverage Review — Finding And Closing Governance Gaps

Real estates are never perfectly governed, and the AcmeCloud demo is honest
about that on purpose: `legacy_customer_backup` is cataloged but has **no
policy at all**. This walkthrough is the governance-lead arc — find the gap,
see how it answers, close it, and watch the answer change.

Run it with the `metatate` plugin in Claude Code
([setup](walkthrough-claude-code.md)) against a workspace serving the
AcmeCloud demo.

## 1. Review coverage

```text
/metatate:policy-review
Review policy coverage for the acmecloud_demo.public schema. What is
ungoverned or thin?
```

Claude sweeps the governed context and reports the gaps. Expect at minimum:

- **`legacy_customer_backup` — ungoverned.** Cataloged, columns visible, zero
  published instructions. It contains what its name says: a stale copy of
  customer PII, outside every policy.
- Thin spots worth judgment calls: no explicit rules for scenarios you may
  care about (e.g. retention on telemetry, subject-rights handling), and any
  asset whose only coverage is table-level classification context.

## 2. See how a gap answers

```text
/metatate:authorize-use
Can we use legacy_customer_backup for analytics?
```

Typed `not_enough_published_state` / `no_published_instruction_state`. Agents
get told "governance cannot answer this yet" — not a silent pass, not an
invented deny. Gaps are *visible* at the decision layer, which is what makes
the review loop work.

## 3. Close the gap

Two good endings, depending on what the data actually is:

- **Govern it**: author a policy for `legacy_customer_backup` (the
  [publish-flip walkthrough](walkthrough-publish-flip.md) does exactly this —
  author → approve → publish → the answer flips to a real decision).
- **Retire it**: the honest review outcome for a stale PII copy is often
  deletion. Metatate's part is making sure that decision is made by a person
  looking at a typed gap report — not discovered in an incident.

## 4. Gate the release

For repository changes (new models, export jobs, AI workflows), the same
review runs as an advisory gate:

```text
/metatate:release-gate
Review this change set before release.
```

— or in CI, `scripts/run_cicd_policy_gate.sh --strict`
([docs/ci-cd-policy-gate.md](ci-cd-policy-gate.md)), where the pull-request
fixture shows the exact splits: safe aggregate passes, PII detail needs
controls, the marketing model fails, the Salesforce sync needs approval +
anonymization, the ticket fine-tune is blocked.

## The loop

Discover → review coverage → see gaps answer honestly → govern or retire →
publish → the answers change. Every step is typed, cited, and reconstructible
— that's governance as an operating loop, not a document.
