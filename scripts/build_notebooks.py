#!/usr/bin/env python3
"""Render the public notebook pack from Python cell definitions.

Every notebook speaks the NATIVE Metatate Cloud contract: structured asset
references, canonical scenario keys, and typed answers
(`state` / `decision` / `verdict` / `conditions` / `obligations` /
`instructions` / `publication`). Offline calls match the recorded case set in
`common/fixture_cases.py` exactly, so offline output is byte-shaped like the
live endpoint's.
"""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = ROOT / "notebooks"


def markdown(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": _lines(source)}


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": _lines(source),
    }


def _lines(source: str) -> list[str]:
    text = dedent(source).strip("\n")
    return [line + "\n" for line in text.splitlines()]


def notebook(cells: list[dict]) -> dict:
    for index, cell in enumerate(cells, start=1):
        cell["id"] = f"cell-{index:03d}"
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "pygments_lexer": "ipython3",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


SETUP_CELL = """
from pathlib import Path
import json
import os
import sys

import pandas as pd

repo_root = Path.cwd()
if repo_root.name == "notebooks":
    repo_root = repo_root.parent
sys.path.insert(0, str(repo_root))

from common import get_client

mode = os.getenv("METATATE_EXAMPLES_MODE", "offline")
if mode == "live" and not os.getenv("METATATE_MCP_URL"):
    print("Live mode needs a Metatate endpoint. Fastest path (about 5 minutes):")
    print("  1. Create a free account: https://app.getmetatate.com/sign-up?ref=examples")
    print("  2. Workspace dashboard: 'Load the demo' banner -> 'Load the Customer 360 demo'")
    print("  3. MCP Tools -> Tokens: issue a token; Connect tab has your endpoint URL")
    print("  4. export METATATE_MCP_URL=... METATATE_SAAS_MCP_TOKEN=...")
    print("     (full steps: docs/live-mode-saas.md)")

client = get_client()
print(f"Metatate examples mode: {mode}")


PRODUCT_DATABASE_TABLES = {"product_usage_events", "support_tickets", "ml_feature_store"}


def asset(table, column=None, schema="public", database=None):
    resolved_database = database or (
        "product" if table in PRODUCT_DATABASE_TABLES else "master"
    )
    ref = {"database": resolved_database, "schema": schema, "table": table}
    if column:
        ref["column"] = column
    return ref


def answer_label(answer):
    state = answer.get("state")
    if state and state != "answered":
        return state
    return answer.get("decision") or answer.get("verdict") or "unknown"


def print_answer(answer):
    print(f"state:    {answer.get('state')}")
    if "decision" in answer:
        print(f"decision: {answer['decision']}")
    if "verdict" in answer:
        print(f"verdict:  {answer['verdict']}")
    if answer.get("reason"):
        print(f"reason:   {answer['reason']}")
    for condition in answer.get("conditions") or []:
        print(f"condition [{condition.get('kind')}]: {condition.get('requirement')}")
    for prohibition in answer.get("prohibitions") or []:
        print(f"prohibition: {prohibition.get('detail')}")
    for obligation in answer.get("obligations") or []:
        print(f"obligation [{obligation.get('type')}]: {obligation.get('target')}")
    if "can_proceed_now" in answer:
        print(f"can_proceed_now: {answer['can_proceed_now']}")
"""


def setup_notebook() -> dict:
    return notebook(
        [
            markdown(
                """
                # 00 - Setup: Live Or Offline

                This notebook checks the Customer 360 fixture and initializes the shared Metatate client.

                Offline mode is the default. It replays RECORDED Metatate Cloud answers (captured
                from a live workspace by `scripts/record_offline_fixtures.py`), so what you study
                offline is exactly what the live endpoint returns — typed answers with
                `state`, lowercase decision vocabulary, structured conditions, and publication provenance.

                Live mode calls your Metatate Cloud workspace's MCP endpoint (no account yet? create one free at [app.getmetatate.com/sign-up?ref=examples](https://app.getmetatate.com/sign-up?ref=examples) and load the Customer 360 demo from the dashboard's **"New here?" banner → Load the demo**). Set `METATATE_EXAMPLES_MODE=live`, export `METATATE_MCP_URL` and your access token, then start Jupyter — see [docs/live-mode-saas.md](../docs/live-mode-saas.md).
                """
            ),
            code(SETUP_CELL),
            markdown("## Load Synthetic Tables"),
            code(
                """
                table_dir = repo_root / "sample-data" / "customer-360" / "tables"
                tables = {}
                for path in sorted(table_dir.glob("*.csv")):
                    tables[path.stem] = pd.read_csv(path)
                    print(f"{path.name}: {len(tables[path.stem])} rows")
                """
            ),
            code(
                """
                tables["customers"].head()
                """
            ),
            markdown(
                """
                ## Discover Governed Context

                `discover_context` lists everything the CURRENT publication governs — each asset
                carries its instruction count and the canonical scenario keys it can answer.
                """
            ),
            code(
                """
                discovery = client.discover_context()
                print(f"state: {discovery['state']}")
                print(f"publication: {discovery['publication']['publication_id']}")
                pd.DataFrame(
                    [
                        {
                            "table": entry["ref"]["table"],
                            "column": entry["ref"].get("column"),
                            "instructions": entry["instruction_count"],
                            "scenarios": ", ".join(entry["scenario_keys"]),
                        }
                        for entry in discovery["assets"]
                    ]
                )
                """
            ),
        ]
    )


def cookbook_notebook() -> dict:
    return notebook(
        [
            markdown(
                """
                # 01 - Decision Layer Cookbook

                The core Metatate flow over the typed-answer contract:

                1. discover governed assets
                2. get an asset's decision context and business context
                3. inspect column meaning, classification, and masking facts
                4. read the full rulebook for an asset
                5. authorize a proposed use (allow AND deny)
                6. validate generated SQL before execution
                7. explain a decision by chaining its `decision_id`
                """
            ),
            code(SETUP_CELL),
            markdown("## 1. Discover governed assets"),
            code(
                """
                discovery = client.discover_context()
                pd.DataFrame(
                    [
                        {
                            "table": entry["ref"]["table"],
                            "column": entry["ref"].get("column"),
                            "instructions": entry["instruction_count"],
                        }
                        for entry in discovery["assets"]
                    ]
                )
                """
            ),
            markdown(
                """
                ## 2. Decision context for a table

                Ranked, cited instructions (the winner first) plus the published business
                context. Every row names its policy, scenario, and decision.
                """
            ),
            code(
                """
                context = client.get_decision_context(asset("customers"))
                print(f"state: {context['state']}  effective: {context['effective_decision']}")
                print(json.dumps(context["business_context"], indent=2))
                pd.DataFrame(
                    [
                        {
                            "scenario": d["scenario_key"],
                            "decision": d["decision"],
                            "policy": d["provenance"]["policy_name"],
                            "family": d["instruction_family"],
                        }
                        for d in context["decisions"]
                    ]
                )
                """
            ),
            markdown("## 3. Column meaning facts (classification, PII, masking)"),
            code(
                """
                facts = client.inspect_data_meaning(asset("customers", "email"))
                print(json.dumps(facts, indent=2))
                """
            ),
            markdown(
                """
                ## 4. Read the rulebook before you act

                The tools above answer one question at a time. `inspect_governance_rules`
                returns everything the CURRENT publication has to say about an asset in a
                single call — every active rule with its family, scenario, decision,
                enforcement mode, and provenance. Agents use it as a planning input:
                read the rulebook first, then plan work that will not be blocked later.
                """
            ),
            code(
                """
                rules = client.inspect_governance_rules(asset("customers"))
                print(f"state: {rules['state']}  active rules: {len(rules['rules'])}")
                pd.DataFrame(
                    [
                        {
                            "family": rule["instruction_family"],
                            "scenario": rule["scenario_key"],
                            "decision": rule["decision"],
                            "category": rule["category"],
                            "policy": rule["provenance"]["policy_name"],
                        }
                        for rule in rules["rules"]
                    ]
                )
                """
            ),
            markdown(
                """
                The rulebook carries the full destination-aware transfer matrix, so an
                agent can see that a Salesforce export will be conditional and an
                ads-platform export denied BEFORE attempting either (notebook 03
                exercises those decisions).
                """
            ),
            code(
                """
                transfer = next(
                    rule
                    for rule in rules["rules"]
                    if rule["instruction_family"] == "transfer_governance"
                )
                print(f"transfer decision: {transfer['decision']} ({transfer['scenario_key']})")
                print(json.dumps(transfer["parameters"], indent=2))
                """
            ),
            markdown(
                """
                ## 5. Authorize a proposed use

                Analytics is a permitted use — Metatate can also just say yes.
                Marketing is prohibited: same asset, different scenario, typed deny.
                """
            ),
            code(
                """
                analytics = client.authorize_use(
                    asset("customers"),
                    use="build a churn analytics dashboard",
                    scenario_key="purpose.allowed_use",
                    purpose_key="analytics.reporting",
                )
                print_answer(analytics)
                """
            ),
            code(
                """
                marketing = client.authorize_use(
                    asset("customers"),
                    use="launch a marketing campaign on customer contact data",
                    scenario_key="purpose.prohibited_use",
                )
                print_answer(marketing)
                """
            ),
            markdown("## 6. Validate SQL before execution (intent- and column-aware)"),
            code(
                """
                safe = client.validate_query_context(
                    "SELECT region, SUM(arr) FROM customers GROUP BY region",
                    scenario_key="purpose.allowed_use",
                    default_database="master",
                    default_schema="public",
                    purpose_key="analytics.reporting",
                )
                print(f"aggregate query -> {safe['verdict']}")

                detail = client.validate_query_context(
                    "SELECT customer_name, email FROM customers WHERE region = 'EU'",
                    scenario_key="purpose.allowed_use",
                    default_database="master",
                    default_schema="public",
                )
                print(f"detail query    -> {detail['verdict']} (a masked column is referenced)")
                for finding in detail["findings"]:
                    for instruction in finding["instructions"]:
                        print(f"  {instruction['decision']}: {instruction['decision_reason']}")
                """
            ),
            markdown(
                """
                ## 7. Explain the decision

                Every authorize answer carries the `decision_id` of the winning serving row.
                `explain_why` resolves it server-side and tells you whether that row is still
                in the CURRENT publication.
                """
            ),
            code(
                """
                explanation = client.explain_why(analytics["decision_id"])
                print(f"current: {explanation['current']}")
                print(explanation["explanation"])
                print(json.dumps(explanation["record"]["provenance"], indent=2))
                """
            ),
        ]
    )


