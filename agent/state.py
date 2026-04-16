"""
Agent State — the shared data structure that every node reads and writes.
"""

from __future__ import annotations

import operator
from dataclasses import dataclass, field
from typing import Any, Literal

from langgraph.graph import MessagesState


# The possible intents the router can classify
Intent = Literal["query", "clean", "edit", "analyze", "visualize", "explain", "error"]


@dataclass
class AgentState(MessagesState):
    """
    Shared state that flows through the entire LangGraph.
    Every node can read any field and write to the fields it owns.
    """

    # --- Input ---
    user_prompt: str = ""
    dataset: str = ""
    table: str = ""

    # --- Router ---
    intent: Intent = "query"
    plan: str = ""

    # --- Schema context ---
    table_schema: list[dict[str, Any]] = field(default_factory=list)
    sample_rows: list[dict[str, Any]] = field(default_factory=list)

    # --- SQL Generation & Execution ---
    generated_sql: str = ""
    sql_result: list[dict[str, Any]] = field(default_factory=list)
    row_count: int = 0

    # --- Cleaning ---
    cleaning_report: str = ""
    cleaning_actions: list[str] = field(default_factory=list)

    # --- Editing ---
    edit_sql: str = ""
    edit_summary: str = ""

    # --- Analysis ---
    analysis_text: str = ""
    statistics: dict[str, Any] = field(default_factory=dict)

    # --- Visualization ---
    chart_spec: dict[str, Any] = field(default_factory=dict)
    chart_type: str = ""

    # --- Explanation ---
    explanation: str = ""

    # --- Metadata ---
    steps_taken: list[str] = field(default_factory=list)
    error: str = ""
    final_response: str = ""
