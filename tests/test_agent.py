"""
Agent integration tests.
These tests mock the BigQuery client so they run without GCP credentials.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from agent.state import AgentState


# ─── Mock data ───────────────────────────────────────────
MOCK_SCHEMA = [
    {"name": "order_id", "type": "STRING", "mode": "REQUIRED", "description": ""},
    {"name": "product", "type": "STRING", "mode": "REQUIRED", "description": ""},
    {"name": "quantity", "type": "INTEGER", "mode": "REQUIRED", "description": ""},
    {"name": "total_amount", "type": "FLOAT", "mode": "REQUIRED", "description": ""},
    {"name": "region", "type": "STRING", "mode": "REQUIRED", "description": ""},
]

MOCK_ROWS = [
    {"order_id": "ORD-001", "product": "Laptop", "quantity": 2, "total_amount": 2599.98, "region": "North"},
    {"order_id": "ORD-002", "product": "Mouse", "quantity": 5, "total_amount": 149.95, "region": "South"},
    {"order_id": "ORD-003", "product": "Desk", "quantity": 1, "total_amount": 549.00, "region": "East"},
]


# ─── Test State ──────────────────────────────────────────
def test_agent_state_defaults():
    """AgentState should initialize with sensible defaults."""
    state = AgentState(messages=[])
    assert state.user_prompt == ""
    assert state.intent == "query"
    assert state.steps_taken == []
    assert state.error == ""


def test_agent_state_with_values():
    """AgentState should accept custom values."""
    state = AgentState(
        messages=[],
        user_prompt="Show me sales",
        intent="query",
        table="sales_data",
    )
    assert state.user_prompt == "Show me sales"
    assert state.table == "sales_data"


# ─── Test Router Node ───────────────────────────────────
@patch("agent.nodes.list_tables", return_value=["sales_data"])
@patch("agent.nodes._llm_call")
def test_router_classifies_query(mock_llm, mock_tables):
    """Router should classify a data retrieval request as 'query'."""
    from agent.nodes import router_node

    mock_llm.return_value = 'INTENT: query\nPLAN: Fetch top 10 sales rows\nTABLE: sales_data'

    result = router_node({
        "user_prompt": "Show me the top 10 sales",
        "dataset": "autoanalyst",
        "table_schema": MOCK_SCHEMA,
        "sample_rows": MOCK_ROWS,
        "steps_taken": ["load_schema"],
    })

    assert result["intent"] == "query"
    assert "router" in result["steps_taken"][-1]


@patch("agent.nodes.list_tables", return_value=["sales_data"])
@patch("agent.nodes._llm_call")
def test_router_classifies_clean(mock_llm, mock_tables):
    """Router should classify a cleaning request as 'clean'."""
    from agent.nodes import router_node

    mock_llm.return_value = 'INTENT: clean\nPLAN: Fix nulls and duplicates\nTABLE: sales_data'

    result = router_node({
        "user_prompt": "Clean this data, remove duplicates",
        "dataset": "autoanalyst",
        "table_schema": MOCK_SCHEMA,
        "sample_rows": MOCK_ROWS,
        "steps_taken": ["load_schema"],
    })

    assert result["intent"] == "clean"


@patch("agent.nodes.list_tables", return_value=["sales_data"])
@patch("agent.nodes._llm_call")
def test_router_classifies_visualize(mock_llm, mock_tables):
    """Router should classify a chart request as 'visualize'."""
    from agent.nodes import router_node

    mock_llm.return_value = 'INTENT: visualize\nPLAN: Create bar chart of sales by region\nTABLE: sales_data'

    result = router_node({
        "user_prompt": "Show me a bar chart of sales by region",
        "dataset": "autoanalyst",
        "table_schema": MOCK_SCHEMA,
        "sample_rows": MOCK_ROWS,
        "steps_taken": ["load_schema"],
    })

    assert result["intent"] == "visualize"


# ─── Test Query Node ────────────────────────────────────
@patch("agent.nodes.execute_query", return_value=MOCK_ROWS)
@patch("agent.nodes.validate_sql", return_value={"valid": True, "estimated_bytes": 1000})
@patch("agent.nodes._llm_call")
def test_query_node_generates_sql(mock_llm, mock_validate, mock_execute):
    """Query node should generate SQL and execute it."""
    from agent.nodes import query_node

    mock_llm.return_value = "SELECT * FROM `proj.ds.sales_data` LIMIT 10"

    result = query_node({
        "user_prompt": "Show me the top 10 rows",
        "dataset": "autoanalyst",
        "table": "sales_data",
        "table_schema": MOCK_SCHEMA,
        "sample_rows": MOCK_ROWS,
        "steps_taken": ["load_schema", "router → query"],
    })

    assert "generated_sql" in result
    assert result["row_count"] == 3
    assert len(result["sql_result"]) == 3


@patch("agent.nodes.validate_sql", return_value={"valid": False, "error": "Syntax error"})
@patch("agent.nodes._llm_call")
def test_query_node_handles_invalid_sql(mock_llm, mock_validate):
    """Query node should handle invalid SQL gracefully."""
    from agent.nodes import query_node

    mock_llm.return_value = "INVALID SQL HERE"

    result = query_node({
        "user_prompt": "Do something weird",
        "dataset": "autoanalyst",
        "table": "sales_data",
        "table_schema": MOCK_SCHEMA,
        "sample_rows": MOCK_ROWS,
        "steps_taken": [],
    })

    assert result.get("error")
    assert "validation" in result["error"].lower()


# ─── Test Analyze Node ──────────────────────────────────
@patch("agent.nodes._llm_call")
def test_analyze_node_produces_analysis(mock_llm):
    """Analyze node should produce textual analysis."""
    from agent.nodes import analyze_node

    mock_llm.return_value = "The data shows strong sales in the North region with average order value of $1,099."

    result = analyze_node({
        "user_prompt": "Analyze the sales data",
        "dataset": "autoanalyst",
        "table": "sales_data",
        "table_schema": MOCK_SCHEMA,
        "sample_rows": MOCK_ROWS,
        "sql_result": MOCK_ROWS,
        "steps_taken": ["load_schema", "router → analyze"],
    })

    assert result["analysis_text"]
    assert "analyze" in result["steps_taken"]


# ─── Test Visualize Node ────────────────────────────────
@patch("agent.nodes._llm_call")
def test_visualize_node_produces_chart_spec(mock_llm):
    """Visualize node should produce a valid chart specification."""
    from agent.nodes import visualize_node

    mock_llm.return_value = json.dumps({
        "chart_type": "bar",
        "title": "Sales by Region",
        "x": "region",
        "y": "total_amount",
        "color": None,
        "orientation": "v",
        "labels": {"x": "Region", "y": "Total Amount ($)"},
    })

    result = visualize_node({
        "user_prompt": "Show a bar chart of sales by region",
        "dataset": "autoanalyst",
        "table": "sales_data",
        "table_schema": MOCK_SCHEMA,
        "sample_rows": MOCK_ROWS,
        "sql_result": MOCK_ROWS,
        "steps_taken": [],
    })

    assert result["chart_type"] == "bar"
    assert result["chart_spec"]["title"] == "Sales by Region"


# ─── Test Error Node ────────────────────────────────────
def test_error_node_returns_message():
    """Error handler should produce a user-friendly error message."""
    from agent.nodes import error_node

    result = error_node({
        "error": "Table not found",
        "steps_taken": ["load_schema"],
    })

    assert "Table not found" in result["final_response"]
    assert "error_handler" in result["steps_taken"]


# ─── Test Explain Node ──────────────────────────────────
@patch("agent.nodes._llm_call")
def test_explain_node_narrates(mock_llm):
    """Explain node should narrate the agent's actions."""
    from agent.nodes import explain_node

    mock_llm.return_value = "I retrieved the top sales data from your sales_data table."

    result = explain_node({
        "user_prompt": "Show me sales",
        "plan": "Query top sales",
        "generated_sql": "SELECT * FROM tbl LIMIT 10",
        "row_count": 10,
        "cleaning_report": "",
        "edit_summary": "",
        "analysis_text": "",
        "steps_taken": ["load_schema", "router → query", "query (10 rows)"],
    })

    assert result["final_response"]
    assert "explain" in result["steps_taken"]
