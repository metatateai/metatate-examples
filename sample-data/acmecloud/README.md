# AcmeCloud Sample Data

AcmeCloud is a synthetic B2B SaaS dataset used across the Metatate examples.

## Contents

```text
catalog.yaml            Estate spec: tables, columns, descriptions, tags, and
                        column classifications (built-in taxonomy + custom types)
policies/               Six real Metatate Cloud policy DSL documents
expected-decisions.yaml The behavior contract: governed question -> expected answer
tables/                 CSV source tables for offline inspection
metatate-responses/     Offline response fixtures for the notebooks
```

`catalog.yaml` also declares the demo's catalog COLLECTIONS ("Customer 360"),
which the collection-targeted policy references by id.

`catalog.yaml`, `policies/`, and `expected-decisions.yaml` together are the
**estate spec** — the single source of truth for the demo domain. The
Metatate Cloud one-click demo is derived from this spec by the product's
real governance engine (parsed by policy-core, materialized by
governance-core), and the expected-decisions matrix is asserted against the
derived state in the product's test suite. Nothing downstream is
hand-authored.

The CSV data is intentionally small. The Metatate response fixtures represent
the decision-layer output produced after equivalent policies are deployed and
published in a Metatate Cloud workspace.

To run against this domain live, load it into your own workspace with the
one-click **Load the AcmeCloud demo** action (dashboard → "New here?" banner);
contributors running the local `metatate-saas` stack can apply
`metatate-saas/scripts/acmecloud-demo-fixtures.sh` instead. See
`docs/live-mode-saas.md`.
