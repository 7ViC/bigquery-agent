"""
API request and response schemas.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    """Request body for /agent/run and /agent/stream."""

    prompt: str = Field(..., description="Natural language prompt for the agent", min_length=1)
    dataset: str = Field("", description="BigQuery dataset (uses default if empty)")
    table: str = Field("", description="BigQuery table (auto-detected if empty)")


class AgentResponse(BaseModel):
    """Response from /agent/run."""

    response: str = Field(..., description="Agent's final explanation")
    intent: str = Field("", description="Classified intent")
    plan: str = Field("", description="Execution plan")
    sql: str = Field("", description="Generated SQL (if any)")
    row_count: int = Field(0, description="Number of rows in result")
    data: list[dict[str, Any]] = Field(default_factory=list, description="Query result data")
    chart_spec: dict[str, Any] = Field(default_factory=dict, description="Chart specification")
    cleaning_report: str = Field("", description="Data cleaning report")
    edit_summary: str = Field("", description="Edit operation summary")
    analysis: str = Field("", description="Statistical analysis")
    steps: list[str] = Field(default_factory=list, description="Steps the agent took")
    error: str = Field("", description="Error message if any")


class StreamEvent(BaseModel):
    """A single event in the SSE stream."""

    node: str
    data: dict[str, Any]


class TableSchema(BaseModel):
    """Schema of a BigQuery table."""

    name: str
    type: str
    mode: str
    description: str = ""


class TableInfo(BaseModel):
    """Metadata about a BigQuery table."""

    table_id: str
    num_rows: int
    num_bytes: int
    created: str
    modified: str
    description: str
    num_columns: int
    schema_fields: list[TableSchema] = Field(default_factory=list)