def langgraph_notebook() -> dict:
    return notebook(
        [
            markdown(
                """
                # 02 - Governed SQL Agent With LangGraph

                A minimal governed-SQL pattern: every draft query is validated with Metatate,
                and the `verdict` routes the agent — `pass` approves, `warn` revises to a
                minimized query, `fail` blocks. The same routing runs as a real LangGraph
                `StateGraph` in `framework_runtime/langgraph_acceptance.py`.
                """
            ),
            code(SETUP_CELL),
            code(
                """
                SAFE_SQL = "SELECT region, SUM(arr) FROM customers GROUP BY region"

                # B3: the purpose is part of the QUESTION, not a label on it.
                # The aggregate declares `analytics.reporting` and is allowed.
                # The detail and marketing queries are deliberately purpose-blind,
                # so they demonstrate the fail-closed answer instead of an allow.
                PURPOSE_BY_SQL = {SAFE_SQL: "analytics.reporting"}

                def governed_sql(sql, scenario_key):
                    answer = client.validate_query_context(
                        sql,
                        scenario_key=scenario_key,
                        default_database="master",
                        default_schema="public",
                        purpose_key=PURPOSE_BY_SQL.get(sql),
                    )
                    verdict = answer["verdict"]
                    if verdict == "fail":
                        return {"verdict": verdict, "final_sql": None, "route": "block"}
                    if verdict == "warn":
                        return {"verdict": verdict, "final_sql": SAFE_SQL, "route": "revise"}
                    return {"verdict": verdict, "final_sql": sql, "route": "approve"}
                """
            ),
            code(
                """
                runs = {
                    "safe": governed_sql(SAFE_SQL, "purpose.allowed_use"),
                    "unsafe": governed_sql(
                        "SELECT customer_name, email FROM customers WHERE region = 'EU'",
                        "purpose.allowed_use",
                    ),
                    "blocked": governed_sql(
                        "SELECT customer_name, email FROM customers WHERE marketing_consent = 'opted_in'",
                        "purpose.prohibited_use",
                    ),
                }
                for name, run in runs.items():
                    print(f"{name}: {run['route']} ({run['verdict']}) -> {run['final_sql']}")
                """
            ),
            markdown(
                """
                The deterministic runtime proof (a real `StateGraph` with approve/revise/block
                routing) lives in `framework_runtime/` and runs in CI — see
                `docs/framework-runtime-acceptance.md`.
                """
            ),
        ]
    )


def transfer_notebook() -> dict:
    return notebook(
        [
            markdown(
                """
                # 03 - Transfer Governance Before Export

                Destination-aware authorization: the SAME asset and operation produce different
                typed answers per destination and consumer jurisdiction, because the server
                evaluates the authored transfer rules at read time.
                """
            ),
            code(SETUP_CELL),
            markdown("## Salesforce (US) for EU consumers → conditional, with typed conditions"),
            code(
                """
                salesforce = client.authorize_use(
                    asset("customers"),
                    use="sync approved customer fields to the CRM",
                    scenario_key="residency.cross_border_transfer",
                    operation="export",
                    destination={"system": "SALESFORCE", "jurisdiction": "US"},
                    consumer_jurisdiction="EU",
                )
                print_answer(salesforce)
                """
            ),
            markdown("## Advertising platform → deny · External LLM vendor → deny"),
            code(
                """
                ads = client.authorize_use(
                    asset("customers"),
                    use="send the customer batch to the advertising platform",
                    scenario_key="residency.cross_border_transfer",
                    operation="export",
                    destination={"system": "ADS_PLATFORM", "jurisdiction": "US"},
                    consumer_jurisdiction="US",
                )
                llm = client.authorize_use(
                    asset("customers"),
                    use="send the customer batch to an external LLM vendor",
                    scenario_key="residency.cross_border_transfer",
                    operation="export",
                    destination={"system": "EXTERNAL_LLM_VENDOR", "jurisdiction": "US"},
                    consumer_jurisdiction="US",
                )
                print(f"ADS_PLATFORM        -> {ads['decision']}")
                print(f"EXTERNAL_LLM_VENDOR -> {llm['decision']}")
                """
            ),
            markdown(
                """
                ## An unmatched destination falls back to the authored default

                No rule names `INTERNAL_WAREHOUSE`, so the policy's `defaultEffect`
                (conditional) answers — nothing is silently allowed.
                """
            ),
            code(
                """
                unmatched = client.authorize_use(
                    asset("customer_exports"),
                    use="stage the export batch in the internal warehouse",
                    scenario_key="residency.cross_border_transfer",
                    operation="export",
                    destination={"system": "INTERNAL_WAREHOUSE", "jurisdiction": "US"},
                    consumer_jurisdiction="US",
                )
                print_answer(unmatched)
                """
            ),
            markdown("## Chain the conditional decision into `explain_why`"),
            code(
                """
                explanation = client.explain_why(salesforce["decision_id"])
                print(f"current: {explanation['current']}")
                print(explanation["explanation"])
                """
            ),
        ]
    )


def governed_text_to_sql_notebook() -> dict:
    return notebook(
        [
            markdown(
                """
                # 04 - Governed Text-to-SQL Agent

                A deterministic text-to-SQL planner whose EVERY draft is validated before it is
                returned: `pass` ships, `warn` is revised to a minimized aggregate, `fail` is
                refused with the policy reason.
                """
            ),
            code(SETUP_CELL),
            code(
                """
                SAFE_SQL = "SELECT region, SUM(arr) FROM customers GROUP BY region"

                # B3: the purpose is part of the QUESTION, not a label on it.
                # The aggregate declares `analytics.reporting` and is allowed.
                # The detail and marketing queries are deliberately purpose-blind,
                # so they demonstrate the fail-closed answer instead of an allow.
                PURPOSE_BY_SQL = {SAFE_SQL: "analytics.reporting"}

                def plan(question):
                    q = question.lower()
                    if "marketing" in q or "campaign" in q:
                        return (
                            "SELECT customer_name, email FROM customers WHERE marketing_consent = 'opted_in'",
                            "purpose.prohibited_use",
                        )
                    if "email" in q or "identify" in q:
                        return (
                            "SELECT customer_name, email FROM customers WHERE region = 'EU'",
                            "purpose.allowed_use",
                        )
                    return (SAFE_SQL, "purpose.allowed_use")

                def text_to_sql(question):
                    sql, scenario_key = plan(question)
                    answer = client.validate_query_context(
                        sql,
                        scenario_key=scenario_key,
                        default_database="master",
                        default_schema="public",
                        purpose_key=PURPOSE_BY_SQL.get(sql),
                    )
                    verdict = answer["verdict"]
                    if verdict == "fail":
                        return {"question": question, "verdict": verdict, "sql": None}
                    if verdict == "warn":
                        return {"question": question, "verdict": verdict, "sql": SAFE_SQL}
                    return {"question": question, "verdict": verdict, "sql": sql}
                """
            ),
            code(
                """
                for question in [
                    "How does ARR break down by region?",
                    "List EU customers with their email addresses.",
                    "Build an email list for the marketing campaign.",
                ]:
                    result = text_to_sql(question)
                    print(f"{result['question']}")
                    print(f"  verdict: {result['verdict']}  sql: {result['sql']}")
                """
            ),
        ]
    )


def red_team_notebook() -> dict:
    return notebook(
        [
            markdown(
                """
                # 05 - Agent Red-Team Evaluation Harness

                Repeatable risky-prompt checks: each case states the governed question AND the
                typed answer it must produce. The same matrix lives in the estate spec
                (`sample-data/customer-360/expected-decisions.yaml`) and is asserted against the
                engine-derived state in the product's test suite.
                """
            ),
            code(SETUP_CELL),
            code(
                """
                CASES = [
                    {
                        "name": "marketing exfil",
                        "call": lambda: client.authorize_use(
                            asset("customers"),
                            use="launch a marketing campaign on customer contact data",
                            scenario_key="purpose.prohibited_use",
                        ),
                        "expect": "deny",
                    },
                    {
                        "name": "ticket fine-tune",
                        "call": lambda: client.authorize_use(
                            asset("support_tickets"),
                            use="fine-tune a support assistant on ticket text",
                            scenario_key="ai.training",
                        ),
                        "expect": "deny",
                    },
                    {
                        "name": "LLM vendor export",
                        "call": lambda: client.authorize_use(
                            asset("customers"),
                            use="send the customer batch to an external LLM vendor",
                            scenario_key="residency.cross_border_transfer",
                            operation="export",
                            destination={"system": "EXTERNAL_LLM_VENDOR", "jurisdiction": "US"},
                            consumer_jurisdiction="US",
                        ),
                        "expect": "deny",
                    },
                    {
                        "name": "safe control (analytics)",
                        "call": lambda: client.authorize_use(
                            asset("customers"),
                            use="build a churn analytics dashboard",
                            scenario_key="purpose.allowed_use",
                            purpose_key="analytics.reporting",
                        ),
                        "expect": "allow",
                    },
                ]
                """
            ),
            code(
                """
                failures = []
                for case in CASES:
                    answer = case["call"]()
                    got = answer_label(answer)
                    ok = got == case["expect"]
                    print(f"{'PASS' if ok else 'FAIL'} {case['name']}: expected {case['expect']}, got {got}")
                    if not ok:
                        failures.append(case["name"])
                assert not failures, failures
                print("\\nAll red-team expectations hold.")
                """
            ),
        ]
    )


def ci_gate_notebook() -> dict:
    return notebook(
        [
            markdown(
                """
                # 06 - CI Gate For Data And AI Changes

                The reusable `cicd_policy_gate` package maps a pull request's change set
                (SQL models, export jobs, AI workflows — each carrying a canonical
                `scenario_key`) onto validate/authorize calls and turns the typed answers into
                pass / needs_controls / fail gates with reviewable reason codes.
                """
            ),
            code(SETUP_CELL),
            code(
                """
                from cicd_policy_gate.gate import evaluate_changes, load_changes

                change_set = load_changes()
                summary = evaluate_changes(client, change_set, strict=True)
                print(f"pass={summary.passed} needs_controls={summary.needs_controls} fail={summary.failed}")
                print(f"release_allowed: {summary.release_allowed}")
                """
            ),
            code(
                """
                for result in summary.results:
                    print(f"{result.change_id}: {result.gate} ({result.decision})")
                    if result.reason_codes:
                        print(f"  reason_codes: {', '.join(result.reason_codes)}")
                    if result.required_controls:
                        print(f"  controls: {'; '.join(result.required_controls)}")
                """
            ),
            markdown(
                """
                In CI, run `scripts/run_cicd_policy_gate.sh --strict` — the exit code blocks the
                merge when denied changes are present. See `docs/ci-cd-policy-gate.md` for the
                GitHub Actions shape.
                """
            ),
        ]
    )


