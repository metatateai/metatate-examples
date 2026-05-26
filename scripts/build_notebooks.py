#!/usr/bin/env python3
"""Render the public notebook pack from Python cell definitions."""

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

client = get_client()
mode = os.getenv("METATATE_EXAMPLES_MODE", "offline")
print(f"Metatate examples mode: {mode}")
"""


def setup_notebook() -> dict:
    return notebook(
        [
            markdown(
                """
                # 00 - Setup: Live Or Offline

                This notebook checks the AcmeCloud fixture and initializes the shared Metatate client.

                Offline mode is the default. It reads committed response fixtures and requires no Snowflake account.

                Live mode calls the Metatate Native App SQL tool layer in Snowflake. Set `METATATE_EXAMPLES_MODE=live` and configure `.env` before starting Jupyter.
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
            markdown("## Discover Governed Context"),
            code(
                """
                response = client.discover_context(database="ACMECLOUD_DEMO", schema="PUBLIC")
                print(json.dumps(response["data"], indent=2))
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

                This notebook walks through the core Metatate flow:

                1. discover governed tables
                2. inspect business and column meaning
                3. authorize a proposed use
                4. validate generated SQL
                5. explain a decision
                """
            ),
            code(SETUP_CELL),
            markdown("## 1. Discover governed tables"),
            code(
                """
                discover = client.discover_context(database="ACMECLOUD_DEMO", schema="PUBLIC")
                pd.DataFrame(discover["data"]["tables"])[
                    ["full_table_name", "sensitivity", "enforcement_mode", "has_pii", "domain", "owner"]
                ]
                """
            ),
            markdown("## 2. Get table-level decision context"),
            code(
                """
                table_name = "ACMECLOUD_DEMO.PUBLIC.CUSTOMERS"
                context = client.get_decision_context(table_name)
                print(json.dumps(context["data"]["policy_summary"], indent=2))
                print(json.dumps(context["data"]["business_context"], indent=2))
                """
            ),
            markdown("## 3. Inspect column meaning"),
            code(
                """
                meaning = client.inspect_data_meaning(table_name)
                pd.DataFrame(meaning["data"]["columns"])[
                    ["column_name", "data_type_label", "data_category", "is_pii", "effective_sensitivity", "masking_type"]
                ]
                """
            ),
            markdown("## 4. Authorize analytics"),
            code(
                """
                analytics = client.authorize_use(
                    table_name,
                    operation="read",
                    intended_use="analytics",
                    actor_role="DATA_ANALYST",
                    columns=["CUSTOMER_ID", "EMAIL", "ARR"],
                )
                print(json.dumps(analytics["data"], indent=2))
                """
            ),
            markdown("## 5. Validate generated SQL before execution"),
            code(
                """
                sql = "SELECT customer_id, email, arr FROM ACMECLOUD_DEMO.PUBLIC.CUSTOMERS WHERE region = 'EU'"
                validation = client.validate_query_context(
                    sql,
                    operation="read",
                    intended_use="analytics",
                    actor_role="DATA_ANALYST",
                )
                print(json.dumps(validation["data"], indent=2))
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

                This example shows the agent pattern Metatate is meant to support:

                User asks a business question, the agent discovers context, drafts SQL, validates it through Metatate, and revises or blocks the output based on the decision.

                If `langgraph` is installed, the cells build a small graph. Without it, the notebook runs the same steps as plain Python so the example stays readable.
                """
            ),
            code(SETUP_CELL),
            code(
                """
                from typing import TypedDict, Any

                TABLE = "ACMECLOUD_DEMO.PUBLIC.CUSTOMERS"
                QUESTION = "Show ARR by region for active customers. Include email if it helps identify accounts."


                class AgentState(TypedDict, total=False):
                    question: str
                    context: dict[str, Any]
                    draft_sql: str
                    validation: dict[str, Any]
                    final_sql: str
                    decision: str
                    notes: list[str]


                def discover_context_step(state: AgentState) -> AgentState:
                    context = client.get_decision_context(TABLE)
                    return {**state, "context": context}


                def draft_sql_step(state: AgentState) -> AgentState:
                    # The initial draft intentionally includes EMAIL so Metatate can catch it.
                    draft_sql = (
                        "SELECT region, email, SUM(arr) AS arr "
                        "FROM ACMECLOUD_DEMO.PUBLIC.CUSTOMERS "
                        "WHERE account_status = 'active' "
                        "GROUP BY region, email"
                    )
                    return {**state, "draft_sql": draft_sql}


                def validate_sql_step(state: AgentState) -> AgentState:
                    validation = client.validate_query_context(
                        state["draft_sql"],
                        operation="read",
                        intended_use="analytics",
                        actor_role="DATA_ANALYST",
                    )
                    decision = validation["data"].get("decision", {}).get("decision", "UNKNOWN")
                    return {**state, "validation": validation, "decision": decision}


                def revise_sql_step(state: AgentState) -> AgentState:
                    findings = state["validation"]["data"].get("sql_findings", [])
                    final_sql = state["draft_sql"]
                    notes = []
                    if any(item.get("code") == "PII_COLUMN_SELECTED" for item in findings):
                        final_sql = (
                            "SELECT region, SUM(arr) AS arr "
                            "FROM ACMECLOUD_DEMO.PUBLIC.CUSTOMERS "
                            "WHERE account_status = 'active' "
                            "GROUP BY region"
                        )
                        notes.append("Removed EMAIL because Metatate flagged it as PII for analytics.")
                    return {**state, "final_sql": final_sql, "notes": notes}
                """
            ),
            code(
                """
                try:
                    from langgraph.graph import END, StateGraph

                    workflow = StateGraph(AgentState)
                    workflow.add_node("discover_context", discover_context_step)
                    workflow.add_node("draft_sql", draft_sql_step)
                    workflow.add_node("validate_sql", validate_sql_step)
                    workflow.add_node("revise_sql", revise_sql_step)
                    workflow.set_entry_point("discover_context")
                    workflow.add_edge("discover_context", "draft_sql")
                    workflow.add_edge("draft_sql", "validate_sql")
                    workflow.add_edge("validate_sql", "revise_sql")
                    workflow.add_edge("revise_sql", END)
                    app = workflow.compile()
                    result = app.invoke({"question": QUESTION})
                    print("Ran with LangGraph.")
                except ImportError:
                    result = {"question": QUESTION}
                    for step in (discover_context_step, draft_sql_step, validate_sql_step, revise_sql_step):
                        result = step(result)
                    print("LangGraph is not installed. Ran the same flow as plain Python.")

                print("Question:")
                print(result["question"])
                print("\\nDraft SQL:")
                print(result["draft_sql"])
                print("\\nMetatate decision:")
                print(result["decision"])
                print("\\nFinal SQL:")
                print(result["final_sql"])
                print("\\nNotes:")
                print("\\n".join(result.get("notes", [])))
                """
            ),
            markdown(
                """
                The point is not the SQL itself. The point is that the agent does not decide alone. It checks the decision layer before handing SQL to a user or workflow.
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

                This notebook demonstrates destination-aware authorization. The same source table produces different decisions depending on destination system, destination jurisdiction, and consumer jurisdiction.
                """
            ),
            code(SETUP_CELL),
            markdown("## Approved destination with required controls"),
            code(
                """
                table_name = "ACMECLOUD_DEMO.PUBLIC.CUSTOMERS"
                salesforce = client.authorize_use(
                    table_name,
                    operation="export",
                    intended_use="external_sharing",
                    actor_role="DATA_ENGINEER",
                    columns=["CUSTOMER_ID", "CUSTOMER_NAME", "EMAIL", "ACCOUNT_STATUS"],
                    destination={"system": "SALESFORCE", "jurisdiction": "US"},
                    consumer_jurisdiction="EU",
                )
                print(json.dumps(salesforce["data"], indent=2))
                """
            ),
            markdown("## Explain the conditional decision"),
            code(
                """
                decision_id = salesforce["data"]["decision_id"]
                explanation = client.explain_why(decision_id=decision_id)
                print(json.dumps(explanation["data"], indent=2))
                """
            ),
            markdown("## Prohibited destination"),
            code(
                """
                ads_platform = client.authorize_use(
                    table_name,
                    operation="export",
                    intended_use="external_sharing",
                    actor_role="DATA_ENGINEER",
                    columns=["CUSTOMER_ID", "CUSTOMER_NAME", "EMAIL"],
                    destination={"system": "ADS_PLATFORM", "jurisdiction": "US"},
                    consumer_jurisdiction="US",
                )
                print(json.dumps(ads_platform["data"], indent=2))
                """
            ),
            markdown(
                """
                A useful agent should not simply generate an export query. It should ask the data's decision layer whether the transfer is allowed for the actual destination.
                """
            ),
        ]
    )


NOTEBOOKS = {
    "00_setup_live_or_offline.ipynb": setup_notebook,
    "01_decision_layer_cookbook.ipynb": cookbook_notebook,
    "02_governed_sql_agent_langgraph.ipynb": langgraph_notebook,
    "03_transfer_governance_before_export.ipynb": transfer_notebook,
}


def main() -> None:
    NOTEBOOK_DIR.mkdir(parents=True, exist_ok=True)
    for filename, factory in NOTEBOOKS.items():
        path = NOTEBOOK_DIR / filename
        path.write_text(json.dumps(factory(), indent=2) + "\n", encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
