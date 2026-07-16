# AcmeCloud Sample Data

AcmeCloud is a synthetic B2B SaaS dataset used across the Metatate examples.

## Contents

```text
tables/               CSV source tables for offline inspection
policies/             Example Metatate policy YAML
metatate-responses/   Offline response fixtures for the notebooks
```

The CSV data is intentionally small. The Metatate response fixtures represent
the decision-layer output produced after equivalent policies are deployed and
published in a Metatate Cloud workspace.

To run against this domain live, load it into your own workspace with the
one-click **Load the AcmeCloud demo** action (dashboard → "New here?" banner);
contributors running the local `metatate-saas` stack can apply
`metatate-saas/scripts/acmecloud-demo-fixtures.sh` instead. See
`docs/live-mode-saas.md`.
