"""MCP server exposing konsol.cli_api methods as tools."""
from __future__ import annotations

import json
import os
from typing import Any

from konsol_cli.backends.api import ApiBackend
from konsol_cli.settings import Settings

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - optional dependency
    raise SystemExit(
        "konsol-mcp requires the mcp package. Install with: pip install 'konsol-cli[mcp]'"
    ) from exc

mcp = FastMCP("konsol")


def _backend() -> ApiBackend:
    settings = Settings.from_env(
        backend="api",
        site=os.environ.get("KONSOL_SITE", "konsolidat.local"),
        url=os.environ.get("KONSOL_URL"),
        api_key=os.environ.get("KONSOL_API_KEY"),
        api_secret=os.environ.get("KONSOL_API_SECRET"),
        compose_file=None,
        compose_service="frappe_backend",
    )
    return ApiBackend(settings)


def _json(data: Any) -> str:
    return json.dumps(data, indent=2, default=str)


@mcp.tool()
def list_dimensions(status: str | None = None) -> str:
    """List Dimension docs. Optional status: Draft, Published, or Inactive."""
    return _json(_backend().list_dimensions(status=status))


@mcp.tool()
def get_dimension(name: str) -> str:
    """Get a single Dimension doc by name."""
    return _json(_backend().get_dimension(name))


@mcp.tool()
def upsert_dimension(spec: dict[str, Any], publish: bool = False) -> str:
    """Create or update a Dimension doc."""
    return _json(_backend().upsert_dimension(spec, publish=publish))


@mcp.tool()
def publish_dimension(name: str) -> str:
    """Publish a Dimension doc and request a governed rebuild."""
    return _json(_backend().publish_dimension(name))


@mcp.tool()
def list_measures(status: str | None = None) -> str:
    """List Measure docs. Optional status: Draft, Published, or Inactive."""
    return _json(_backend().list_measures(status=status))


@mcp.tool()
def get_measure(name: str) -> str:
    """Get a single Measure doc by name."""
    return _json(_backend().get_measure(name))


@mcp.tool()
def upsert_measure(spec: dict[str, Any], publish: bool = False) -> str:
    """Create or update a Measure doc."""
    return _json(_backend().upsert_measure(spec, publish=publish))


@mcp.tool()
def publish_measure(name: str) -> str:
    """Publish a Measure doc and request a governed rebuild."""
    return _json(_backend().publish_measure(name))


@mcp.tool()
def list_fact_tables(status: str | None = None) -> str:
    """List Fact Table docs. Optional status: Draft, Published, or Inactive."""
    return _json(_backend().list_fact_tables(status=status))


@mcp.tool()
def get_fact_table(name: str) -> str:
    """Get a single Fact Table doc by fact_name."""
    return _json(_backend().get_fact_table(name))


@mcp.tool()
def upsert_fact_table(spec: dict[str, Any], publish: bool = False) -> str:
    """Create or update a Fact Table doc."""
    return _json(_backend().upsert_fact_table(spec, publish=publish))


@mcp.tool()
def publish_fact_table(name: str) -> str:
    """Publish a Fact Table doc and request a governed rebuild."""
    return _json(_backend().publish_fact_table(name))


@mcp.tool()
def unpublish_fact_table(name: str) -> str:
    """Unpublish a Fact Table doc and request a governed rebuild."""
    return _json(_backend().unpublish_fact_table(name))


@mcp.tool()
def list_connectors(enabled: bool | None = None) -> str:
    """List Connector docs. Optional enabled filter."""
    return _json(_backend().list_connectors(enabled=enabled))


@mcp.tool()
def get_connector(name: str) -> str:
    """Get a single Connector doc by ID (CONN-.#####)."""
    return _json(_backend().get_connector(name))


@mcp.tool()
def upsert_connector(spec: dict[str, Any]) -> str:
    """Create or update a Connector doc."""
    return _json(_backend().upsert_connector(spec))


@mcp.tool()
def list_erp_sources() -> str:
    """Return enabled ERP source keys (dbt vars.erp_sources)."""
    return _json(_backend().list_erp_sources())


@mcp.tool()
def apply_schema(run_dbt: bool = False) -> str:
    """Apply schema from published config (dbt vars, ClickHouse DDL, budget fields)."""
    return _json(_backend().apply_schema(run_dbt=run_dbt))


@mcp.tool()
def get_schema_status() -> str:
    """Return registry counts and pipeline build request status."""
    return _json(_backend().get_schema_status())


@mcp.tool()
def export_config(status: str | None = None) -> str:
    """Export dimensions, measures, and fact tables as a portable bundle."""
    return _json(_backend().export_config(status=status))


@mcp.tool()
def apply_config(spec: dict[str, Any], publish: bool = False) -> str:
    """Apply a config bundle (dimensions, measures, fact tables)."""
    return _json(_backend().apply_config(spec, publish=publish))


@mcp.tool()
def diff_config(spec: dict[str, Any], status: str | None = None) -> str:
    """Diff a config bundle against the live site."""
    return _json(_backend().diff_config(spec, status=status))


def main() -> None:
    mcp.run()