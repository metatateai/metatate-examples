# B3 purpose conversion — mapping manifest and provenance

What changed when the pack converted to B3's purposeful-call contract, why each
case answers the way it does, and what is deliberately *not* claimed.

There are **no aliases, no approximate matching, and no fallback** between
purposeful and purpose-blind recordings. `purpose_key` is part of the offline
router's exact match key, so a call that declares a different purpose — or none —
is a different question and resolves to a different recording or to
`offline_fixture_missing`.

## Why the pack is clearer than it was

Before B3 these cases were a fairly uniform set of allows. The estate now
demonstrates a **three-way boundary** on the same assets:

| The question asked | Answer | What a reader learns |
| --- | --- | --- |
| A purpose the published policy covers | `answered` / `allow` | declaring *why* is what earns the decision |
| A **valid** purpose the policy's legacy authoring cannot cover | `review_required` | a real purpose is not automatically a permitted one |
| **No** purpose, or an intent the registry cannot express | `review_required` | absence fails closed; Metatate does not guess |

The third row is the one worth stressing: fail-closed is not the system being
strict, it is the system refusing to invent a purpose you did not declare.

## Categories and keys — a family grant, a leaf call

This is intentional vocabulary design, not a legacy artifact, and the demo has
said so in a comment since before B3 landed
(`expected-decisions.yaml`: *"the permitted-uses list names the `analytics`
CATEGORY, so a call stating any `analytics.*` purpose matches"*).

**A policy may grant a whole family; a caller states one leaf; the leaf matches
because it belongs to the family.**

```
policy   permittedUses: [analytics, ...]     <- the analytics CATEGORY
caller   purpose_key = "analytics.reporting"  <- a leaf inside it
result   match
```

Both statements are correct and they are **not the same statement**. Collapsing
the policy entry to `analytics.reporting` would silently shrink a family-wide
grant to a single purpose, so the inventory records it as a category and the
acceptance suite asserts it is never narrowed.

Category-vs-key is decided **mechanically**, not by a lookup table: an entry is a
category reference iff it byte-equals a registry family token, and the two
namespaces are disjoint by construction — every key contains a `.`, no family
token does. `ai` is therefore a category because it is the family of
`ai.inference`; `analytics.reporting` is a key because it has a dot.

Category tokens in this pack:

| entry | list | breadth | resolves in (current pack) |
| --- | --- | --- | --- |
| `ai` | prohibited | `ai.*` | 1 case(s) |
| `analytics` | permitted | `analytics.*` | 9 case(s) |
| `marketing` | prohibited | `marketing.*` | 3 case(s) |

The **breadth** column is the durable contract. The **resolves in** column is a
*measurement of the current example set* — adding or removing a legitimate
purposeful case moves it without touching the grant, so the suite reports it and
deliberately does not assert it.

And the pairing that makes the design legible: a purpose-**blind** call on those
same rows still fails closed to review. The family grant says *which* purposes
are permitted; it never says a caller may decline to state one.

## The three-way boundary, taught rather than inferred

| The question asked | Answer | Why |
| --- | --- | --- |
| A purpose the policy covers | `answered` / `allow` | `analytics-customers-allow` declares `analytics.reporting`; the policy grants the `analytics` family, so the leaf matches. |
| A **valid** purpose the policy's legacy authoring cannot cover | `review_required` | `support-tickets-…` declares `operations.support` — a real registered purpose. The policy's authored entries are legacy free strings that cannot prove coverage. |
| **No** purpose at all | `review_required` | `analytics-customers-purpose-missing-review` asks the identical question minus the purpose. One absent key, a different answer. |

**The sharpest case is `ml-embedding-storage-review`.** It **declares** a valid
`ai.inference` and *still* reviews — because the policy's authored
`embedding_storage` entry says feature vectors may be **STORED**, which never
established inference use. Declaring a good purpose does not rescue an authored
entry that cannot prove coverage. That is the whole lesson in one case, and it is
why the entry carries a standing *do not map* ruling: mapping it to
`ai.inference` would infer coverage the author never wrote.

## Renames — resynced to canonical

The three renames carried in an earlier revision of this branch asserted a reason
that turned out to be false, and they are gone. Canonical ids and outcomes were
re-derived from publication `7b10b30f` after the staging reinstall:

| earlier (withdrawn) | canonical | live outcome |
| --- | --- | --- |
| `ml-retrieval-context-purpose-inexpressible-review` | **`ml-retrieval-context-allow`** | `answered` / allow, `ai.inference` |
| `customer-360-internal-sharing-purpose-inexpressible-review` | **`customer-360-internal-sharing-allow`** | `answered` / allow, `analytics.reporting` |
| `ml-embedding-storage-purpose-inexpressible-review` | **`ml-embedding-storage-review`** | `review_required`, `ai.inference` |

Two of those three were **mapped** by #374 (`retrieval_context` → `ai.inference`,
`customer_360_reporting` → `analytics.reporting`); calling them inexpressible was
wrong. The third is genuinely unmappable but its *purpose* is expressible — what
cannot prove coverage is the policy's authored entry. The earlier recordings that
suggested otherwise were the stale pre-B3P publication, the same root cause as the
finance divergence.