def governed_rag_ingestion_gate_notebook() -> dict:
    return notebook(
        [
            markdown(
                """
                # 07 - Governed RAG And Embedding Ingestion Gate

                Before data enters a RAG index or an embedding store, ask Metatate. Training on
                ticket text is a typed deny; LLM inference over customer data is permitted —
                the gate keeps the corpus honest either way.
                """
            ),
            code(SETUP_CELL),
            code(
                """
                candidates = [
                    {
                        "corpus": "support ticket bodies (fine-tune)",
                        "answer": client.authorize_use(
                            asset("support_tickets"),
                            use="fine-tune a support assistant on ticket text",
                            scenario_key="ai.training",
                        ),
                    },
                    {
                        "corpus": "customer account summaries (LLM inference)",
                        "answer": client.authorize_use(
                            asset("customers"),
                            use="summarize customer accounts with an LLM",
                            scenario_key="ai.inference",
                        ),
                    },
                ]
                for candidate in candidates:
                    answer = candidate["answer"]
                    label = answer_label(answer)
                    action = "INGEST" if label == "allow" else "SKIP"
                    print(f"{action} {candidate['corpus']} -> {label}")
                    if answer.get("reason"):
                        print(f"  {answer['reason']}")
                """
            ),
            markdown("## Validate the retrieval query that will feed the index"),
            code(
                """
                retrieval_sql = client.validate_query_context(
                    "SELECT region, SUM(arr) FROM customers GROUP BY region",
                    scenario_key="purpose.allowed_use",
                    default_database="master",
                    default_schema="public",
                    purpose_key="analytics.reporting",
                )
                print(f"retrieval query verdict: {retrieval_sql['verdict']}")
                """
            ),
        ]
    )


def openai_agents_tool_guard_notebook() -> dict:
    return notebook(
        [
            markdown(
                """
                # 08 - OpenAI Agents SDK Tool Guard Pattern

                A deterministic tool-guard: the agent's data tool calls Metatate FIRST and only
                executes when the typed answer allows it. The real `FunctionTool` runtime proof
                (no LLM) is `framework_runtime/openai_agents_acceptance.py`.
                """
            ),
            code(SETUP_CELL),
            code(
                """
                def guarded_customer_tool(use, scenario_key):
                    answer = client.authorize_use(asset("customers"), use=use, scenario_key=scenario_key)
                    if answer_label(answer) != "allow":
                        return {
                            "executed": False,
                            "decision": answer_label(answer),
                            "reason": answer.get("reason"),
                        }
                    return {"executed": True, "decision": "allow", "evidence": answer["decision_id"]}
                """
            ),
            code(
                """
                print(guarded_customer_tool("build a churn analytics dashboard", "purpose.allowed_use"))
                print(guarded_customer_tool(
                    "launch a marketing campaign on customer contact data", "purpose.prohibited_use"
                ))
                """
            ),
        ]
    )


def approval_workflow_notebook() -> dict:
    return notebook(
        [
            markdown(
                """
                # 09 - Human Approval Packet For Conditional Export

                Typed decisions drive an operational review loop: `pass`/`allow` proceeds,
                `conditional` generates an exception packet whose attestations come from the
                answer's structured conditions, `deny`/`fail` stays blocked — never an informal
                override.
                """
            ),
            code(SETUP_CELL),
            code(
                """
                from human_exception_workflow.workflow import run_workflow, print_summary

                run = run_workflow(client)
                print_summary(run)
                """
            ),
            code(
                """
                conditional = next(item for item in run.items if item.request_id == "req-002")
                print(json.dumps(conditional.packet, indent=2))
                """
            ),
            markdown(
                """
                The reviewer approves with the required attestations
                (`approval_recorded`, `anonymization_before_transfer` — derived from the
                answer's `approval_required` and `anonymize_first` conditions), and only then
                does the workflow resume, pinned to the reviewed destination.
                """
            ),
        ]
    )


def llamaindex_retrieval_notebook() -> dict:
    return notebook(
        [
            markdown(
                """
                # 10 - LlamaIndex Governed Retrieval Pattern

                A retrieval function that is governance-aware end to end: the planner maps a
                question to SQL + a canonical scenario, Metatate validates it, and only a
                `pass`/revised query reaches the retriever. Wrap `governed_retrieval` as a
                LlamaIndex `FunctionTool` and the framework routes through the same gate
                (`framework_runtime/llamaindex_acceptance.py` proves it).
                """
            ),
            code(SETUP_CELL),
            code(
                """
                SAFE_SQL = "SELECT region, SUM(arr) FROM customers GROUP BY region"

                # B3: the purpose is part of the QUESTION, not a label on it.
                # The aggregate declares `analytics.reporting` and is allowed.
                # The detail and marketing queries are deliberately purpose-blind,
                # so they demonstrate the fail-closed answer instead of an allow.
                PURPOSE_BY_SQL = {SAFE_SQL: "analytics.reporting"}

                def plan_retrieval(question):
                    q = question.lower()
                    if "marketing" in q:
                        return (
                            "SELECT customer_name, email FROM customers WHERE marketing_consent = 'opted_in'",
                            "purpose.prohibited_use",
                        )
                    if "email" in q:
                        return (
                            "SELECT customer_name, email FROM customers WHERE region = 'EU'",
                            "purpose.allowed_use",
                        )
                    return (SAFE_SQL, "purpose.allowed_use")

                def governed_retrieval(question):
                    sql, scenario_key = plan_retrieval(question)
                    answer = client.validate_query_context(
                        sql,
                        scenario_key=scenario_key,
                        default_database="master",
                        default_schema="public",
                        purpose_key=PURPOSE_BY_SQL.get(sql),
                    )
                    if answer["verdict"] == "fail":
                        return {"question": question, "retrieved": None, "verdict": "fail"}
                    final_sql = sql if answer["verdict"] == "pass" else SAFE_SQL
                    return {"question": question, "retrieved": final_sql, "verdict": answer["verdict"]}
                """
            ),
            code(
                """
                for question in [
                    "What is ARR by region?",
                    "Show EU customers and their email addresses.",
                    "Pull the marketing outreach list.",
                ]:
                    print(governed_retrieval(question))
                """
            ),
        ]
    )


def langgraph_governed_sql_agent_runtime_notebook() -> dict:
    return notebook(
        [
            markdown(
                """
                # 11 - LangGraph Governed SQL Agent Runtime

                The REAL LangGraph runtime: a multi-node `StateGraph` plans SQL, validates it
                with Metatate, and conditionally routes to approve / revise / block on the typed
                verdict. Requires `requirements-framework.txt` (Python 3.10+).
                """
            ),
            code(SETUP_CELL),
            code(
                """
                from framework_runtime.langgraph_governed_sql_agent import (
                    build_governed_sql_agent,
                    summarize_state,
                )
                from framework_runtime.scenarios import RecordingMetatateClient

                recording = RecordingMetatateClient(client)
                agent = build_governed_sql_agent(recording)
                """
            ),
            code(
                """
                for question in [
                    "How does ARR break down by region?",
                    "List EU customers with their email addresses.",
                    "Build an email list for the marketing campaign.",
                ]:
                    state = agent.invoke({"question": question})
                    summary = summarize_state(state)
                    print(f"{question}")
                    print(f"  route: {summary['route']} ({summary['decision']})")
                    print(f"  final_sql: {summary['final_sql']}")
                print(f"Metatate calls made by the graph: {len(recording.calls)}")
                """
            ),
        ]
    )


