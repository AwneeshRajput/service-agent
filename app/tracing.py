"""LangSmith tracing setup.

LangGraph and the LangSmith SDK read their settings from environment variables,
but pydantic-settings only loads .env into the Settings object. configure_tracing()
copies the values across so tracing works whether the keys live in .env or in
the real environment. Call it before the graph runs (app.main does this at import).
"""

import os
from typing import Any

from app.config import get_settings


def configure_tracing() -> bool:
    settings = get_settings()
    enabled = settings.langsmith_tracing and bool(settings.langsmith_api_key)
    os.environ["LANGSMITH_TRACING"] = "true" if enabled else "false"
    if enabled:
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
        os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint
    return enabled


def flush_traces() -> None:
    """Send any traces still queued in memory. Called on server shutdown."""
    from langchain_core.tracers.langchain import wait_for_all_tracers
    from langsmith.run_trees import get_cached_client

    wait_for_all_tracers()
    get_cached_client().flush()


def drop_db(inputs: dict[str, Any]) -> dict[str, Any]:
    """Hide the SQLAlchemy session from traced tool inputs."""
    return {key: value for key, value in inputs.items() if key != "db"}
