# Release Process

This repository uses automated offline CI for every pull request and manual live validation before public releases.

## Pull Request Gate

Every pull request runs `.github/workflows/offline-ci.yml`.

The offline gate checks:

- static repository validation (including notebook-generator drift)
- shell syntax for all scripts
- Python compile checks
- CI/CD policy gate acceptance and CLI behavior
- human exception workflow acceptance and CLI behavior
- framework runtime acceptance for LangGraph, OpenAI Agents SDK, and LlamaIndex
- offline notebook pack execution

These checks use committed fixtures only. They do not require an account or endpoint.

## Live Release Gate

Before tagging a release, run `.github/workflows/live-saas-mcp-validation.yml` from GitHub Actions.

Required repository secrets:

- `METATATE_SAAS_MCP_URL` — a workspace MCP endpoint (Connect tab of the MCP module)
- `METATATE_SAAS_MCP_TOKEN` — a workspace-issued MCP access token (Tokens tab; never the deterministic local fixture token)

Prerequisite (operator step, not CI): the target workspace serves the AcmeCloud
demo publication — via the in-app **Load the AcmeCloud demo** action, or on a
local/staging stack via `metatate-saas/scripts/acmecloud-demo-fixtures.sh`.

The live gate checks:

- static repository validation
- CI/CD policy gate acceptance through the live MCP endpoint
- human exception workflow acceptance through the live MCP endpoint
- framework runtime acceptance through the live MCP endpoint
- live core notebook pack execution
- live LangGraph runtime notebook execution

## Tagging

Tag only from `main` after:

- the release PR has merged
- offline CI is green on `main`
- manual live SaaS validation has passed
- `CHANGELOG.md` has the intended release notes

```bash
git checkout main
git pull --ff-only origin main
git tag -a v<version> -m "metatate-examples v<version>"
git push origin v<version>
```

Releases use semantic version tags such as `v0.2.0`, `v0.2.1`, and `v1.0.0`.

## Release Notes

Release notes should state:

- which examples are included
- which examples run offline
- which examples were validated against a live workspace
- any required workspace, demo-domain, or token setup changes