def governance_states_notebook() -> dict:
    return notebook(
        [
            markdown(
                """
                # 12 - Governance States And The Wider Estate

                Metatate's typed answers are honest about uncertainty, and the estate is big
                enough to prove it: a deliberately UNGOVERNED legacy table, a monitored custom
                masking routine served as review-required, role-gated HR data, PCI-scope
                payment instruments, AI-lifecycle rules on an ML feature store,
                taxonomy-targeted masking that follows the classification — not a column
                list — plus a deliberately CONFLICTED policy pair, the retain/conditional/
                log_only decision vocabulary, the free-text scenario front door, and a
                second governed schema.
                """
            ),
            code(SETUP_CELL),
            markdown(
                """
                ## 1. The honest states

                An ungoverned asset is a typed `not_enough_published_state` — never an empty
                pass. A custom masking routine the engine cannot map deterministically is a
                typed `review_required` — a human must decide.
                """
            ),
            code(
                """
                ungoverned = client.authorize_use(
                    asset("legacy_customer_backup"),
                    use="report on the legacy customer backup",
                    scenario_key="purpose.allowed_use",
                )
                print(f"legacy_customer_backup -> {ungoverned['state']} ({ungoverned.get('reason_code')})")
                for action in ungoverned.get("next_actions") or []:
                    print(f"  next: {action}")
                """
            ),
            code(
                """
                review = client.authorize_use(
                    asset("employees", "full_name"),
                    use="display employee names in the people directory",
                    scenario_key="masking.display",
                )
                print(f"employees.full_name masking -> {review['state']} ({review.get('reason_code')})")
                """
            ),
            markdown(
                """
                ## 2. Role-gated access and public-sharing prohibitions

                `access.read` on employee records cites BOTH role rules — the deny wins, and
                the allow for people-ops roles is right there in the citations.
                """
            ),
            code(
                """
                hr_read = client.authorize_use(
                    asset("employees"),
                    use="browse employee records",
                    scenario_key="access.read",
                )
                print_answer(hr_read)
                for instruction in hr_read["instructions"]:
                    print(f"  cited: {instruction['instruction_key']} -> {instruction['decision']}")
                """
            ),
            code(
                """
                sharing = client.authorize_use(
                    asset("employees"),
                    use="publish the org chart externally",
                    scenario_key="sharing.public",
                )
                print(f"sharing.public -> {sharing['decision']}")
                """
            ),
            markdown(
                """
                ## 3. The AI lifecycle, scenario by scenario

                Training on RAW ticket text is denied — but training on DERIVED features is
                allowed. Retrieval context and embedding storage are permitted; vendor
                transfer and fully automated decisioning are not.
                """
            ),
            code(
                """
                lifecycle = [
                    ("raw tickets, ai.training", client.authorize_use(
                        asset("support_tickets"),
                        use="fine-tune a support assistant on ticket text",
                        scenario_key="ai.training",
                    )),
                    ("features, ai.training", client.authorize_use(
                        asset("ml_feature_store"),
                        use="train the churn model on derived features",
                        scenario_key="ai.training",
                    )),
                    ("features, ai.retrieval_context", client.authorize_use(
                        asset("ml_feature_store"),
                        use="feed churn features into agent retrieval context",
                        scenario_key="ai.retrieval_context",
                        purpose_key="ai.inference",
                    )),
                    ("features, ai.embedding_storage", client.authorize_use(
                        asset("ml_feature_store"),
                        use="index feature vectors in the embedding store",
                        scenario_key="ai.embedding_storage",
                        purpose_key="ai.inference",
                    )),
                    ("features, ai.vendor_transfer", client.authorize_use(
                        asset("ml_feature_store"),
                        use="share churn features with an external AI vendor",
                        scenario_key="ai.vendor_transfer",
                    )),
                    ("features, ai.automated_decisioning", client.authorize_use(
                        asset("ml_feature_store"),
                        use="auto-cancel accounts from churn scores",
                        scenario_key="ai.automated_decisioning",
                    )),
                ]
                for name, answer in lifecycle:
                    print(f"{name:40s} -> {answer_label(answer)}")
                """
            ),
            markdown(
                """
                Look at the two `ai.inference` rows. **Same asset, same declared
                purpose, opposite answers.**

                `ai.retrieval_context` is allowed because its policy's permitted
                use was canonicalized to the registry key `ai.inference` — the
                declared purpose matches a permitted use.

                `ai.embedding_storage` reviews, *even though the call declares the
                same valid purpose*, because that policy's authored entry says
                feature vectors may be **STORED** — which never established
                inference use. An unmapped legacy entry cannot prove coverage, and
                declaring a good purpose does not rescue it.

                That is the whole boundary in two lines: the purpose you state has
                to meet a permitted use the policy actually expressed.
                """
            ),
            markdown(
                """
                ## 4. Taxonomy-targeted masking: classify once, govern everywhere

                One policy targets the taxonomy type `pii.contact.email` — no column lists.
                The engine resolved it to every column the catalog classifies as an email,
                including the HR table nobody edited the policy for.
                """
            ),
            code(
                """
                work_email = client.validate_query_context(
                    "SELECT work_email FROM employees",
                    scenario_key="purpose.allowed_use",
                    default_database="master",
                    default_schema="public",
                )
                print(f"SELECT work_email -> {work_email['verdict']}")
                for finding in work_email["findings"]:
                    for instruction in finding["instructions"]:
                        paths = ",".join(p["source"] for p in instruction.get("resolution_paths") or [])
                        print(f"  {instruction['decision']} via [{paths}] {instruction.get('decision_reason')}")
                """
            ),
            markdown(
                """
                ## 5. Collections: govern the named set, not a table list

                The "Customer 360" COLLECTION groups five tables; one policy targets the
                collection by id. The answer's citations carry a `collection` resolution
                path — add a table to the collection and the policy follows it.
                """
            ),
            code(
                """
                sharing = client.authorize_use(
                    asset("subscriptions"),
                    use="share account health summaries with the success team",
                    scenario_key="sharing.internal",
                    purpose_key="analytics.reporting",
                )
                print(f"sharing.internal on subscriptions -> {sharing['decision']}")
                for instruction in sharing["instructions"]:
                    paths = ",".join(p["source"] for p in instruction.get("resolution_paths") or [])
                    print(f"  cited via [{paths}]: {instruction['provenance']['policy_name']}")
                """
            ),
            markdown("## 6. PCI-scope payment data and intent-less reads"),
            code(
                """
                card = client.validate_query_context(
                    "SELECT card_last4 FROM payment_methods",
                    scenario_key="purpose.allowed_use",
                    default_database="master",
                    default_schema="public",
                )
                print(f"card_last4 (analytics intent) -> {card['verdict']} (tokenized column referenced)")

                salary = client.validate_query_context(
                    "SELECT salary FROM employees",
                    default_database="master",
                    default_schema="public",
                )
                print(f"salary (NO stated intent)    -> {salary['verdict']} (role-gated read applies to any SQL)")
                """
            ),
            markdown(
                """
                ## 7. Governance debt is a typed state, not a coin flip

                Two policies deliberately disagree about outreach on
                `marketing_prospects`: Growth Marketing permits the exact use the
                Privacy Office prohibits, at the same priority, on the same scenario.
                The engine refuses to pick a side — the answer is a typed
                `review_required(conflicted_published_state)` citing BOTH sources.
                """
            ),
            code(
                """
                conflict = client.authorize_use(
                    asset("marketing_prospects"),
                    use="run outreach against the prospect list",
                    scenario_key="purpose.allowed_use",
                )
                print(f"marketing_prospects outreach -> {conflict['state']} ({conflict.get('reason_code')})")
                for source in (conflict.get("conflict") or {}).get("sources") or []:
                    print(f"  cited: {source['provenance']['policy_name']} -> {source['decision']}")
                """
            ),
            markdown(
                """
                ## 8. The rest of the decision vocabulary

                Not every answer is allow/deny. Retention serves an honest `retain`
                (with a structured obligation), row-level access serves `conditional`
                with a `role_restricted` condition, compliance context serves
                `log_only`, and an enforced PCI mask serves `mask_full` with a `mask`
                obligation naming the method.
                """
            ),
            code(
                """
                retention = client.authorize_use(
                    asset("subscriptions"),
                    use="confirm how long subscription revenue facts must be kept",
                    scenario_key="retention.lifecycle",
                )
                print_answer(retention)
                """
            ),
            code(
                """
                rows = client.authorize_use(
                    asset("employees"),
                    use="read employee rows for my region",
                    scenario_key="access.row_filter",
                )
                print_answer(rows)
                """
            ),
            code(
                """
                gdpr = client.authorize_use(
                    asset("employees"),
                    use="review the GDPR context for employee records",
                    scenario_key="compliance.regulatory",
                )
                print(f"compliance.regulatory -> {gdpr['decision']} (regulatory context, not a permission)")

                pci = client.authorize_use(
                    asset("payment_methods", "card_token"),
                    use="display stored payment instruments in the support console",
                    scenario_key="masking.display",
                )
                print_answer(pci)
                """
            ),
            markdown(
                """
                ## 9. The free-text front door

                No `scenario_key` at all: the server maps the plain-English use to a
                canonical scenario deterministically — and when the text is ambiguous,
                it refuses to guess with a typed `scenario_unresolved`.
                """
            ),
            code(
                """
                mapped = client.authorize_use(
                    asset("support_tickets"),
                    use="fine-tune a model on this data",
                )
                print(f"free text, no scenario_key -> {mapped['state']} / {mapped.get('decision')} (mapped to {mapped.get('scenario_key')})")

                ambiguous = client.authorize_use(
                    asset("customers"),
                    use="compare ai.training and ai.inference guidance for customer data",
                )
                print(f"ambiguous free text        -> {ambiguous['state']} ({ambiguous.get('reason_code')})")
                """
            ),
            markdown(
                """
                ## 10. A second schema, same decision layer

                The estate spans two schemas: `finance.invoices` and
                `finance.revenue_ledger` are governed by their own guardrail policy —
                schema-qualified assets answer exactly like `public` ones.
                """
            ),
            code(
                """
                ledger = client.authorize_use(
                    asset("revenue_ledger", schema="finance"),
                    use="publish ledger extracts on the public status page",
                    scenario_key="sharing.public",
                )
                print(f"finance.revenue_ledger public sharing -> {ledger['decision']}")
                """
            ),
            code(
                """
                invoices = client.authorize_use(
                    asset("invoices", schema="finance"),
                    use="prepare the quarterly revenue recognition report",
                    scenario_key="purpose.allowed_use",
                    purpose_key="compliance.reporting",
                )
                print(f"finance.invoices reporting            -> {invoices['decision']}")
                """
            ),
        ]
    )


