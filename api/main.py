"""
FastAPI server — the REST API for the AutoAnalyst agent.
"""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from agent.graph import run_agent, stream_agent
from agent.tools import get_table_info, get_table_schema, list_datasets, list_tables
from agent.utils import setup_logging
from api.schemas import AgentRequest, AgentResponse, TableInfo, TableSchema
from config.settings import get_settings

logger = logging.getLogger("autoanalyst.api")


# ─── Lifespan ────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    settings = get_settings()
    logger.info(
        "AutoAnalyst API starting (project=%s, dataset=%s, llm=%s)",
        settings.gcp_project_id,
        settings.bq_dataset,
        settings.llm_provider,
    )
    yield
    logger.info("AutoAnalyst API shutting down")


# ─── App ─────────────────────────────────────────────────
app = FastAPI(
    title="AutoAnalyst API",
    description="Autonomous Data Analyst Agent — LangGraph + BigQuery + LLM",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Health ──────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "autoanalyst"}


# ─── Agent Endpoints ────────────────────────────────────
@app.post("/agent/run", response_model=AgentResponse)
async def agent_run(req: AgentRequest):
    """Run the full agent pipeline and return the complete result."""
    try:
        state = await run_agent(
            user_prompt=req.prompt,
            dataset=req.dataset,
            table=req.table,
        )

        return AgentResponse(
            response=state.get("final_response", state.get("explanation", "")),
            intent=state.get("intent", ""),
            plan=state.get("plan", ""),
            sql=state.get("generated_sql", state.get("edit_sql", "")),
            row_count=state.get("row_count", 0),
            data=state.get("sql_result", [])[:100],  # Cap at 100 rows for response
            chart_spec=state.get("chart_spec", {}),
            cleaning_report=state.get("cleaning_report", ""),
            edit_summary=state.get("edit_summary", ""),
            analysis=state.get("analysis_text", ""),
            steps=state.get("steps_taken", []),
            error=state.get("error", ""),
        )
    except Exception as e:
        logger.exception("Agent run failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agent/stream")
async def agent_stream(req: AgentRequest):
    """Stream agent execution as Server-Sent Events."""

    async def event_generator():
        try:
            async for node_name, update in stream_agent(
                user_prompt=req.prompt,
                dataset=req.dataset,
                table=req.table,
            ):
                event_data = {
                    "node": node_name,
                    "steps_taken": update.get("steps_taken", []),
                }

                # Include relevant data based on the node
                if node_name == "router":
                    event_data["intent"] = update.get("intent", "")
                    event_data["plan"] = update.get("plan", "")
                elif node_name == "query":
                    event_data["sql"] = update.get("generated_sql", "")
                    event_data["row_count"] = update.get("row_count", 0)
                elif node_name == "clean":
                    event_data["cleaning_report"] = update.get("cleaning_report", "")
                elif node_name == "edit":
                    event_data["edit_summary"] = update.get("edit_summary", "")
                elif node_name == "analyze":
                    event_data["analysis"] = update.get("analysis_text", "")[:500]
                elif node_name == "visualize":
                    event_data["chart_spec"] = update.get("chart_spec", {})
                elif node_name == "explain":
                    event_data["response"] = update.get("final_response", "")
                elif node_name == "error_handler":
                    event_data["error"] = update.get("final_response", "")

                yield {"event": "step", "data": json.dumps(event_data, default=str)}

            yield {"event": "done", "data": json.dumps({"status": "complete"})}
        except Exception as e:
            logger.exception("Stream failed")
            yield {"event": "error", "data": json.dumps({"error": str(e)})}

    return EventSourceResponse(event_generator())


# ─── Data Endpoints ─────────────────────────────────────
@app.get("/datasets")
async def get_datasets():
    """List all BigQuery datasets in the project."""
    try:
        return {"datasets": list_datasets()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tables/{dataset}")
async def get_tables(dataset: str):
    """List all tables in a dataset."""
    try:
        return {"dataset": dataset, "tables": list_tables(dataset)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/schema/{dataset}/{table}")
async def get_schema(dataset: str, table: str):
    """Get the schema of a specific table."""
    try:
        schema = get_table_schema(table, dataset)
        info = get_table_info(table, dataset)
        return {
            "dataset": dataset,
            "table": table,
            "info": info,
            "schema": schema,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Run directly ────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
