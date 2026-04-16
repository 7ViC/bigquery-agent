"""
Agent Nodes — each function is a node in the LangGraph state machine.
Every node receives the full AgentState and returns a partial dict of updates.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from agent.prompts import (
    ANALYZE_PROMPT,
    CLEAN_PROMPT,
    EDIT_PROMPT,
    EXPLAIN_PROMPT,
    QUERY_PROMPT,
    ROUTER_PROMPT,
    VISUALIZE_PROMPT,
)
from agent.state import AgentState
from agent.tools import (
    execute_dml,
    execute_query,
    get_sample_rows,
    get_table_schema,
    list_tables,
    validate_sql,
)
from agent.utils import format_rows, format_schema, get_llm, safe_json_parse, truncate
from config.settings import get_settings

logger = logging.getLogger("autoanalyst.nodes")


# ─────────────────────────────────────────────────────────
# HELPER: invoke LLM
# ─────────────────────────────────────────────────────────
def _llm_call(prompt: str) -> str:
    """Call the LLM and return the text response."""
    llm = get_llm()
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content.strip()


# ─────────────────────────────────────────────────────────
# NODE: Load Schema
# ─────────────────────────────────────────────────────────
def load_schema_node(state: AgentState) -> dict[str, Any]:
    """Fetch table schema and sample rows to give the LLM context."""
    settings = get_settings()
    dataset = state.get("dataset") or settings.bq_dataset
    table = state.get("table", "")

    steps = list(state.get("steps_taken", []))
    steps.append("load_schema")

    # If no table specified, try to figure it out from available tables
    if not table:
        tables = list_tables(dataset)
        if tables:
            table = tables[0]
        else:
            return {
                "error": f"No tables found in dataset '{dataset}'.",
                "steps_taken": steps,
            }

    try:
        schema = get_table_schema(table, dataset)
        samples = get_sample_rows(table, dataset, limit=5)
        logger.info("Loaded schema for %s.%s (%d columns)", dataset, table, len(schema))
        return {
            "table_schema": schema,
            "sample_rows": samples,
            "table": table,
            "dataset": dataset,
            "steps_taken": steps,
        }
    except Exception as e:
        logger.error("Failed to load schema: %s", e)
        return {"error": f"Could not load table schema: {e}", "steps_taken": steps}


# ─────────────────────────────────────────────────────────
# NODE: Router
# ─────────────────────────────────────────────────────────
def router_node(state: AgentState) -> dict[str, Any]:
    """Classify the user's intent and build an execution plan."""
    settings = get_settings()
    dataset = state.get("dataset") or settings.bq_dataset

    tables = list_tables(dataset)
    schema_str = format_schema(state.get("table_schema", []))
    sample_str = format_rows(state.get("sample_rows", []))

    prompt = ROUTER_PROMPT.format(
        tables=", ".join(tables) if tables else "(none)",
        schema=schema_str,
        sample_rows=sample_str,
        user_prompt=state["user_prompt"],
    )

    response = _llm_call(prompt)
    logger.info("Router response:\n%s", response)

    # Parse the structured response
    intent = "query"
    plan = ""
    table = state.get("table", "")

    for line in response.strip().split("\n"):
        line = line.strip()
        if line.upper().startswith("INTENT:"):
            raw = line.split(":", 1)[1].strip().lower().strip('"\'')
            if raw in ("query", "clean", "edit", "analyze", "visualize", "explain"):
                intent = raw
        elif line.upper().startswith("PLAN:"):
            plan = line.split(":", 1)[1].strip()
        elif line.upper().startswith("TABLE:"):
            t = line.split(":", 1)[1].strip()
            if t and t.lower() != "auto":
                table = t

    steps = list(state.get("steps_taken", []))
    steps.append(f"router → {intent}")

    return {
        "intent": intent,
        "plan": plan,
        "table": table,
        "steps_taken": steps,
    }


# ─────────────────────────────────────────────────────────
# NODE: Query
# ─────────────────────────────────────────────────────────
def query_node(state: AgentState) -> dict[str, Any]:
    """Generate and execute a SELECT query."""
    settings = get_settings()
    dataset = state.get("dataset") or settings.bq_dataset
    table = state.get("table", "")
    schema_str = format_schema(state.get("table_schema", []))
    sample_str = format_rows(state.get("sample_rows", []))

    prompt = QUERY_PROMPT.format(
        project=settings.gcp_project_id,
        dataset=dataset,
        table=table,
        schema=schema_str,
        sample_rows=sample_str,
        user_prompt=state["user_prompt"],
    )

    sql = _llm_call(prompt)
    # Clean up any markdown fences
    sql = sql.replace("```sql", "").replace("```", "").strip()
    logger.info("Generated SQL:\n%s", sql)

    # Validate before executing
    validation = validate_sql(sql)
    if not validation.get("valid"):
        return {
            "generated_sql": sql,
            "error": f"SQL validation failed: {validation.get('error', 'unknown')}",
            "steps_taken": list(state.get("steps_taken", [])) + ["query (failed validation)"],
        }

    try:
        rows = execute_query(sql)
        steps = list(state.get("steps_taken", []))
        steps.append(f"query ({len(rows)} rows)")
        return {
            "generated_sql": sql,
            "sql_result": rows,
            "row_count": len(rows),
            "steps_taken": steps,
        }
    except Exception as e:
        return {
            "generated_sql": sql,
            "error": f"Query execution failed: {e}",
            "steps_taken": list(state.get("steps_taken", [])) + ["query (execution error)"],
        }