def sql_gauntlet_notebook() -> dict:
    return notebook(
        [
            markdown(
                """
                # 13 - The SQL Gauntlet: Intent- And Column-Aware Validation

                `validate_query_context` does not grade SQL on vibes. Participation is
                precise: COLUMN rows join the verdict only when the column is actually
                referenced (or a star pulls everything), TABLE rows only when the
                stated intent matches their scenario, and always-applicable read
                controls apply to any SQL. This notebook runs real query shapes
                through that model — JOINs, `SELECT *`, CTEs, a join into an
                ungoverned table, byte-identical SQL under two intents, and a
                cross-schema join.
                """
            ),
            code(SETUP_CELL),
            markdown(
                """
                ## 1. A JOIN is evaluated per referenced table

                Both sides of the join get their own finding; the verdict aggregates
                over every participating row.
                """
            ),
            code(
                """
                joined = client.validate_query_context(
                    "SELECT c.region, SUM(s.arr) FROM customers c JOIN subscriptions s ON s.customer_id = c.customer_id GROUP BY c.region",
                    scenario_key="purpose.allowed_use",
                    default_database="master",
                    default_schema="public",
                    purpose_key="analytics.reporting",
                )
                print(f"customers JOIN subscriptions -> {joined['verdict']}")
                for finding in joined["findings"]:
                    print(f"  {finding['ref']['table']}: {finding['status']} ({finding.get('decision')})")
                """
            ),
            markdown(
                """
                ## 2. `SELECT *` pulls every masked column into the verdict

                The star is a projection signal: it makes ALL column rows participate.
                Name only the columns you need and the same table can pass clean.
                """
            ),
            code(
                """
                star = client.validate_query_context(
                    "SELECT * FROM payment_methods LIMIT 5",
                    scenario_key="purpose.allowed_use",
                    default_database="master",
                    default_schema="public",
                )
                print(f"SELECT *                    -> {star['verdict']} (both tokenized card columns participate)")

                narrow = client.validate_query_context(
                    "SELECT payment_method_id FROM payment_methods",
                    scenario_key="purpose.allowed_use",
                    default_database="master",
                    default_schema="public",
                )
                print(f"SELECT payment_method_id    -> {narrow['verdict']} (no masked column referenced)")
                """
            ),
            markdown(
                """
                ## 3. CTE names are not tables

                `recent` is a WITH-alias — the parser excludes it, so the only
                finding is the real `subscriptions` reference.
                """
            ),
            code(
                """
                cte = client.validate_query_context(
                    "WITH recent AS (SELECT customer_id, arr FROM subscriptions WHERE end_date IS NULL) SELECT customer_id, SUM(arr) FROM recent GROUP BY customer_id",
                    scenario_key="purpose.allowed_use",
                    default_database="master",
                    default_schema="public",
                    purpose_key="analytics.reporting",
                )
                print(f"CTE aggregate -> {cte['verdict']}")
                print(f"findings: {[finding['ref']['table'] for finding in cte['findings']]}")
                """
            ),
            markdown(
                """
                ## 4. Joining an ungoverned table is called out, per ref

                `legacy_customer_backup` is cataloged but ungoverned. The join still
                gets an overall verdict — with an explicit per-ref
                `not_enough_published_state` finding instead of a silent pass.
                """
            ),
            code(
                """
                legacy = client.validate_query_context(
                    "SELECT c.customer_name, l.exported_at FROM customers c JOIN legacy_customer_backup l ON l.customer_id = c.customer_id",
                    scenario_key="purpose.allowed_use",
                    default_database="master",
                    default_schema="public",
                    purpose_key="analytics.reporting",
                )
                print(f"governed JOIN ungoverned -> {legacy['verdict']}")
                for finding in legacy["findings"]:
                    print(f"  {finding['ref']['table']}: {finding['status']} ({finding.get('reason_code')})")
                """
            ),
            markdown(
                """
                ## 5. The intent flip: same SQL, opposite verdicts

                Byte-identical SQL. Under an analytics intent the permitted-use row
                participates and the query passes; under a marketing intent the
                prohibited-use deny participates and the same query fails. Intent is
                part of the question — not an afterthought.
                """
            ),
            code(
                """
                analytics = client.validate_query_context(
                    "SELECT region, COUNT(*) FROM customers GROUP BY region",
                    scenario_key="purpose.allowed_use",
                    default_database="master",
                    default_schema="public",
                    purpose_key="analytics.reporting",
                )
                marketing = client.validate_query_context(
                    "SELECT region, COUNT(*) FROM customers GROUP BY region",
                    scenario_key="purpose.prohibited_use",
                    default_database="master",
                    default_schema="public",
                )
                print(f"analytics intent -> {analytics['verdict']}")
                print(f"marketing intent -> {marketing['verdict']} (same SQL, different question)")
                """
            ),
            markdown(
                """
                ## 6. Cross-schema joins resolve like anything else

                Two-part names qualify against the default database — the `finance`
                schema's guardrails answer for their own tables. The finance policy
                grants `compliance.reporting` and `compliance.audit`, so the call
                declares the purpose it is actually pursuing.
                """
            ),
            code(
                """
                finance = client.validate_query_context(
                    "SELECT i.invoice_id, r.amount FROM finance.invoices i JOIN finance.revenue_ledger r ON r.invoice_id = i.invoice_id",
                    scenario_key="purpose.allowed_use",
                    default_database="master",
                    default_schema="public",
                    purpose_key="compliance.reporting",
                )
                print(f"finance.invoices JOIN finance.revenue_ledger -> {finance['verdict']}")
                for finding in finance["findings"]:
                    print(f"  {finding['ref']['schema']}.{finding['ref']['table']}: {finding.get('decision')}")
                """
            ),
        ]
    )


def governed_agent_arc_notebook() -> dict:
    return notebook(
        [
            markdown(
                """
                # 14 - The Governed Agent, End To End

                Every other notebook proves one decision at a time. This one gives a
                LangGraph agent a realistic multi-part brief and lets governance
                visibly change its course:

                > *"Build the EU churn dashboard, push the at-risk segment to
                > Salesforce, and fine-tune the support assistant on ticket text."*

                The agent reads the rulebook first, self-revises warned SQL, turns a
                conditional export into a human exception packet and resumes with
                attested controls, REROUTES a denied fine-tune to the governed
                alternative, and closes by chaining `explain_why` over every decision
                id it collected. Offline it replays recorded answers with a
                deterministic planner; in live mode an optional LLM drafts the SQL
                (`METATATE_EXAMPLES_LLM`) while governance calls stay identical.

                Requires `requirements-framework.txt` (LangGraph), like notebook 11.
                """
            ),
            code(SETUP_CELL),
            markdown("## Run the whole arc"),
            code(
                """
                from governed_agent_arc import ArcRecordingClient, ScriptedPlanner, run_arc

                recording = ArcRecordingClient(client)
                report = run_arc(recording, ScriptedPlanner())
                for line in report.transcript:
                    print(line)
                """
            ),
            markdown(
                """
                ## The decision spine

                Eleven Metatate calls, in order — the agent's entire interaction with
                governance, every one a typed answer:
                """
            ),
            code(
                """
                for step, call in enumerate(report.decision_sequence, start=1):
                    print(f"{step:>2}. {call['tool']:<24} -> {call['label']}")
                """
            ),
            markdown(
                """
                ## Beat 1: the draft that had to change

                The first draft referenced a masked column — `warn`, not a guess. The
                agent revised once and re-validated to `pass`. It never returns SQL
                Metatate has not passed.
                """
            ),
            code(
                """
                print(f"draft:   {report.draft_sql}")
                print(f"final:   {report.final_sql}")
                print(f"revisions: {report.revision_count} (dashboard {report.dashboard_status})")
                """
            ),
            markdown(
                """
                ## Beat 2: the conditional export became a review, then a resume

                `conditional` is not a soft yes — the agent built an exception packet
                (the same `human_exception_workflow` machinery from notebook 09) and
                resumed only after the reviewer attested BOTH required controls.
                """
            ),
            code(
                """
                packet = report.exception_packet
                print(f"packet:  {packet['packet_id']} -> queue {packet['reviewer_queue']}")
                print(f"attestations required: {packet['required_attestations']}")
                print(f"status:  {report.export_status}")
                print(f"resume:  {report.resume_payload['action']}")
                """
            ),
            markdown(
                """
                ## Beat 3: deny became redirection, not a dead end

                Fine-tuning on raw ticket text is denied. The rulebook already showed
                where training IS allowed — the agent re-asked on the feature store
                and got a real `allow`, with its own decision id.
                """
            ),
            code(
                """
                print(f"training: {report.training_status} (rerouted: {report.rerouted})")
                """
            ),
            markdown(
                """
                ## Beat 4: the receipts

                Every decision the agent collected resolves through `explain_why`,
                and every one is still current in the live publication.
                """
            ),
            code(
                """
                for explanation in report.explanations:
                    print(f"{explanation['decision_id']} -> current: {explanation['current']}")
                print(f"total Metatate calls: {report.metatate_calls}")
                """
            ),
        ]
    )


def audit_evidence_notebook() -> dict:
    return notebook(
        [
            markdown(
                """
                # 15 - The Audit Evidence Packet

                "Advisory" does not mean unaccountable. Decision answers cite serving
                `decision_id` values, while authorization and validation evaluations
                mint durable `authorization_id` and `validation_id` receipts. This
                notebook turns a day of governed questions into a single audit-ready
                report with publication provenance, policy versions, explain chains,
                and the honest corners where the estate refused to guess. In the app,
                **Activity → Audit trail** shows the governance receipts; **MCP Tools →
                Tokens → View requests** is the separate transport request log.
                """
            ),
            code(SETUP_CELL),
            markdown("## A day of governed questions"),
            code(
                """
                from audit_evidence import collect_evidence, render_markdown

                packet = collect_evidence(client)
                print(f"decisions: {packet.total}")
                print(f"explained and current: {packet.current}/{packet.explained}")
                print(f"honest corners: {packet.honest_corners}")
                print(f"publication: {packet.publication_id}")
                """
            ),
            markdown(
                """
                ## The packet, audit-ready

                Per decision: asset, scenario, typed decision, the citing policy BY
                NAME AND VERSION, evidence id, conditions and obligations — and the
                explain-chain confirmation. Then the corners: the ungoverned legacy
                table and the monitored custom mask, on the record instead of hidden.
                """
            ),
            code(
                """
                print(render_markdown(packet))
                """
            ),
            markdown(
                """
                ## Three explanation references, three distinct records

                `decision_id` cites a serving-row decision. `authorization_id`
                and `validation_id` cite the two durable evaluation ledgers.
                They are all explainable, but they are not interchangeable.
                """
            ),
            code(
                """
                analytics = client.authorize_use(
                    {"database": "master", "schema": "public", "table": "customers"},
                    use="build a churn analytics dashboard",
                    scenario_key="purpose.allowed_use",
                    purpose_key="analytics.reporting",
                )
                safe_query = client.validate_query_context(
                    "SELECT region, SUM(arr) FROM customers GROUP BY region",
                    scenario_key="purpose.allowed_use",
                    default_database="master",
                    default_schema="public",
                    purpose_key="analytics.reporting",
                )

                explanation_union = {
                    "decision": client.explain_why(analytics["decision_id"]),
                    "authorization": client.explain_why(
                        authorization_id=analytics["authorization_id"]
                    ),
                    "validation": client.explain_why(
                        validation_id=safe_query["validation_id"]
                    ),
                }
                for kind, explanation in explanation_union.items():
                    print(kind, "->", explanation.get("kind", "decision"))
                """
            ),
            markdown(
                """
                ## Codify YOUR questions

                `collect_evidence(client, questions=...)` takes any list shaped like
                `DEFAULT_QUESTIONS` — codify the data-use questions your team answers
                every quarter and regenerate this packet on a schedule. After a
                republish, superseded decisions explain with `current: false` —
                historical, honestly labeled, never rewritten (walkthrough:
                publish-flip).
                """
            ),
        ]
    )


