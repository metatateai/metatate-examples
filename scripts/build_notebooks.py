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
    print("  2. Workspace dashboard: 'Load the demo' banner -> 'Load the AcmeCloud demo'")
    print("  3. MCP Tools -> Tokens: issue a token; Connect tab has your endpoint URL")
    print("  4. export METATATE_MCP_URL=... METATATE_SAAS_MCP_TOKEN=...")
    print("     (full steps: docs/live-mode-saas.md)")

client = get_client()
print(f"Metatate examples mode: {mode}")


def asset(table, column=None):
    ref = {"database": "acmecloud_demo", "schema": "public", "table": table}
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

                This notebook checks the AcmeCloud fixture and initializes the shared Metatate client.

                Offline mode is the default. It replays RECORDED Metatate Cloud answers (captured
                from a live workspace by `scripts/record_offline_fixtures.py`), so what you study
                offline is exactly what the live endpoint returns — typed answers with
                `state`, lowercase decision vocabulary, structured conditions, and publication provenance.

                Live mode calls your Metatate Cloud workspace's MCP endpoint (no account yet? create one free at [app.getmetatate.com/sign-up?ref=examples](https://app.getmetatate.com/sign-up?ref=examples) and load the AcmeCloud demo from the dashboard's **"New here?" banner → Load the demo**). Set `METATATE_EXAMPLES_MODE=live`, export `METATATE_MCP_URL` and your access token, then start Jupyter — see [docs/live-mode-saas.md](../docs/live-mode-saas.md).
                """
            ),
            code(SETUP_CELL),
            markdown("## Load Synthetic Tables"),
            code(
                """
                table_dir = repo_root / "sample-data" / "acmecloud" / "tables"
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
                4. authorize a proposed use (allow AND deny)
                5. validate generated SQL before execution
                6. explain a decision by chaining its `decision_id`
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
                ## 4. Authorize a proposed use

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
            markdown("## 5. Validate SQL before execution (intent- and column-aware)"),
            code(
                """
                safe = client.validate_query_context(
                    "SELECT region, SUM(arr) FROM customers GROUP BY region",
                    scenario_key="purpose.allowed_use",
                    default_database="acmecloud_demo",
                    default_schema="public",
                )
                print(f"aggregate query -> {safe['verdict']}")

                detail = client.validate_query_context(
                    "SELECT customer_name, email FROM customers WHERE region = 'EU'",
                    scenario_key="purpose.allowed_use",
                    default_database="acmecloud_demo",
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
                ## 6. Explain the decision

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

                def governed_sql(sql, scenario_key):
                    answer = client.validate_query_context(
                        sql,
                        scenario_key=scenario_key,
                        default_database="acmecloud_demo",
                        default_schema="public",
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
                        default_database="acmecloud_demo",
                        default_schema="public",
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
                (`sample-data/acmecloud/expected-decisions.yaml`) and is asserted against the
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
                    default_database="acmecloud_demo",
                    default_schema="public",
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
                        default_database="acmecloud_demo",
                        default_schema="public",
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
