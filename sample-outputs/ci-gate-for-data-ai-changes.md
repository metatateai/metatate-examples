# CI Gate For Data And AI Changes Output

The CI/CD gate evaluates five proposed pull request changes:

- an aggregate revenue dashboard passes
- an analytics detail model with identifiers requires controls
- a marketing activation SQL model fails
- a Salesforce export requires controls
- a support-ticket training job fails

The notebook prints denied changes without failing by default so readers can run it end to end. Set `METATATE_EXAMPLES_STRICT_CI_GATE=1` to make denied changes raise the same way a CI job would fail.

The command-line version is:

```bash
scripts/run_cicd_policy_gate.sh --strict
```