# ─────────────────────────────────────────────────────────
# NODE: Clean
# ─────────────────────────────────────────────────────────
def clean_node(state: AgentState) -> dict[str, Any]:
    """Detect data quality issues and fix them."""
    settings = get_settings()
    dataset = state.get("dataset") or settings.bq_dataset
    table = state.get("table", "")
    schema_str = format_schema(state.get("table_schema", []))

    # Get more sample rows for cleaning analysis
    samples = get_sample_rows(table, dataset, limit=20)
    sample_str = format_rows(samples, max_rows=20)

    prompt = CLEAN_PROMPT.format(
        project=settings.gcp_project_id,
        dataset=dataset,
        table=table,
        schema=schema_str,
        sample_rows=sample_str,
        user_prompt=state["user_prompt"],
    )

    response = _llm_call(prompt)
    logger.info("Clean response:\n%s", truncate(response, 500))

    # Parse structured response
    report = ""
    actions = []
    sql_statements = []
    current_section = None

    for line in response.split("\n"):
        stripped = line.strip()
        if stripped.upper().startswith("REPORT:"):
            current_section = "report"
            report = stripped.split(":", 1)[1].strip()
        elif stripped.upper().startswith("ACTIONS:"):
            current_section = "actions"
        elif stripped.upper().startswith("SQL:"):
            current_section = "sql"
            remainder = stripped.split(":", 1)[1].strip()
            if remainder:
                sql_statements.append(remainder)
        elif current_section == "report":
            report += "\n" + stripped
        elif current_section == "actions" and stripped:
            actions.append(stripped)
        elif current_section == "sql" and stripped:
            sql_statements.append(stripped)

    # Join and split by semicolons for multiple statements
    full_sql = " ".join(sql_statements)
    individual_sqls = [s.strip() for s in full_sql.split(";") if s.strip()]

    # Execute each cleaning SQL
    executed = []
    for sql in individual_sqls:
        try:
            validation = validate_sql(sql)
            if validation.get("valid"):
                affected = execute_dml(sql)
                executed.append(f"✓ {sql[:80]}... ({affected} rows)")
            else:
                executed.append(f"✗ Skipped (invalid): {sql[:80]}...")
        except Exception as e:
            executed.append(f"✗ Failed: {sql[:60]}... — {e}")

    steps = list(state.get("steps_taken", []))
    steps.append(f"clean ({len(executed)} actions)")

    return {
        "cleaning_report": report.strip(),
        "cleaning_actions": executed if executed else actions,
        "steps_taken": steps,
    }


# ─────────────────────────────────────────────────────────
# NODE: Edit
# ─────────────────────────────────────────────────────────
def edit_node(state: AgentState) -> dict[str, Any]:
    """Generate and execute INSERT/UPDATE/DELETE statements."""
    settings = get_settings()
    dataset = state.get("dataset") or settings.bq_dataset
    table = state.get("table", "")
    schema_str = format_schema(state.get("table_schema", []))
    sample_str = format_rows(state.get("sample_rows", []))

    prompt = EDIT_PROMPT.format(
        project=settings.gcp_project_id,
        dataset=dataset,
        table=table,
        schema=schema_str,
        sample_rows=sample_str,
        user_prompt=state["user_prompt"],
    )

    response = _llm_call(prompt)
    logger.info("Edit response:\n%s", truncate(response, 500))

    summary = ""
    sql = ""
    for line in response.split("\n"):
        stripped = line.strip()
        if stripped.upper().startswith("SUMMARY:"):
            summary = stripped.split(":", 1)[1].strip()
        elif stripped.upper().startswith("SQL:"):
            sql = stripped.split(":", 1)[1].strip()

    # If SQL spans multiple lines after the SQL: marker
    if not sql:
        in_sql = False
        sql_lines = []
        for line in response.split("\n"):
            if line.strip().upper().startswith("SQL:"):
                in_sql = True
                remainder = line.strip().split(":", 1)[1].strip()
                if remainder:
                    sql_lines.append(remainder)
            elif in_sql:
                sql_lines.append(line)
        sql = "\n".join(sql_lines).strip()

    sql = sql.replace("```sql", "").replace("```", "").strip()

    if not sql:
        return {
            "edit_summary": "Could not generate edit SQL from the request.",
            "error": "No SQL generated for edit operation.",
            "steps_taken": list(state.get("steps_taken", [])) + ["edit (no SQL)"],
        }

    # Validate and execute
    validation = validate_sql(sql)
    if not validation.get("valid"):
        return {
            "edit_sql": sql,
            "edit_summary": f"SQL validation failed: {validation.get('error')}",
            "error": validation.get("error", ""),
            "steps_taken": list(state.get("steps_taken", [])) + ["edit (invalid SQL)"],
        }

    try:
        affected = execute_dml(sql)
        summary = f"{summary} — {affected} rows affected."
        steps = list(state.get("steps_taken", []))
        steps.append(f"edit ({affected} rows)")
        return {
            "edit_sql": sql,
            "edit_summary": summary,
            "steps_taken": steps,
        }
    except Exception as e:
        return {
            "edit_sql": sql,
            "edit_summary": f"Edit failed: {e}",
            "error": str(e),
            "steps_taken": list(state.get("steps_taken", [])) + ["edit (error)"],
        }


