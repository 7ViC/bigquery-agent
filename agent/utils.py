"""
Utility helpers — logging setup, data formatting, LLM client factory.
"""

from __future__ import annotations

import json
import logging
import logging.config
from pathlib import Path
from typing import Any

import yaml
from langchain_core.language_models import BaseChatModel

from config.settings import get_settings

logger = logging.getLogger("autoanalyst")


# ─── Logging ────────────────────────────────────────────
def setup_logging() -> None:
    """Load logging config from YAML."""
    cfg_path = Path(__file__).resolve().parent.parent / "config" / "logging.yaml"
    if cfg_path.exists():
        with open(cfg_path) as f:
            config = yaml.safe_load(f)
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=logging.INFO)
    logger.info("Logging initialized")


# ─── LLM Factory ────────────────────────────────────────
def get_llm(temperature: float = 0.0) -> BaseChatModel:
    """Return a LangChain chat model based on config."""
    settings = get_settings()

    if settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=temperature,
        )
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            temperature=temperature,
        )


# ─── Formatting ─────────────────────────────────────────
def format_schema(schema: list[dict[str, Any]]) -> str:
    """Format BigQuery schema fields into a readable string."""
    if not schema:
        return "(no schema available)"
    lines = []
    for col in schema:
        name = col.get("name", "?")
        dtype = col.get("type", "?")
        mode = col.get("mode", "NULLABLE")
        desc = col.get("description", "")
        line = f"  - {name} ({dtype}, {mode})"
        if desc:
            line += f"  # {desc}"
        lines.append(line)
    return "\n".join(lines)


def format_rows(rows: list[dict[str, Any]], max_rows: int = 10) -> str:
    """Format data rows into a readable table string."""
    if not rows:
        return "(no data)"
    display = rows[:max_rows]
    try:
        return json.dumps(display, indent=2, default=str)
    except Exception:
        return str(display)


def truncate(text: str, max_len: int = 2000) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def safe_json_parse(text: str) -> dict[str, Any] | None:
    """Try to parse JSON from LLM output, stripping markdown fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Remove ```json ... ``` fences
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Failed to parse JSON from LLM output: %s", truncate(cleaned, 200))
        return None