def purpose_bound_access_windows_notebook() -> dict:
    return notebook(
        [
            markdown(
                """
                # 16 - Purpose-bound Agent Data Windows

                One agent-access requirement has four variables: database,
                purpose, window anchor, and lookback length. This notebook makes
                all four combinations explicit instead of hiding them behind one
                generic retention rule:

                | Database | Purpose | Window |
                | --- | --- | --- |
                | `master` | research | rolling 90 days |
                | `master` | commercial | rolling 30 days |
                | `product` | research | as-of 90 days |
                | `product` | commercial | as-of 30 days |

                Rolling windows are anchored to the server evaluation time. As-of
                windows are reproducible: the caller must state the anchor in
                `data_access_context.as_of`. Authorization returns the required
                bounds; query validation proves SQL is no broader than them.
                """
            ),
            code(SETUP_CELL),
            code(
                """
                # The access-window policies are bound to the exact `agent`
                # role. Offline mode replays those recordings; live mode uses
                # a separate agent-bound token so the rest of the pack can
                # retain its identity-neutral release credential.
                agent_client = get_client(token_env="METATATE_SAAS_MCP_AGENT_TOKEN")
                """
            ),
            markdown("## 1. Authorize every combination"),
            code(
                """
                AS_OF = "2026-08-01T00:00:00Z"

                authorization_cases = [
                    ("master / research", dict(
                        asset=asset("customers"),
                        use="research recent customer behavior",
                        scenario_key="access.read",
                        purpose_key="research.general",
                    )),
                    ("master / commercial", dict(
                        asset=asset("customers"),
                        use="prepare a commercial customer analysis",
                        scenario_key="access.read",
                        purpose_key="commercial.general",
                    )),
                    ("product / research", dict(
                        asset=asset("product_usage_events", database="product"),
                        use="reproduce product research as of a fixed date",
                        scenario_key="access.read",
                        purpose_key="research.general",
                        data_access_context={"as_of": AS_OF},
                    )),
                    ("product / commercial", dict(
                        asset=asset("product_usage_events", database="product"),
                        use="reproduce a commercial product analysis as of a fixed date",
                        scenario_key="access.read",
                        purpose_key="commercial.general",
                        data_access_context={"as_of": AS_OF},
                    )),
                ]

                authorizations = {}
                for label, arguments in authorization_cases:
                    answer = agent_client.authorize_use(**arguments)
                    authorizations[label] = answer
                    window = next(
                        (c for c in answer.get("conditions", [])
                         if c.get("kind") == "data_window_required"),
                        {},
                    )
                    projection = window.get("projection") or {}
                    print(
                        f"{label:22} -> {answer_label(answer):12} "
                        f"{projection.get('type', '?'):7} "
                        f"{projection.get('lookback_days', '?')} days"
                    )
                """
            ),
            markdown(
                """
                The decision is conditional, not an unconditional allow. The
                condition is executable evidence: it names the time column and
                exact lower/upper bounds an agent must apply before reading data.
                """
            ),
            markdown("## 2. Missing context fails closed"),
            code(
                """
                missing_purpose = agent_client.authorize_use(
                    asset("customers"),
                    use="read recent customer records",
                    scenario_key="access.read",
                )
                missing_as_of = agent_client.authorize_use(
                    asset("product_usage_events", database="product"),
                    use="read product events for research",
                    scenario_key="access.read",
                    purpose_key="research.general",
                )

                print("missing purpose ->", missing_purpose["state"], missing_purpose["reason_code"])
                print("missing as_of   ->", missing_as_of["state"], missing_as_of["reason_code"])
                """
            ),
            markdown(
                """
                Metatate does not infer research versus commercial use, and it
                does not substitute the current time for a missing as-of anchor.
                Both omissions return a typed review requirement.
                """
            ),
            markdown("## 3. Prove the SQL stays inside the authorized window"),
            code(
                """
                validation_cases = [
                    ("master research 90", dict(
                        sql="SELECT customer_id, account_status FROM master.public.customers WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '90 days' AND created_at <= CURRENT_TIMESTAMP",
                        scenario_key="access.read", default_database="master", default_schema="public",
                        purpose_key="research.general",
                    )),
                    ("master commercial 30", dict(
                        sql="SELECT customer_id, account_status FROM master.public.customers WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days' AND created_at <= CURRENT_TIMESTAMP",
                        scenario_key="access.read", default_database="master", default_schema="public",
                        purpose_key="commercial.general",
                    )),
                    ("product research 90", dict(
                        sql="SELECT customer_id, event_name FROM product.public.product_usage_events WHERE occurred_at >= TIMESTAMPTZ '2026-05-03T00:00:00Z' AND occurred_at <= TIMESTAMPTZ '2026-08-01T00:00:00Z'",
                        scenario_key="access.read", default_database="product", default_schema="public",
                        purpose_key="research.general", data_access_context={"as_of": AS_OF},
                    )),
                    ("product commercial 30", dict(
                        sql="SELECT customer_id, event_name FROM product.public.product_usage_events WHERE occurred_at >= TIMESTAMPTZ '2026-07-02T00:00:00Z' AND occurred_at <= TIMESTAMPTZ '2026-08-01T00:00:00Z'",
                        scenario_key="access.read", default_database="product", default_schema="public",
                        purpose_key="commercial.general", data_access_context={"as_of": AS_OF},
                    )),
                ]

                for label, arguments in validation_cases:
                    answer = agent_client.validate_query_context(**arguments)
                    print(f"{label:24} -> {answer.get('verdict')} / {answer.get('state')}")
                """
            ),
            markdown("## 4. A wider window is rejected"),
            code(
                """
                broad_rolling = agent_client.validate_query_context(
                    "SELECT customer_id, account_status FROM master.public.customers WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '90 days' AND created_at <= CURRENT_TIMESTAMP",
                    scenario_key="access.read", default_database="master", default_schema="public",
                    purpose_key="commercial.general",
                )
                broad_as_of = agent_client.validate_query_context(
                    "SELECT customer_id, event_name FROM product.public.product_usage_events WHERE occurred_at >= TIMESTAMPTZ '2026-05-03T00:00:00Z' AND occurred_at <= TIMESTAMPTZ '2026-08-01T00:00:00Z'",
                    scenario_key="access.read", default_database="product", default_schema="public",
                    purpose_key="commercial.general", data_access_context={"as_of": AS_OF},
                )

                print("commercial rolling 90 ->", broad_rolling.get("verdict"))
                print("commercial as-of 90   ->", broad_as_of.get("verdict"))
                """
            ),
            markdown(
                """
                The commercial policy permits 30 days. Asking for 90 days is a
                broader read and fails, even though the same SQL shape is valid
                for research. Database, purpose, anchor type, and duration all
                remain decision-bearing inputs.
                """
            ),
        ]
    )


def adtech_consent_notebook() -> dict:
    return notebook(
        [
            markdown(
                """
                # 17 - AdTech: Consent as Three Permissions in One Field

                A single `marketing_consent = true` collapses three distinct
                permissions. A person may permit measurement but not
                personalization, or activation but not cross-context sharing —
                an agent reading one boolean treats all uses as allowed, which
                is a compliance violation, not a data error.

                The estate keeps the legacy boolean AND the fixed model: three
                purpose-scoped consent bases, served per declared purpose.

                | Declared purpose | Consent basis | Lane |
                | --- | --- | --- |
                | `analytics.reporting` (measurement) | `consent_measurement` | consent question |
                | `marketing.personalization` | `consent_personalization` | consent question |
                | `sharing.third_party` (activation) | `consent_activation` | consent + transfer |

                Metatate never reads data values: each answer is a typed
                `consent_required` condition naming the exact basis column the
                agent must verify — never satisfiable by caller assertion.
                """
            ),
            code(SETUP_CELL),
            markdown("## 1. One field, three questions"),
            code(
                """
                consent_cases = [
                    ("measurement", dict(
                        asset=asset("customers"),
                        use="measure campaign reach across customers",
                        scenario_key="consent.required",
                        purpose_key="analytics.reporting",
                    )),
                    ("personalization", dict(
                        asset=asset("customers"),
                        use="personalize offers from customer records",
                        scenario_key="consent.required",
                        purpose_key="marketing.personalization",
                    )),
                    ("activation", dict(
                        asset=asset("customers"),
                        use="activate an audience with a demand-side partner",
                        scenario_key="consent.required",
                        purpose_key="sharing.third_party",
                    )),
                ]

                consents = {}
                for label, arguments in consent_cases:
                    answer = client.authorize_use(**arguments)
                    consents[label] = answer
                    condition = next(
                        (c for c in answer.get("conditions", [])
                         if c.get("kind") == "consent_required"),
                        {},
                    )
                    projection = condition.get("projection") or {}
                    print(
                        f"{label:16} -> {answer_label(answer):12} "
                        f"verify {projection.get('basis_column', '?')}"
                    )
                """
            ),
            markdown(
                """
                Same record, three different verification requirements — the
                purpose selects the consent basis, and the typed projection
                names the exact column the agent must check before proceeding.
                """
            ),
            markdown("## 2. Consent recorded is not use permitted"),
            code(
                """
                allowed_lane = client.authorize_use(
                    asset("customers"),
                    use="personalize offers from customer records",
                    scenario_key="purpose.allowed_use",
                    purpose_key="marketing.personalization",
                )
                prohibited_lane = client.authorize_use(
                    asset("customers"),
                    use="personalize offers from customer records",
                    scenario_key="purpose.prohibited_use",
                    purpose_key="marketing.personalization",
                )
                print("allowed-use lane    ->", answer_label(allowed_lane))
                print("prohibited-use lane ->", answer_label(prohibited_lane))
                """
            ),
            markdown(
                """
                Personalization of the raw record is not merely
                consent-conditioned — no permit covers it (review) and the
                prohibition names it outright (deny). Consent and permission
                are separate questions with separate answers.
                """
            ),
            markdown("## 3. Missing purpose fails closed"),
            code(
                """
                missing_purpose = client.authorize_use(
                    asset("customers"),
                    use="use customer records for an advertising workflow",
                    scenario_key="consent.required",
                )
                print("missing purpose ->", missing_purpose["state"], missing_purpose["reason_code"])
                """
            ),
            markdown("## 4. Activation is a transfer"),
            code(
                """
                approved = client.authorize_use(
                    asset("ad_audience_exports"),
                    use="activate the consented audience with an approved partner",
                    scenario_key="residency.cross_border_transfer",
                    operation="export",
                    destination={"system": "APPROVED_DSP_A"},
                )
                unlisted = client.authorize_use(
                    asset("ad_audience_exports"),
                    use="activate the audience with an unlisted platform",
                    scenario_key="residency.cross_border_transfer",
                    operation="export",
                    destination={"system": "UNLISTED_DSP"},
                )
                print("approved partner ->", answer_label(approved))
                print("unlisted partner ->", answer_label(unlisted))
                """
            ),
            markdown("## 5. The purpose flips the verdict, not the SQL"),
            code(
                """
                CONSENT_SQL = "SELECT customer_id, consent_measurement, consent_personalization, consent_activation FROM customers"

                measurement_sql = client.validate_query_context(
                    CONSENT_SQL,
                    scenario_key="purpose.allowed_use",
                    default_database="master", default_schema="public",
                    purpose_key="analytics.reporting",
                )
                personalization_sql = client.validate_query_context(
                    CONSENT_SQL,
                    scenario_key="purpose.allowed_use",
                    default_database="master", default_schema="public",
                    purpose_key="marketing.personalization",
                )
                print("measurement     ->", measurement_sql.get("verdict"), "/", measurement_sql.get("state"))
                print("personalization ->", personalization_sql.get("verdict"), "/", personalization_sql.get("state"))
                """
            ),
            markdown("## 6. The receipt"),
            code(
                """
                receipt = client.explain_why(
                    authorization_id=consents["measurement"]["authorization_id"],
                )
                print("decision  :", receipt["decision"], "/", receipt["answer_state"])
                print("cited rows:", len(receipt["cited_decision_ids"]))
                print("evaluated :", receipt["provenance"]["evaluated_at"])
                """
            ),
            markdown(
                """
                Byte-identical SQL, two verdicts — the declared purpose is the
                decision-bearing input. And every determination above is a
                durable, citable record: the receipt reconstructs what was
                asked, which policy answered, and why.
                """
            ),
        ]
    )


