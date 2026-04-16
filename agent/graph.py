"""
LangGraph State Machine — the orchestration brain.

This defines the directed graph of nodes that the agent traverses.
The router determines which path to take based on the user's intent.
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, StateGraph

from agent.nodes import (
    analyze_node,
    clean_node,
    edit_node,
    error_node,
    explain_node,
    load_schema_node,
    query_node,
    router_node,
    visualize_node,
)
from agent.state import AgentState

logger = logging.getLogger("autoanalyst.graph")


def _route_by_intent(state: AgentState) -> str:
    """Conditional edge: route to the appropriate node based on classified intent."""
    if state.get("error"):
        return "error_handler"

    intent = state.get("intent", "query")
    mapping = {
        "query": "query",
        "clean": "clean",
        "edit": "edit",
        "analyze": "analyze",
        "visualize": "visualize",
        "explain": "explain",
    }
    return mapping.get(intent, "query")


def _should_analyze_after_query(state: AgentState) -> str:
    """After query, decide if we should also analyze or go straight to explain."""
    if state.get("error"):
        return "error_handler"
    # If the original intent was analyze or visualize, the query was just a data fetch
    intent = state.get("intent", "")
    if intent == "analyze":
        return "analyze"
    if intent == "visualize":
        return "visualize"
    return "explain"


def _post_action_route(state: AgentState) -> str:
    """After any action node, go to explain (or error)."""
    if state.get("error"):
        return "error_handler"
    return "explain"


def build_agent_graph() -> StateGraph:
    """
    Build and compile the full agent graph.

    Flow:
        load_schema → router → [query|clean|edit|analyze|visualize|explain] → explain → END
    """
    graph = StateGraph(AgentState)

    # ── Register all nodes ──
    graph.add_node("load_schema", load_schema_node)
    graph.add_node("router", router_node)
    graph.add_node("query", query_node)
    graph.add_node("clean", clean_node)
    graph.add_node("edit", edit_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("visualize", visualize_node)
    graph.add_node("explain", explain_node)
    graph.add_node("error_handler", error_node)

    # ── Entry point ──
    graph.set_entry_point("load_schema")

    # ── Edges ──
    # load_schema always goes to router
    graph.add_edge("load_schema", "router")

    # Router dispatches based on intent
    graph.add_conditional_edges(
        "router",
        _route_by_intent,
        {
            "query": "query",
            "clean": "clean",
            "edit": "edit",
            "analyze": "analyze",
            "visualize": "visualize",
            "explain": "explain",
            "error_handler": "error_handler",
        },
    )

    # After query, might need further processing
    graph.add_conditional_edges(
        "query",
        _should_analyze_after_query,
        {
            "analyze": "analyze",
            "visualize": "visualize",
            "explain": "explain",
            "error_handler": "error_handler",
        },
    )

    # After clean/edit/analyze/visualize → explain
    graph.add_conditional_edges("clean", _post_action_route, {"explain": "explain", "error_handler": "error_handler"})
    graph.add_conditional_edges("edit", _post_action_route, {"explain": "explain", "error_handler": "error_handler"})
    graph.add_conditional_edges("analyze", _post_action_route, {"explain": "explain", "error_handler": "error_handler"})
    graph.add_conditional_edges("visualize", _post_action_route, {"explain": "explain", "error_handler": "error_handler"})

    # Terminal nodes
    graph.add_edge("explain", END)
    graph.add_edge("error_handler", END)

    # ── Compile ──
    compiled = graph.compile()
    logger.info("Agent graph compiled successfully")
    return compiled


# ─── Convenience runner ──────────────────────────────────
async def run_agent(
    user_prompt: str,
    dataset: str = "",
    table: str = "",
) -> dict[str, Any]:
    """
    Run the full agent pipeline for a user prompt.
    Returns the final state dict.
    """
    graph = build_agent_graph()

    initial_state = {
        "user_prompt": user_prompt,
        "dataset": dataset,
        "table": table,
        "messages": [],
        "steps_taken": [],
    }

    logger.info("Running agent for prompt: %s", user_prompt[:100])
    final_state = await graph.ainvoke(initial_state)
    logger.info("Agent completed. Steps: %s", final_state.get("steps_taken", []))
    return final_state


async def stream_agent(
    user_prompt: str,
    dataset: str = "",
    table: str = "",
):
    """
    Stream agent execution step by step.
    Yields (node_name, state_update) tuples.
    """
    graph = build_agent_graph()

    initial_state = {
        "user_prompt": user_prompt,
        "dataset": dataset,
        "table": table,
        "messages": [],
        "steps_taken": [],
    }

    async for event in graph.astream(initial_state, stream_mode="updates"):
        for node_name, state_update in event.items():
            yield node_name, state_update