# ─────────────────────────────────────────────────────────
# NODE: Analyze
# ─────────────────────────────────────────────────────────
def analyze_node(state: AgentState) -> dict[str, Any]:
    """Run statistical analysis on query results."""
    settings = get_settings()
    dataset = state.get("dataset") or settings.bq_dataset
    table = state.get("table", "")
    schema_str = format_schema(state.get("table_schema", []))
    results = state.get("sql_result", [])

    # If no results yet, run a broad query first
    if not results:
        try:
            ref = f"`{settings.gcp_project_id}.{dataset}.{table}`"
            results = execute_query(f"SELECT * FROM {ref} LIMIT 500")
        except Exception as e:
            return {
                "error": f"Could not fetch data for analysis: {e}",
                "steps_taken": list(state.get("steps_taken", [])) + ["analyze (no data)"],
            }

    result_str = format_rows(results, max_rows=50)

    prompt = ANALYZE_PROMPT.format(
        project=settings.gcp_project_id,
        dataset=dataset,
        table=table,
        schema=schema_str,
        results=result_str,
        row_count=len(results),
        user_prompt=state["user_prompt"],
    )

    analysis = _llm_call(prompt)
    steps = list(state.get("steps_taken", []))
    steps.append("analyze")

    return {
        "analysis_text": analysis,
        "sql_result": results,
        "row_count": len(results),
        "steps_taken": steps,
    }


# ─────────────────────────────────────────────────────────
# NODE: Visualize
# ─────────────────────────────────────────────────────────
def visualize_node(state: AgentState) -> dict[str, Any]:
    """Generate a Plotly chart specification."""
    settings = get_settings()
    dataset = state.get("dataset") or settings.bq_dataset
    table = state.get("table", "")
    results = state.get("sql_result", [])

    if not results:
        try:
            ref = f"`{settings.gcp_project_id}.{dataset}.{table}`"
            results = execute_query(f"SELECT * FROM {ref} LIMIT 500")
        except Exception as e:
            return {
                "error": f"Could not fetch data for visualization: {e}",
                "steps_taken": list(state.get("steps_taken", [])) + ["visualize (no data)"],
            }

    columns = list(results[0].keys()) if results else []
    result_str = format_rows(results, max_rows=30)

    prompt = VISUALIZE_PROMPT.format(
        results=result_str,
        row_count=len(results),
        columns=", ".join(columns),
        user_prompt=state["user_prompt"],
    )

    response = _llm_call(prompt)
    chart_spec = safe_json_parse(response)

    steps = list(state.get("steps_taken", []))
    steps.append("visualize")

    if chart_spec:
        return {
            "chart_spec": chart_spec,
            "chart_type": chart_spec.get("chart_type", "bar"),
            "sql_result": results,
            "row_count": len(results),
            "steps_taken": steps,
        }
    else:
        return {
            "error": "Could not parse chart specification from LLM.",
            "sql_result": results,
            "row_count": len(results),
            "steps_taken": steps,
        }


# ─────────────────────────────────────────────────────────
# NODE: Explain
# ─────────────────────────────────────────────────────────
def explain_node(state: AgentState) -> dict[str, Any]:
    """Produce a human-readable explanation of everything the agent did."""
    prompt = EXPLAIN_PROMPT.format(
        user_prompt=state.get("user_prompt", ""),
        steps=", ".join(state.get("steps_taken", [])),
        plan=state.get("plan", "N/A"),
        sql=state.get("generated_sql", state.get("edit_sql", "N/A")),
        row_count=state.get("row_count", 0),
        cleaning_report=state.get("cleaning_report", "N/A"),
        edit_summary=state.get("edit_summary", "N/A"),
        analysis=truncate(state.get("analysis_text", "N/A"), 1000),
    )

    explanation = _llm_call(prompt)
    steps = list(state.get("steps_taken", []))
    steps.append("explain")

    return {
        "explanation": explanation,
        "final_response": explanation,
        "steps_taken": steps,
    }


# ─────────────────────────────────────────────────────────
# NODE: Error Handler
# ─────────────────────────────────────────────────────────
def error_node(state: AgentState) -> dict[str, Any]:
    """Handle errors gracefully."""
    error = state.get("error", "An unknown error occurred.")
    return {
        "final_response": f"I encountered an issue: {error}\n\nPlease check your query and try again.",
        "steps_taken": list(state.get("steps_taken", [])) + ["error_handler"],
    }
