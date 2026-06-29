"""MCP server exposing konsol.cli_api methods as tools."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml

from konsol_cli.backends.api import ApiBackend
from konsol_cli.settings import Settings
from konsol_mcp.responses import format_mcp_response

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


# Common keys used to name a doc across the konsol doctypes, in priority order.
_NAME_KEYS = (
    "name",
    "dimension_name",
    "measure_name",
    "fact_name",
    "connector_name",
)

# Note attached to publish/unpublish/apply mutations: these go through the
# backend's governed methods, which respect the konsol publish gates.
_PUBLISH_GATE_NOTE = (
    "Routed through the konsol publish gate; a governed dbt rebuild may be queued."
)


def _doc_name(*candidates: Any) -> str | None:
    """Best-effort extraction of a human doc name from backend payloads/specs."""
    for candidate in candidates:
        if isinstance(candidate, dict):
            for key in _NAME_KEYS:
                value = candidate.get(key)
                if value:
                    return str(value)
        elif isinstance(candidate, str) and candidate:
            return candidate
    return None


def _read_list(data: Any, message: str) -> str:
    """Envelope for a list read: payload goes into ``affected_objects``."""
    objects = data if isinstance(data, list) else [data]
    return _json(format_mcp_response("success", message, affected_objects=objects))


def _read_diff(data: Any, message: str) -> str:
    """Envelope for a structured read (diff/export/status): payload into ``diff``."""
    return _json(
        format_mcp_response(
            "success", message, diff=data if isinstance(data, dict) else {"value": data}
        )
    )


def _mutated(
    name: str | None,
    message: str,
    result: Any,
    *,
    warnings: list | None = None,
) -> str:
    """Envelope for a mutation: ``affected_objects=[name]``, raw result in ``diff``."""
    return _json(
        format_mcp_response(
            "success",
            message,
            affected_objects=[name] if name is not None else [],
            diff=result if isinstance(result, dict) else None,
            warnings=warnings,
        )
    )


@mcp.tool()
def list_dimensions(status: str | None = None) -> str:
    """List Dimension docs. Optional status: Draft, Published, or Inactive."""
    data = _backend().list_dimensions(status=status)
    return _read_list(data, f"Listed {len(data)} dimension(s).")


@mcp.tool()
def get_dimension(name: str) -> str:
    """Get a single Dimension doc by name."""
    return _read_list(_backend().get_dimension(name), f"Fetched dimension {name}.")


@mcp.tool()
def upsert_dimension(spec: dict[str, Any], publish: bool = False) -> str:
    """Create or update a Dimension doc."""
    result = _backend().upsert_dimension(spec, publish=publish)
    warnings = [_PUBLISH_GATE_NOTE] if publish else None
    return _mutated(
        _doc_name(result, spec), "Upserted dimension.", result, warnings=warnings
    )


@mcp.tool()
def publish_dimension(name: str) -> str:
    """Publish a Dimension doc and request a governed rebuild."""
    result = _backend().publish_dimension(name)
    return _mutated(name, f"Published dimension {name}.", result, warnings=[_PUBLISH_GATE_NOTE])


@mcp.tool()
def unpublish_dimension(name: str) -> str:
    """Unpublish a Dimension doc and request a governed rebuild."""
    result = _backend().unpublish_dimension(name)
    return _mutated(name, f"Unpublished dimension {name}.", result, warnings=[_PUBLISH_GATE_NOTE])


@mcp.tool()
def list_measures(status: str | None = None) -> str:
    """List Measure docs. Optional status: Draft, Published, or Inactive."""
    data = _backend().list_measures(status=status)
    return _read_list(data, f"Listed {len(data)} measure(s).")


@mcp.tool()
def get_measure(name: str) -> str:
    """Get a single Measure doc by name."""
    return _read_list(_backend().get_measure(name), f"Fetched measure {name}.")


@mcp.tool()
def upsert_measure(spec: dict[str, Any], publish: bool = False) -> str:
    """Create or update a Measure doc."""
    result = _backend().upsert_measure(spec, publish=publish)
    warnings = [_PUBLISH_GATE_NOTE] if publish else None
    return _mutated(
        _doc_name(result, spec), "Upserted measure.", result, warnings=warnings
    )


@mcp.tool()
def publish_measure(name: str) -> str:
    """Publish a Measure doc and request a governed rebuild."""
    result = _backend().publish_measure(name)
    return _mutated(name, f"Published measure {name}.", result, warnings=[_PUBLISH_GATE_NOTE])


@mcp.tool()
def unpublish_measure(name: str) -> str:
    """Unpublish a Measure doc and request a governed rebuild."""
    result = _backend().unpublish_measure(name)
    return _mutated(name, f"Unpublished measure {name}.", result, warnings=[_PUBLISH_GATE_NOTE])


@mcp.tool()
def list_fact_tables(status: str | None = None) -> str:
    """List Fact Table docs. Optional status: Draft, Published, or Inactive."""
    data = _backend().list_fact_tables(status=status)
    return _read_list(data, f"Listed {len(data)} fact table(s).")


@mcp.tool()
def get_fact_table(name: str) -> str:
    """Get a single Fact Table doc by fact_name."""
    return _read_list(_backend().get_fact_table(name), f"Fetched fact table {name}.")


@mcp.tool()
def upsert_fact_table(spec: dict[str, Any], publish: bool = False) -> str:
    """Create or update a Fact Table doc."""
    result = _backend().upsert_fact_table(spec, publish=publish)
    warnings = [_PUBLISH_GATE_NOTE] if publish else None
    return _mutated(
        _doc_name(result, spec), "Upserted fact table.", result, warnings=warnings
    )


@mcp.tool()
def publish_fact_table(name: str) -> str:
    """Publish a Fact Table doc and request a governed rebuild."""
    result = _backend().publish_fact_table(name)
    return _mutated(name, f"Published fact table {name}.", result, warnings=[_PUBLISH_GATE_NOTE])


@mcp.tool()
def unpublish_fact_table(name: str) -> str:
    """Unpublish a Fact Table doc and request a governed rebuild."""
    result = _backend().unpublish_fact_table(name)
    return _mutated(name, f"Unpublished fact table {name}.", result, warnings=[_PUBLISH_GATE_NOTE])


@mcp.tool()
def list_connectors(enabled: bool | None = None) -> str:
    """List Connector docs. Optional enabled filter."""
    data = _backend().list_connectors(enabled=enabled)
    return _read_list(data, f"Listed {len(data)} connector(s).")


@mcp.tool()
def get_connector(name: str) -> str:
    """Get a single Connector doc by ID (CONN-.#####)."""
    return _read_list(_backend().get_connector(name), f"Fetched connector {name}.")


@mcp.tool()
def upsert_connector(spec: dict[str, Any]) -> str:
    """Create or update a Connector doc."""
    result = _backend().upsert_connector(spec)
    return _mutated(_doc_name(result, spec), "Upserted connector.", result)


@mcp.tool()
def delete_connector(name: str) -> str:
    """Delete a Connector doc by ID (CONN-...) or connector_name."""
    result = _backend().delete_connector(name)
    return _mutated(name, f"Deleted connector {name}.", result)


@mcp.tool()
def test_connector_writeback(name: str) -> str:
    """Validate a Connector's write-back credentials against the live ERP."""
    result = _backend().test_connector_writeback(name)
    return _mutated(name, f"Tested write-back for connector {name}.", result)


@mcp.tool()
def provision_connector_airbyte(name: str) -> str:
    """Test extract creds and provision Airbyte source + connection for a Connector."""
    result = _backend().provision_connector_airbyte(name)
    return _mutated(name, f"Provisioned Airbyte for connector {name}.", result)


@mcp.tool()
def list_erp_sources() -> str:
    """Return enabled ERP source keys (dbt vars.erp_sources)."""
    return _read_diff(_backend().list_erp_sources(), "Listed enabled ERP sources.")


@mcp.tool()
def apply_schema(run_dbt: bool = False) -> str:
    """Apply schema from published config (dbt vars, ClickHouse DDL, budget fields)."""
    result = _backend().apply_schema(run_dbt=run_dbt)
    return _mutated(
        None,
        "Applied schema from published config.",
        result,
        warnings=[_PUBLISH_GATE_NOTE],
    )


@mcp.tool()
def get_schema_status() -> str:
    """Return registry counts and pipeline build request status."""
    return _read_diff(_backend().get_schema_status(), "Fetched schema status.")


@mcp.tool()
def export_config(status: str | None = None) -> str:
    """Export dimensions, measures, fact tables, and connectors as a portable bundle."""
    return _read_diff(_backend().export_config(status=status), "Exported config bundle.")


@mcp.tool()
def apply_config(spec: dict[str, Any], publish: bool = False, prune: bool = False) -> str:
    """Apply a config bundle (dimensions, measures, fact tables, connectors)."""
    result = _backend().apply_config(spec, publish=publish, prune=prune)
    warnings = [_PUBLISH_GATE_NOTE] if publish else None
    return _mutated(
        _doc_name(result), "Applied config bundle.", result, warnings=warnings
    )


@mcp.tool()
def diff_config(spec: dict[str, Any], status: str | None = None) -> str:
    """Diff a config bundle against the live site."""
    return _read_diff(_backend().diff_config(spec, status=status), "Diffed config bundle.")


# --- M3: GitOps composite ---------------------------------------------------

# Sections of a config diff/bundle, in display order.
_DIFF_SECTIONS = ("dimensions", "measures", "fact_tables", "connectors")

def _load_bundle_file(path: Path) -> dict[str, Any]:
    """Load a config bundle from a YAML/JSON file (mirrors commands/config.py).

    Raises ``ValueError`` if the file cannot be parsed into a config object;
    callers translate that into a ``validation_failed`` envelope.
    """
    text = path.read_text()
    if path.suffix in {".yaml", ".yml"}:
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a config object (got {type(data).__name__}).")
    return data

def _diff_key(item: Any) -> Any:
    """Extract the entity key from a diff item (dict with ``key``, or a string)."""
    if isinstance(item, dict):
        return item.get("key")
    return item

def _bundle_affected_objects(diff: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten a config diff into the objects that would be touched."""
    objects: list[dict[str, Any]] = []
    for section in _DIFF_SECTIONS:
        data = diff.get(section) or {}
        for change in ("added", "modified", "only_on_site"):
            for item in data.get(change, []):
                objects.append({"kind": section, "key": _diff_key(item), "change": change})
    return objects

def _bundle_impact_summary(diff: dict[str, Any]) -> str:
    """Human-readable per-section change counts for a config diff."""
    parts: list[str] = []
    for section in _DIFF_SECTIONS:
        data = diff.get(section) or {}
        added = len(data.get("added", []))
        modified = len(data.get("modified", []))
        only_on_site = len(data.get("only_on_site", []))
        if added or modified or only_on_site:
            parts.append(f"{section}: +{added} ~{modified} -{only_on_site}")
    return "; ".join(parts) if parts else "No changes detected."

@mcp.tool()
def apply_model_from_gitops(
    bundle_path: str,
    dry_run: bool = True,
    publish: bool = False,
    prune: bool = False,
) -> str:
    """Apply a GitOps config bundle file to the konsol site (composite).

    Loads the YAML/JSON bundle at ``bundle_path``, diffs it against the live
    site, and either previews (``dry_run``, the default) or applies it. This
    composes the ``diff_config`` / ``apply_config`` backend primitives and
    routes mutations through the konsol publish gate; it never bypasses them.

    Args:
        bundle_path: Path to a YAML or JSON config bundle file.
        dry_run: When True (default) only preview the diff — no mutation.
        publish: When applying, publish each entity after save.
        prune: When applying, remove site entities absent from the bundle.

    Returns:
        The serialized response envelope. ``validation_failed`` on a missing,
        empty, or unparseable bundle (never raises); ``dry_run`` for a
        preview; ``success`` after a real apply.
    """
    if not bundle_path or not str(bundle_path).strip():
        return _json(
            format_mcp_response(
                "validation_failed",
                "No bundle_path provided.",
                warnings=["bundle_path is required."],
            )
        )

    path = Path(str(bundle_path).strip())
    if not path.is_file():
        return _json(
            format_mcp_response(
                "validation_failed",
                f"Bundle path not found: {bundle_path}.",
                warnings=[f"{bundle_path} is not a readable file."],
            )
        )

    try:
        bundle = _load_bundle_file(path)
    except Exception as exc:  # noqa: BLE001 - surface any parse error as validation
        return _json(
            format_mcp_response(
                "validation_failed",
                f"Could not parse bundle {bundle_path}.",
                warnings=[str(exc)],
            )
        )

    if not bundle:
        return _json(
            format_mcp_response(
                "validation_failed",
                f"Bundle {bundle_path} is empty.",
                warnings=["Bundle contains no config objects."],
            )
        )

    backend = _backend()
    diff = backend.diff_config(bundle)
    affected = _bundle_affected_objects(diff)
    impact = _bundle_impact_summary(diff)

    if dry_run:
        return _json(
            format_mcp_response(
                "dry_run",
                f"Previewed {bundle_path}; no changes applied.",
                affected_objects=affected,
                diff=diff,
                impact_summary=impact,
                next_steps=["re-run with dry_run=False to apply"],
            )
        )

    summary = backend.apply_config(bundle, publish=publish, prune=prune)
    warnings = [_PUBLISH_GATE_NOTE] if publish else None
    return _json(
        format_mcp_response(
            "success",
            f"Applied {bundle_path}.",
            affected_objects=affected,
            diff=summary,
            impact_summary=impact,
            warnings=warnings,
            next_steps=["publish_model_changes to rebuild"],
        )
    )

def main() -> None:
    mcp.run()