**Examples-only additions** (not in the metatate-saas matrix), both deliberate
demonstrations of the fail-closed legs: `analytics-customers-purpose-missing-review`
and `support-tickets-unmapped-policy-use-review`.


## Per-case provenance

Read from the recorded live answers against publication `7b10b30f` — not asserted.
`evaluated_purpose` is the server echoing back the purpose it actually evaluated,
which is what proves the declared value reached the decision rather than decorating
the call.

| Case | Declared | `evaluated_purpose` | State | Citing family | `usage_guidance` rows |
| --- | --- | --- | --- | --- | --- |
| `analytics-customers-allow` | `analytics.reporting` | `analytics.reporting` | answered allow | `usage_guidance` | 1 |
| `cte-subscriptions-aggregate-pass` | `analytics.reporting` | `analytics.reporting` | answered pass | `usage_guidance` | 1 |
| `customer-360-internal-sharing-allow` | `analytics.reporting` | `analytics.reporting` | answered allow | `usage_guidance` | 1 |
| `finance-cross-schema-join-pass` | `compliance.reporting` | `compliance.reporting` | answered pass | `usage_guidance` | 2 |
| `finance-invoices-allowed-use` | `compliance.reporting` | `compliance.reporting` | answered allow | `usage_guidance` | 1 |
| `join-customers-subscriptions-pass` | `analytics.reporting` | `analytics.reporting` | answered pass | `usage_guidance` | 2 |
| `join-legacy-ungoverned-warn` | `analytics.reporting` | `analytics.reporting` | answered warn | `usage_guidance` | 1 |
| `ml-embedding-storage-review` | `ai.inference` | `ai.inference` | review_required require_review | `usage_guidance` | 1 |
| `ml-retrieval-context-allow` | `ai.inference` | `ai.inference` | answered allow | `usage_guidance` | 1 |
| `safe-aggregate-pass` | `analytics.reporting` | `analytics.reporting` | answered pass | `usage_guidance` | 1 |
| `same-sql-analytics-intent-pass` | `analytics.reporting` | `analytics.reporting` | answered pass | `usage_guidance` | 1 |
| `support-tickets-unmapped-policy-use-review` | `operations.support` | `operations.support` | review_required require_review | `usage_guidance` | 1 |

### Not every allow is coverage-driven — say so plainly

Every case that *declares* a purpose above cites at least one `usage_guidance`
row, so for those the purpose genuinely did the work.

The interesting cases are the **purpose-blind allows**. 2 authorize
cases answer `allow` while citing **zero** `usage_guidance` rows:

- `inference-customers-allow` — cites `ai_governance`
- `ml-training-features-allow` — cites `ai_governance`

These are authorized by AI governance for the asset, not by a permitted use
matching a purpose — which is exactly why canonical declares **no** purpose for
them. Reading "declare a purpose → get an allow" as the mechanism would be wrong,
and it is why I removed the purposes an earlier revision had added to them.
**The mechanism is whatever the citation says it is.**


## The finance divergence — RESOLVED, not quarantined

It was withdrawn from current-behaviour claims while unexplained. The cause was
then diagnosed and fixed rather than papered over: staging was serving a
publication from `2026-07-23T22:02Z` while the purpose vocabulary migrated on
07-29, so current B3 semantics were evaluating **pre-B3P serving rows** — under
which an unmapped legacy entry correctly cannot prove coverage, so `allow` became
`require_review`. Neither implementation was at fault; the live answer was correct
behaviour on stale input.

After the staging reinstall (publication `7b10b30f`) and the canonical policy
re-sync, live and offline agree and both cases are **back in the matrix** with
their canonical purposes:

| case | purpose | live |
| --- | --- | --- |
| `finance-invoices-allowed-use` | `compliance.reporting` | `answered` / allow |
| `finance-cross-schema-join-pass` | `compliance.reporting` | `answered` / pass |

The notebook sections that demonstrated them are restored. Nothing was edited to
agree — the recordings are live output from the verified publication.


## What enforces all of this

`scripts/purpose_contract_acceptance.py` (wired into offline CI). It asserts,
among other things, that: every case is reachable through the **typed** client;
dropping or mutating `purpose_key` never silently lands on another recording;
purpose-blind controls match their own recordings **and** a purposeful call never
lands on a blind control; every recording maps to a live case (no rename
orphans); every expectation matches its recording (the stale-claim guard); and no
quarantined id leaks back into a current-behaviour section.