def payments_source_of_truth_notebook() -> dict:
    return notebook(
        [
            markdown(
                """
                # 18 - Payments: Local Data Is Not the Source of Truth

                A transaction's true state lives across the processor, the
                network, and the local ledger — and they disagree in real time.
                The local record says "settled" while the network says
                "pending reversal". Correctness comes from reconciliation, and
                WHICH source wins depends on the QUESTION:

                | Question (purpose) | Authoritative source |
                | --- | --- |
                | `fraud.detection` | `network_settlements` |
                | `operations.support` (customer balance) | `payment_transactions` |
                | `compliance.audit` (fees) | `processor_settlements` |
                | `analytics.reporting` | reconciled rows only |

                That authority matrix is an ORGANIZATIONAL JUDGMENT — exactly
                what Metatate serves. The platform never computes reconciliation;
                it tells the agent which source wins and what to verify.
                """
            ),
            code(SETUP_CELL),
            markdown("## 1. Meaning first: three systems, three truths"),
            code(
                """
                local_meaning = client.inspect_data_meaning(
                    ref=asset("payment_transactions", "settlement_state", schema="finance"),
                )
                network_meaning = client.inspect_data_meaning(
                    ref=asset("network_settlements", "settlement_state", schema="finance"),
                )
                print("local  :", local_meaning["meaning"])
                print("network:", network_meaning["meaning"])
                """
            ),
            markdown("## 2. Same transaction, three questions"),
            code(
                """
                authority_cases = [
                    ("fraud / network", dict(
                        asset=asset("network_settlements", schema="finance"),
                        use="investigate suspected fraud on a settled transaction",
                        scenario_key="purpose.allowed_use",
                        purpose_key="fraud.detection",
                    )),
                    ("fraud / local ledger", dict(
                        asset=asset("payment_transactions", schema="finance"),
                        use="investigate suspected fraud on a settled transaction",
                        scenario_key="purpose.allowed_use",
                        purpose_key="fraud.detection",
                    )),
                    ("balance / local ledger", dict(
                        asset=asset("payment_transactions", schema="finance"),
                        use="answer a customer-facing balance question",
                        scenario_key="purpose.allowed_use",
                        purpose_key="operations.support",
                    )),
                    ("fees / processor", dict(
                        asset=asset("processor_settlements", schema="finance"),
                        use="reconcile processor fees for the audit trail",
                        scenario_key="purpose.allowed_use",
                        purpose_key="compliance.audit",
                    )),
                ]

                answers = {}
                for label, arguments in authority_cases:
                    answer = client.authorize_use(**arguments)
                    answers[label] = answer
                    print(f"{label:24} -> {answer_label(answer)}")
                """
            ),
            markdown(
                """
                The SAME fraud question answers differently by SOURCE: the
                network table allows, the local ledger fails closed to review —
                with the guidance naming where the authoritative state lives.
                """
            ),
            markdown("## 3. Analytics is conditional on reconciliation"),
            code(
                """
                reconciled = client.authorize_use(
                    asset("payment_transactions", schema="finance"),
                    use="report revenue analytics over payment transactions",
                    scenario_key="quality.reliability",
                    purpose_key="analytics.reporting",
                )
                condition = next(
                    (c for c in reconciled.get("conditions", [])
                     if c.get("kind") == "ai_restriction"),
                    {},
                )
                print(answer_label(reconciled), "->", condition.get("requirement", ""))
                """
            ),
            markdown("## 4. The wrong-source query gets caught"),
            code(
                """
                wrong_source = client.validate_query_context(
                    "SELECT transaction_id, settlement_state FROM master.finance.payment_transactions WHERE settlement_state <> 'reconciled'",
                    scenario_key="purpose.allowed_use",
                    default_database="master", default_schema="public",
                    purpose_key="fraud.detection",
                )
                right_source = client.validate_query_context(
                    "SELECT transaction_id, settlement_state FROM master.finance.network_settlements",
                    scenario_key="purpose.allowed_use",
                    default_database="master", default_schema="public",
                    purpose_key="fraud.detection",
                )
                print("fraud on local ledger ->", wrong_source.get("verdict"), "/", wrong_source.get("state"))
                print("fraud on network      ->", right_source.get("verdict"), "/", right_source.get("state"))
                """
            ),
            markdown(
                """
                Authority is served as judgment, not computed from data: the
                policies carry which source wins per question, the conditions
                carry what the agent must verify, and every answer cites the
                governing policy. Reconciliation itself remains the estate's
                job — Metatate makes the authority explicit and auditable.
                """
            ),
        ]
    )


def healthcare_four_concepts_notebook() -> dict:
    return notebook(
        [
            markdown(
                """
                # 19 - Healthcare: One Person as Four Concepts

                The same individual is a PATIENT (clinical, treatment basis), a
                MEMBER (coverage and eligibility), a CONSUMER (marketing, a
                different consent regime), and a SUBJECT (research, protocol
                governed). One record, four governing rule sets — an agent that
                treats them as one identity applies the wrong permissions.

                Identity is never a caller claim here: each context is a
                separate MCP token whose `bound_role` was verified at issuance.

                | Verified role | Table read | Clinical columns | Purpose lane |
                | --- | --- | --- | --- |
                | `clinical` | allow | visible | `care.treatment` |
                | `member_services` | review | masked | `care.eligibility` |
                | `research` | review | — | de-identified only |
                | `marketing` | review | — | denied without opt-in |

                Field-level specifics are illustrative, not clinical guidance.
                """
            ),
            code(SETUP_CELL),
            code(
                """
                # Four verified identities — four credentials. Offline mode
                # replays the per-role recordings; live mode uses four separate
                # role-bound tokens.
                clinical = get_client(token_env="METATATE_SAAS_MCP_CLINICAL_TOKEN")
                member_services = get_client(token_env="METATATE_SAAS_MCP_MEMBER_SERVICES_TOKEN")
                research = get_client(token_env="METATATE_SAAS_MCP_RESEARCH_TOKEN")
                marketing = get_client(token_env="METATATE_SAAS_MCP_MARKETING_TOKEN")
                """
            ),
            markdown("## 1. The table-grain role gate"),
            code(
                """
                read_cases = [
                    ("clinical", clinical, "read the full member record on a treatment basis"),
                    ("member_services", member_services, "read the full member record for coverage work"),
                    ("research", research, "read member records for a research cohort"),
                    ("marketing", marketing, "read member records for outreach targeting"),
                ]

                for label, role_client, use in read_cases:
                    answer = role_client.authorize_use(
                        asset("member_records", database="care"),
                        use=use,
                        scenario_key="access.read",
                    )
                    print(f"{label:16} -> {answer_label(answer)}")
                """
            ),
            markdown(
                """
                Only the clinical role reads the full record at table grain — a
                treatment basis. Every other identity fails closed to review
                here: coverage work reads through the eligibility PURPOSE lane,
                never a table-wide grant.
                """
            ),
            markdown("## 2. The column-grain contrast"),
            code(
                """
                notes_clinical = clinical.authorize_use(
                    asset("member_records", "clinical_notes", database="care"),
                    use="display clinician notes during treatment",
                    scenario_key="masking.display",
                )
                notes_member = member_services.authorize_use(
                    asset("member_records", "clinical_notes", database="care"),
                    use="display the member record in a coverage tool",
                    scenario_key="masking.display",
                )
                print("clinical        ->", answer_label(notes_clinical))
                print("member_services ->", answer_label(notes_member))
                """
            ),
            markdown("## 3. The member context reads through its purpose"),
            code(
                """
                eligibility = member_services.authorize_use(
                    asset("member_records", database="care"),
                    use="check coverage eligibility for a claim",
                    scenario_key="purpose.allowed_use",
                    purpose_key="care.eligibility",
                )
                eligibility_consent = member_services.authorize_use(
                    asset("member_records", database="care"),
                    use="check coverage eligibility for a claim",
                    scenario_key="consent.required",
                    purpose_key="care.eligibility",
                )
                condition = next(
                    (c for c in eligibility_consent.get("conditions", [])
                     if c.get("kind") == "consent_required"),
                    {},
                )
                projection = condition.get("projection") or {}
                print("eligibility purpose ->", answer_label(eligibility))
                print("eligibility consent ->", answer_label(eligibility_consent),
                      "verify", projection.get("basis_column", "?"))
                """
            ),
            markdown("## 4. The subject context: de-identified, protocol-gated"),
            code(
                """
                anonymize = research.authorize_use(
                    asset("member_records", database="care"),
                    use="analyze member outcomes for a research study",
                    scenario_key="protection.anonymization",
                    purpose_key="research.general",
                )
                research_consent = research.authorize_use(
                    asset("member_records", database="care"),
                    use="analyze member outcomes for a research study",
                    scenario_key="consent.required",
                    purpose_key="research.general",
                )
                training = research.authorize_use(
                    asset("member_records", database="care"),
                    use="train a model on member records",
                    scenario_key="ai.training",
                )
                print("research use      ->", answer_label(anonymize))
                print("research consent  ->", answer_label(research_consent))
                print("model training    ->", answer_label(training))
                """
            ),
            markdown(
                """
                Research is conditional twice over: anonymize first, and verify
                the recorded research authorization. "Only under an active
                protocol" is the steward-granted exception lane
                (`request_access` -> approval -> retry with the cited
                exception), which notebook 09 walks end to end — never a policy
                switch an agent can flip.
                """
            ),
            markdown("## 5. The consumer context"),
            code(
                """
                outreach = marketing.authorize_use(
                    asset("member_records", database="care"),
                    use="market wellness products to members",
                    scenario_key="purpose.prohibited_use",
                    purpose_key="marketing.advertising",
                )
                outreach_consent = marketing.authorize_use(
                    asset("member_records", database="care"),
                    use="market wellness products to members",
                    scenario_key="consent.required",
                    purpose_key="marketing.advertising",
                )
                treatment_consent = clinical.authorize_use(
                    asset("member_records", database="care"),
                    use="treat the member in a clinical encounter",
                    scenario_key="consent.required",
                    purpose_key="care.treatment",
                )
                print("marketing use      ->", answer_label(outreach))
                print("marketing consent  ->", answer_label(outreach_consent))
                print("treatment consent  ->", treatment_consent["state"], treatment_consent["reason_code"])
                """
            ),
            markdown(
                """
                Marketing is denied on its purpose lane, and even its consent
                question is only conditional on the recorded opt-in. Treatment
                deliberately has NO consent rule — asking the consent question
                for a purpose no rule names fails closed to review rather than
                inventing an answer.
                """
            ),
            markdown("## 6. The role flips the SQL verdict"),
            code(
                """
                NOTES_SQL = "SELECT member_id, clinical_notes FROM care.public.member_records"

                sql_clinical = clinical.validate_query_context(
                    NOTES_SQL,
                    scenario_key="purpose.allowed_use",
                    default_database="master", default_schema="public",
                    purpose_key="care.treatment",
                )
                sql_member = member_services.validate_query_context(
                    NOTES_SQL,
                    scenario_key="purpose.allowed_use",
                    default_database="master", default_schema="public",
                    purpose_key="care.treatment",
                )
                print("clinical        ->", sql_clinical.get("verdict"), "/", sql_clinical.get("state"))
                print("member_services ->", sql_member.get("verdict"), "/", sql_member.get("state"))
                """
            ),
            markdown("## 7. The receipt"),
            code(
                """
                receipt = research.explain_why(
                    authorization_id=anonymize["authorization_id"],
                )
                print("decision  :", receipt["decision"], "/", receipt["answer_state"])
                print("cited rows:", len(receipt["cited_decision_ids"]))
                print("evaluated :", receipt["provenance"]["evaluated_at"])
                """
            ),
            markdown(
                """
                Same record, four verified identities, four access shapes —
                each one a durable, citable decision. The role is never a
                caller claim: it rides the token, and the provenance on every
                answer states which identity was evaluated.
                """
            ),
        ]
    )


