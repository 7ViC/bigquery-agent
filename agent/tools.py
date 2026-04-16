"""
BigQuery tool wrappers — the agent's hands for touching data.
Each function is a standalone tool that can be called by agent nodes.
"""

from __future__ import annotations

import logging
from typing import Any

from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import get_settings

logger = logging.getLogger("autoanalyst.tools")

# ─── Client singleton ───────────────────────────────────
_client: bigquery.Client | None = None


def get_bq_client() -> bigquery.Client:
    """Return a cached BigQuery client."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = bigquery.Client(
            project=settings.gcp_project_id,
            location=settings.gcp_location,
        )
        logger.info(
            "BigQuery client initialized (project=%s, location=%s)",
            settings.gcp_project_id,
            settings.gcp_location,
        )
    return _client


# ─── List Operations ────────────────────────────────────
def list_datasets() -> list[str]:
    """List all datasets in the project."""
    client = get_bq_client()
    datasets = list(client.list_datasets())
    return [ds.dataset_id for ds in datasets]


def list_tables(dataset: str | None = None) -> list[str]:
    """List all tables in a dataset."""
    settings = get_settings()
    ds = dataset or settings.bq_dataset
    client = get_bq_client()
    tables = list(client.list_tables(f"{settings.gcp_project_id}.{ds}"))
    return [t.table_id for t in tables]


# ─── Schema ─────────────────────────────────────────────
def get_table_schema(table: str, dataset: str | None = None) -> list[dict[str, Any]]:
    """Get the schema of a BigQuery table as a list of dicts."""
    settings = get_settings()
    ds = dataset or settings.bq_dataset
    client = get_bq_client()
    ref = f"{settings.gcp_project_id}.{ds}.{table}"
    tbl = client.get_table(ref)
    return [
        {
            "name": field.name,
            "type": field.field_type,
            "mode": field.mode,
            "description": field.description or "",
        }
        for field in tbl.schema
    ]


def get_sample_rows(table: str, dataset: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
    """Fetch a few sample rows from a table."""
    settings = get_settings()
    ds = dataset or settings.bq_dataset
    ref = f"`{settings.gcp_project_id}.{ds}.{table}`"
    sql = f"SELECT * FROM {ref} LIMIT {limit}"
    return execute_query(sql)


# ─── Query Execution ────────────────────────────────────
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def execute_query(sql: str) -> list[dict[str, Any]]:
    """
    Execute a SQL query on BigQuery and return rows as list of dicts.
    Retries up to 3 times with exponential backoff.
    """
    client = get_bq_client()
    logger.info("Executing SQL:\n%s", sql[:500])

    try:
        job = client.query(sql)
        results = job.result()
        rows = [dict(row) for row in results]
        logger.info("Query returned %d rows", len(rows))
        return rows
    except GoogleCloudError as e:
        logger.error("BigQuery error: %s", e)
        raise


def execute_dml(sql: str) -> int:
    """
    Execute a DML statement (INSERT, UPDATE, DELETE, CREATE OR REPLACE).
    Returns the number of affected rows.
    """
    client = get_bq_client()
    logger.info("Executing DML:\n%s", sql[:500])

    try:
        job = client.query(sql)
        job.result()  # Wait for completion
        affected = job.num_dml_affected_rows or 0
        logger.info("DML affected %d rows", affected)
        return affected
    except GoogleCloudError as e:
        logger.error("BigQuery DML error: %s", e)
        raise


# ─── Table Info ──────────────────────────────────────────
def get_table_info(table: str, dataset: str | None = None) -> dict[str, Any]:
    """Get comprehensive table metadata."""
    settings = get_settings()
    ds = dataset or settings.bq_dataset
    client = get_bq_client()
    ref = f"{settings.gcp_project_id}.{ds}.{table}"
    tbl = client.get_table(ref)
    return {
        "table_id": tbl.table_id,
        "num_rows": tbl.num_rows,
        "num_bytes": tbl.num_bytes,
        "created": str(tbl.created),
        "modified": str(tbl.modified),
        "description": tbl.description or "",
        "num_columns": len(tbl.schema),
    }


# ─── Validation ──────────────────────────────────────────
def validate_sql(sql: str) -> dict[str, Any]:
    """
    Dry-run a SQL query to check for syntax errors without executing.
    Returns {"valid": True} or {"valid": False, "error": "..."}.
    """
    client = get_bq_client()
    job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
    try:
        job = client.query(sql, job_config=job_config)
        return {
            "valid": True,
            "estimated_bytes": job.total_bytes_processed,
        }
    except GoogleCloudError as e:
        return {
            "valid": False,
            "error": str(e),
        }
