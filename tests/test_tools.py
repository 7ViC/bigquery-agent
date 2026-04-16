"""
Unit tests for agent tools and utilities.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from agent.utils import format_rows, format_schema, safe_json_parse, truncate


# ─── Test format_schema ─────────────────────────────────
def test_format_schema_basic():
    schema = [
        {"name": "id", "type": "INTEGER", "mode": "REQUIRED", "description": "Primary key"},
        {"name": "name", "type": "STRING", "mode": "NULLABLE", "description": ""},
    ]
    result = format_schema(schema)
    assert "id (INTEGER, REQUIRED)" in result
    assert "# Primary key" in result
    assert "name (STRING, NULLABLE)" in result


def test_format_schema_empty():
    assert format_schema([]) == "(no schema available)"


# ─── Test format_rows ───────────────────────────────────
def test_format_rows_basic():
    rows = [{"a": 1, "b": "hello"}, {"a": 2, "b": "world"}]
    result = format_rows(rows)
    assert "hello" in result
    assert "world" in result


def test_format_rows_truncates():
    rows = [{"x": i} for i in range(100)]
    result = format_rows(rows, max_rows=3)
    parsed = json.loads(result)
    assert len(parsed) == 3


def test_format_rows_empty():
    assert format_rows([]) == "(no data)"


# ─── Test truncate ───────────────────────────────────────
def test_truncate_short():
    assert truncate("hello", 100) == "hello"


def test_truncate_long():
    text = "a" * 200
    result = truncate(text, 50)
    assert len(result) == 50
    assert result.endswith("...")


# ─── Test safe_json_parse ────────────────────────────────
def test_safe_json_parse_valid():
    result = safe_json_parse('{"key": "value"}')
    assert result == {"key": "value"}


def test_safe_json_parse_with_fences():
    result = safe_json_parse('```json\n{"key": "value"}\n```')
    assert result == {"key": "value"}


def test_safe_json_parse_invalid():
    result = safe_json_parse("not json at all")
    assert result is None


def test_safe_json_parse_nested():
    data = {"chart_type": "bar", "x": "region", "y": "sales", "labels": {"x": "Region"}}
    result = safe_json_parse(json.dumps(data))
    assert result["chart_type"] == "bar"
    assert result["labels"]["x"] == "Region"


# ─── Test BigQuery tools (mocked) ───────────────────────
@patch("agent.tools.get_bq_client")
def test_list_datasets(mock_client):
    from agent.tools import list_datasets

    mock_ds = MagicMock()
    mock_ds.dataset_id = "test_dataset"
    mock_client.return_value.list_datasets.return_value = [mock_ds]

    result = list_datasets()
    assert result == ["test_dataset"]


@patch("agent.tools.get_bq_client")
def test_list_tables(mock_client):
    from agent.tools import list_tables

    mock_tbl = MagicMock()
    mock_tbl.table_id = "sales_data"
    mock_client.return_value.list_tables.return_value = [mock_tbl]

    result = list_tables("test_dataset")
    assert result == ["sales_data"]


@patch("agent.tools.get_bq_client")
def test_validate_sql_valid(mock_client):
    from agent.tools import validate_sql

    mock_job = MagicMock()
    mock_job.total_bytes_processed = 1024
    mock_client.return_value.query.return_value = mock_job

    result = validate_sql("SELECT 1")
    assert result["valid"] is True
    assert result["estimated_bytes"] == 1024


@patch("agent.tools.get_bq_client")
def test_validate_sql_invalid(mock_client):
    from google.cloud.exceptions import GoogleCloudError

    from agent.tools import validate_sql

    mock_client.return_value.query.side_effect = GoogleCloudError("Syntax error")

    result = validate_sql("INVALID SQL")
    assert result["valid"] is False
    assert "Syntax error" in result["error"]


@patch("agent.tools.get_bq_client")
def test_execute_query(mock_client):
    from agent.tools import execute_query

    mock_row = MagicMock()
    mock_row.__iter__ = lambda self: iter([("id", 1), ("name", "test")])
    mock_row.keys.return_value = ["id", "name"]

    # Make dict(row) work
    mock_result = [{"id": 1, "name": "test"}]
    mock_job = MagicMock()
    mock_job.result.return_value = mock_result

    mock_client.return_value.query.return_value = mock_job

    # We need to patch differently since execute_query does dict(row) for row in results
    with patch("agent.tools.get_bq_client") as mc:
        job = MagicMock()

        class FakeRow(dict):
            pass

        job.result.return_value = [FakeRow(id=1, name="test")]
        mc.return_value.query.return_value = job

        result = execute_query("SELECT 1 as id, 'test' as name")
        assert len(result) == 1
