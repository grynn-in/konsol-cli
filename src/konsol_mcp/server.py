"""MCP server exposing konsol.cli_api methods as tools.

konsol keeps five endpoints for this client (konsol#379, 5 Nov 2026): config
export/diff/apply and schema apply/status. Every tool here calls only those.
Dimension, measure, dataset and connector work is done in the Frappe Desk or
with frappectl.
"""
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
def apply_schema(run_dbt: bool = False) -> str:
    """Apply schema from published config (dbt vars, ClickHouse DDL, budget fields)."""
    result = _backend().apply_schema(run_dbt=run_dbt)
    message = "Applied schema from published config."
    approval = result.get("build_approval") if isinstance(result, dict) else None
    if approval:
        # konsol#170: requested, not run; a full refresh may wait for review.
        state = result.get("build_approval_state") or "state unknown"
        message += f" Requested a governed build: Build Approval {approval} ({state})."
    return _mutated(
        None,
        message,
        result,
        warnings=[_PUBLISH_GATE_NOTE],
    )


@mcp.tool()
def get_schema_status() -> str:
    """Return registry counts and pipeline build request status."""
    return _read_diff(_backend().get_schema_status(), "Fetched schema status.")


@mcp.tool()
def export_config(status: str | None = None) -> str:
    """Export dimensions, measures, datasets, and connectors as a portable bundle."""
    return _read_diff(_backend().export_config(status=status), "Exported config bundle.")


@mcp.tool()
def apply_config(spec: dict[str, Any], publish: bool = False, prune: bool = False) -> str:
    """Apply a config bundle (dimensions, measures, datasets, connectors)."""
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

    try:
        summary = backend.apply_config(bundle, publish=publish, prune=prune)
    except Exception as exc:  # noqa: BLE001 - surface backend failure as error envelope
        return _json(
            format_mcp_response(
                "error",
                f"Failed to apply {bundle_path}; the site may hold partial changes.",
                affected_objects=affected,
                diff=diff,
                impact_summary=impact,
                warnings=[f"apply_config failed: {exc}"],
                next_steps=[
                    "inspect the konsol site for partially-applied changes, then re-run"
                ],
            )
        )
    warnings = [_PUBLISH_GATE_NOTE] if publish else None
    return _json(
        format_mcp_response(
            "success",
            f"Applied {bundle_path}.",
            affected_objects=affected,
            diff=summary,
            impact_summary=impact,
            warnings=warnings,
            next_steps=["get_schema_status to follow the build requests"],
        )
    )

# --- M7: preview_impact composite (read-only) -------------------------------

# Limitation surfaced on every preview: the backend has no transitive lineage
# endpoint, so impact is approximated from the config diff + schema status.
_IMPACT_LIMITATION_NOTE = (
    "Impact derived from config diff + schema status; no transitive lineage / "
    "blast-radius endpoint is available, so downstream effects are approximate."
)


def _published_downstream_count(status: Any) -> int | None:
    """Best-effort count of currently Published models from a schema-status payload.

    Walks the (opaque) schema-status structure and sums any integer values keyed
    by ``"Published"`` (case-insensitive). Returns ``None`` when no such counts
    are present, so callers can omit the note rather than report a misleading 0.
    """
    found = False
    total = 0

    def _walk(obj: Any) -> None:
        nonlocal found, total
        if isinstance(obj, dict):
            for key, value in obj.items():
                if (
                    isinstance(key, str)
                    and key.lower() == "published"
                    and isinstance(value, int)
                    and not isinstance(value, bool)
                ):
                    found = True
                    total += value
                else:
                    _walk(value)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(status)
    return total if found else None


@mcp.tool()
def preview_impact(
    bundle_path: str | None = None,
    names: list[str] | None = None,
) -> str:
    """Preview the downstream blast radius of a proposed model change (read-only).

    Combines the read-only ``diff_config`` (what a bundle would change) and
    ``get_schema_status`` (current registry / published counts + pipeline
    status) primitives to report the objects a change would touch and how many
    models are currently published downstream. This tool **never mutates,
    publishes, or applies anything** — it always returns ``status="dry_run"``.

    At least one input is required:

    - ``bundle_path``: a YAML/JSON config bundle file to diff against the site.
    - ``names``: an explicit list of model names to assess.

    The backend exposes no true transitive-lineage endpoint, so the impact is
    approximated from the diff + schema status; that limitation is always noted
    in ``warnings``.

    Args:
        bundle_path: Optional path to a YAML or JSON config bundle file.
        names: Optional explicit list of model names to assess.

    Returns:
        The serialized response envelope. ``validation_failed`` when no input is
        given, ``names`` is not a list, or ``bundle_path`` is not a readable /
        parseable file (never raises); otherwise ``dry_run`` with the touched
        objects in ``affected_objects`` and a human ``impact_summary``.
    """
    if names is not None and not isinstance(names, list):
        return _json(
            format_mcp_response(
                "validation_failed",
                "names must be a list of model names.",
                warnings=[f"Expected a list for names, got {type(names).__name__}."],
            )
        )

    bundle_path_str = str(bundle_path).strip() if bundle_path else ""
    if not bundle_path_str and not names:
        return _json(
            format_mcp_response(
                "validation_failed",
                "Provide bundle_path and/or names to preview.",
                warnings=["At least one of bundle_path or names is required."],
            )
        )

    bundle: dict[str, Any] | None = None
    if bundle_path_str:
        path = Path(bundle_path_str)
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
    affected: list[dict[str, Any]] = []
    impact_parts: list[str] = []
    diff_payload: dict[str, Any] = {}

    if bundle is not None:
        config_diff = backend.diff_config(bundle)
        affected.extend(_bundle_affected_objects(config_diff))
        impact_parts.append(_bundle_impact_summary(config_diff))
        diff_payload["config_diff"] = config_diff

    if names:
        for name in names:
            affected.append({"kind": "model", "key": name, "change": "assess"})
        impact_parts.append(f"{len(names)} named model(s) to assess")

    schema_status = backend.get_schema_status()
    diff_payload["schema_status"] = schema_status
    published = _published_downstream_count(schema_status)
    if published is not None:
        impact_parts.append(f"{published} published model(s) currently downstream")

    impact = "; ".join(part for part in impact_parts if part) or "No impact detected."

    return _json(
        format_mcp_response(
            "dry_run",
            f"Previewed impact for {len(affected)} object(s); nothing changed.",
            affected_objects=affected,
            diff=diff_payload,
            impact_summary=impact,
            warnings=[_IMPACT_LIMITATION_NOTE],
            next_steps=[
                "apply_model_from_gitops to apply the bundle",
            ],
        )
    )


def main() -> None:
    mcp.run()