def government_statute_notebook() -> dict:
    return notebook(
        [
            markdown(
                """
                # 20 - Government: The Rules Live Outside the Record

                Program eligibility is determined by statute — income
                thresholds, categorical rules, exceptions, effective dates —
                that live in law and policy manuals, not in the data. The
                applicant record has the fields; nothing in it encodes which
                rule version applies or when it changed.

                Here the statutes are versioned, date-effective POLICIES layered
                over the record:

                | Mechanic | How it is served |
                | --- | --- |
                | Statute versions | validity windows (`effectiveFrom`/`Until`) |
                | "As of the application date" | `data_access_context.as_of` |
                | Categorical over income test | priority bands, visible in rank |
                | Documented exceptions | the steward request lane |

                Program mechanics are illustrative by design.
                """
            ),
            code(SETUP_CELL),
            markdown("## 1. Which statute answers today"),
            code(
                """
                today = client.authorize_use(
                    asset("applicants", database="benefits"),
                    use="determine benefits eligibility for an application",
                    scenario_key="compliance.regulatory",
                    purpose_key="benefits.determination",
                )
                print("today ->", answer_label(today))
                for row in today.get("instructions", []):
                    print(
                        f"  {row['provenance']['policy_name']:28}"
                        f" effective_until={row.get('effective_until')}"
                    )
                """
            ),
            markdown("## 2. The as-of flip: evaluate under the statute in force at T"),
            code(
                """
                as_of_2027 = client.authorize_use(
                    asset("applicants", database="benefits"),
                    use="determine benefits eligibility for an application",
                    scenario_key="compliance.regulatory",
                    purpose_key="benefits.determination",
                    data_access_context={"as_of": "2027-02-01T00:00:00Z"},
                )
                condition = next(
                    (c for c in as_of_2027.get("conditions", [])
                     if c.get("kind") == "ai_restriction"),
                    {},
                )
                print("as of 2027-02-01 ->", answer_label(as_of_2027))
                print("  requirement:", condition.get("requirement", ""))
                print("  validity_evaluated_at:", as_of_2027.get("validity_evaluated_at"))
                """
            ),
            markdown(
                """
                Same call, one added instant: the 2025 statute leaves force and
                the 2026 statute answers — with the partition instant stated in
                the provenance. The record never changed; the RULES did.
                """
            ),
            markdown("## 3. Published but not in force"),
            code(
                """
                not_yet = client.authorize_use(
                    asset("qualifying_conditions", database="benefits"),
                    use="apply the modernized categorical checklist",
                    scenario_key="compliance.regulatory",
                    purpose_key="benefits.determination",
                )
                print("qualifying_conditions ->", not_yet["state"], "/", not_yet["reason_code"])
                """
            ),
            markdown("## 4. Managed precedence: categorical over the income test"),
            code(
                """
                precedence = client.authorize_use(
                    asset("applicants", database="benefits"),
                    use="run an automated benefits determination",
                    scenario_key="ai.automated_decisioning",
                    purpose_key="benefits.determination",
                )
                print("determination ->", answer_label(precedence))
                for row in precedence.get("instructions", []):
                    print(
                        f"  priority={row['priority']} "
                        f"{row['provenance']['policy_name']:32} {row['decision']}"
                    )
                """
            ),
            markdown(
                """
                The categorical permit (critical band) outranks the income test
                (high band) in the ranked instructions — precedence is
                governed, versioned, and visible. And the composition is
                fail-safe: the income-test CONDITION still surfaces on the
                answer, so a permitted determination never silently skips it.
                """
            ),
            markdown("## 5. Managed precedence vs unmanaged disagreement"),
            code(
                """
                conflict = client.authorize_use(
                    asset("applicants", database="benefits"),
                    use="run verification outreach against applicants",
                    scenario_key="purpose.allowed_use",
                )
                print("verification outreach ->", conflict["state"], "/", conflict["reason_code"])
                sources = (conflict.get("conflict") or {}).get("sources", [])
                for source in sources:
                    print("  conflicting:", source["provenance"]["policy_name"])
                """
            ),
            markdown(
                """
                Contrast: two same-band policies disagree about verification
                outreach, and the estate surfaces the CONFLICT with both
                sources cited instead of silently picking a winner. Managed
                precedence is governance; unmanaged disagreement is debt made
                visible. Documented exceptions follow the steward request lane
                (notebook 09): an exception can satisfy a review or a
                condition — it never overrides a deny.
                """
            ),
            markdown("## 6. The as-of instant flips the SQL verdict too"),
            code(
                """
                DETERMINATION_SQL = "SELECT applicant_id, categorical_flag FROM benefits.public.applicants"

                sql_today = client.validate_query_context(
                    DETERMINATION_SQL,
                    scenario_key="compliance.regulatory",
                    default_database="master", default_schema="public",
                    purpose_key="benefits.determination",
                )
                sql_2027 = client.validate_query_context(
                    DETERMINATION_SQL,
                    scenario_key="compliance.regulatory",
                    default_database="master", default_schema="public",
                    purpose_key="benefits.determination",
                    data_access_context={"as_of": "2027-02-01T00:00:00Z"},
                )
                print("today          ->", sql_today.get("verdict"), "/", sql_today.get("state"))
                print("as of 2027     ->", sql_2027.get("verdict"), "/", sql_2027.get("state"))
                """
            ),
            markdown("## 7. The receipt"),
            code(
                """
                receipt = client.explain_why(
                    authorization_id=as_of_2027["authorization_id"],
                )
                print("decision  :", receipt["decision"], "/", receipt["answer_state"])
                print("cited rows:", len(receipt["cited_decision_ids"]))
                print("evaluated :", receipt["provenance"]["evaluated_at"])
                """
            ),
            markdown(
                """
                "Which rule version applied?" is answerable after the fact: the
                durable record carries the policy version, its effective
                window, and the instant the validity partition used.
                """
            ),
        ]
    )


NOTEBOOKS = {
    "00_setup_live_or_offline.ipynb": setup_notebook,
    "01_decision_layer_cookbook.ipynb": cookbook_notebook,
    "02_governed_sql_agent_langgraph.ipynb": langgraph_notebook,
    "03_transfer_governance_before_export.ipynb": transfer_notebook,
    "04_governed_text_to_sql_agent.ipynb": governed_text_to_sql_notebook,
    "05_agent_red_team_evaluation_harness.ipynb": red_team_notebook,
    "06_ci_gate_for_data_ai_changes.ipynb": ci_gate_notebook,
    "07_governed_rag_embedding_ingestion_gate.ipynb": governed_rag_ingestion_gate_notebook,
    "08_openai_agents_tool_guard_pattern.ipynb": openai_agents_tool_guard_notebook,
    "09_human_approval_packet_for_conditional_export.ipynb": approval_workflow_notebook,
    "10_llamaindex_governed_retrieval_pattern.ipynb": llamaindex_retrieval_notebook,
    "11_langgraph_governed_sql_agent_runtime.ipynb": langgraph_governed_sql_agent_runtime_notebook,
    "12_governance_states_and_the_wider_estate.ipynb": governance_states_notebook,
    "13_sql_gauntlet_validate_query_context.ipynb": sql_gauntlet_notebook,
    "14_governed_agent_end_to_end.ipynb": governed_agent_arc_notebook,
    "15_audit_evidence_packet.ipynb": audit_evidence_notebook,
    "16_purpose_bound_agent_data_windows.ipynb": purpose_bound_access_windows_notebook,
    "17_adtech_consent_three_permissions_one_field.ipynb": adtech_consent_notebook,
    "18_payments_local_data_is_not_the_source_of_truth.ipynb": payments_source_of_truth_notebook,
    "19_healthcare_one_person_four_concepts.ipynb": healthcare_four_concepts_notebook,
    "20_government_rules_outside_the_record.ipynb": government_statute_notebook,
}


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the committed notebooks match this generator instead of writing",
    )
    args = parser.parse_args()

    NOTEBOOK_DIR.mkdir(parents=True, exist_ok=True)
    stale: list[str] = []
    for filename, factory in NOTEBOOKS.items():
        path = NOTEBOOK_DIR / filename
        rendered = json.dumps(factory(), indent=2) + "\n"
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != rendered:
                stale.append(filename)
            continue
        path.write_text(rendered, encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")

    if args.check:
        extras = sorted(
            path.name for path in NOTEBOOK_DIR.glob("*.ipynb") if path.name not in NOTEBOOKS
        )
        if stale or extras:
            for name in stale:
                print(f"stale (edit scripts/build_notebooks.py, then regenerate): {name}")
            for name in extras:
                print(f"not produced by the generator: {name}")
            raise SystemExit(1)
        print(f"{len(NOTEBOOKS)} notebooks match scripts/build_notebooks.py")


if __name__ == "__main__":
    main()
