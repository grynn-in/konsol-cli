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
            next_steps=["publish_model_changes to rebuild"],
        )
    )

# --- M4: publish_model_changes composite ------------------------------------

# Model doctypes this composite can publish, in display order.
_MODEL_KINDS = ("dimension", "measure", "fact_table")

# Per-kind backend method names for draft discovery and publishing.
_LIST_BY_KIND = {
    "dimension": "list_dimensions",
    "measure": "list_measures",
    "fact_table": "list_fact_tables",
}
_PUBLISH_BY_KIND = {
    "dimension": "publish_dimension",
    "measure": "publish_measure",
    "fact_table": "publish_fact_table",
}


@mcp.tool()
def publish_model_changes(
    names: list[str] | None = None,
    kinds: list[str] | None = None,
    dry_run: bool = True,
) -> str:
    """Publish Draft model changes through the konsol publish gate (composite).

    Discovers the models that need publishing — Draft Dimensions, Measures,
    and Fact Tables (optionally narrowed by ``kinds`` and/or an explicit
    ``names`` allow-list) — and either previews them (``dry_run``, the
    default) or publishes each one and applies the schema once. This composes
    the ``list_*`` / ``publish_*`` / ``apply_schema`` backend primitives and
    routes every mutation through the governed publish gate; it never bypasses
    it.

    Args:
        names: Optional allow-list of model names to publish. When given,
            only discovered Draft models whose name is in this list are
            published.
        kinds: Optional subset of ``{"dimension", "measure", "fact_table"}``
            to limit discovery to those doctypes.
        dry_run: When True (default) only list the would-be-published models —
            no mutation.

    Returns:
        The serialized response envelope. ``validation_failed`` on a bad
        ``names``/``kinds`` argument (never raises); ``dry_run`` for a
        preview; ``success`` after publishing (or when there is nothing to
        publish).
    """
    if names is not None and not isinstance(names, list):
        return _json(
            format_mcp_response(
                "validation_failed",
                "names must be a list of model names.",
                warnings=[f"Expected a list for names, got {type(names).__name__}."],
            )
        )

    if kinds is not None:
        if not isinstance(kinds, list):
            return _json(
                format_mcp_response(
                    "validation_failed",
                    "kinds must be a list.",
                    warnings=[f"Expected a list for kinds, got {type(kinds).__name__}."],
                )
            )
        invalid = [k for k in kinds if k not in _MODEL_KINDS]
        if invalid:
            return _json(
                format_mcp_response(
                    "validation_failed",
                    "Unknown model kind(s) requested.",
                    warnings=[
                        f"Invalid kinds {invalid}; valid kinds are {list(_MODEL_KINDS)}."
                    ],
                )
            )

    selected_kinds = tuple(kinds) if kinds else _MODEL_KINDS
    backend = _backend()

    # Discover Draft models for each selected kind.
    discovered: list[dict[str, Any]] = []
    for kind in selected_kinds:
        docs = getattr(backend, _LIST_BY_KIND[kind])(status="Draft")
        for doc in docs or []:
            name = _doc_name(doc)
            if name is not None:
                discovered.append({"kind": kind, "key": name})

    if names is not None:
        wanted = set(names)
        discovered = [item for item in discovered if item["key"] in wanted]

    if not discovered:
        return _json(
            format_mcp_response(
                "success",
                "No Draft model changes to publish.",
                warnings=["nothing to publish"],
            )
        )

    if dry_run:
        return _json(
            format_mcp_response(
                "dry_run",
                f"{len(discovered)} model change(s) would be published.",
                affected_objects=discovered,
                next_steps=["re-run with dry_run=False to publish"],
            )
        )

    published: list[dict[str, Any]] = []
    for idx, item in enumerate(discovered):
        try:
            getattr(backend, _PUBLISH_BY_KIND[item["kind"]])(item["key"])
        except Exception as exc:  # noqa: BLE001 - record partial progress before failing
            return _json(
                format_mcp_response(
                    "error",
                    f"Published {len(published)} model change(s) before failing on "
                    f"{item['kind']} {item['key']}.",
                    affected_objects=published,
                    diff={
                        "published": published,
                        "failed": {"kind": item["kind"], "key": item["key"]},
                        "not_attempted": discovered[idx + 1 :],
                    },
                    warnings=[
                        f"publish failed for {item['kind']} {item['key']}: {exc}"
                    ],
                    next_steps=[
                        "resolve the error, then re-run to publish the remaining models"
                    ],
                )
            )
        published.append({"kind": item["kind"], "key": item["key"]})

    try:
        backend.apply_schema(run_dbt=False)
    except Exception as exc:  # noqa: BLE001 - models published but schema apply failed
        return _json(
            format_mcp_response(
                "error",
                f"Published {len(published)} model change(s) but apply_schema failed.",
                affected_objects=published,
                diff={"published": published},
                warnings=[f"apply_schema failed: {exc}"],
                next_steps=["re-run apply_schema once the error is resolved"],
            )
        )

    return _json(
        format_mcp_response(
            "success",
            f"Published {len(published)} model change(s) and applied schema.",
            affected_objects=published,
            warnings=[_PUBLISH_GATE_NOTE],
            next_steps=["apply_schema(run_dbt=True) to rebuild dbt models"],
        )
    )


# --- M5: provision_and_test_connector composite -----------------------------

def _writeback_failed(result: Any) -> bool:
    """Inspect a write-back test result for a failure signal.

    A failure is any of: a truthy ``error`` key, or an explicit falsy
    ``ok``/``success`` flag. A result without any of those signals is treated
    as a pass (so a bare ``{}`` or summary dict does not spuriously fail).
    """
    if not isinstance(result, dict):
        return False
    if result.get("error"):
        return True
    for flag in ("ok", "success"):
        if flag in result and not result[flag]:
            return True
    return False

@mcp.tool()
def provision_and_test_connector(name: str, dry_run: bool = True) -> str:
    """Provision a Connector's Airbyte source then test its write-back (composite).

    Validates that the Connector exists (via ``get_connector``), then either
    previews (``dry_run``, the default) or runs the two-step provision/test
    flow: ``provision_connector_airbyte`` followed by
    ``test_connector_writeback``. This composes the existing backend
    primitives and never bypasses provisioning/test gates.

    Args:
        name: Connector ID (``CONN-...``) or connector_name to provision/test.
        dry_run: When True (default) only preview — no provision/test call.

    Returns:
        The serialized response envelope. ``validation_failed`` when ``name``
        is blank or the connector cannot be fetched (never raises);
        ``dry_run`` for a preview; ``success`` after a clean run; ``error``
        when the write-back test reports a failure (provisioning still ran —
        the failure is surfaced in ``warnings``).
    """
    if not name or not str(name).strip():
        return _json(
            format_mcp_response(
                "validation_failed",
                "No connector name provided.",
                warnings=["name is required."],
            )
        )

    name = str(name).strip()
    backend = _backend()

    try:
        connector = backend.get_connector(name)
    except Exception as exc:  # noqa: BLE001 - missing connector => validation
        return _json(
            format_mcp_response(
                "validation_failed",
                f"Connector {name} could not be fetched.",
                warnings=[str(exc)],
            )
        )

    if not connector:
        return _json(
            format_mcp_response(
                "validation_failed",
                f"Connector {name} not found.",
                warnings=[f"No connector matches {name}."],
            )
        )

    connector_label = _doc_name(connector) or name

    if dry_run:
        return _json(
            format_mcp_response(
                "dry_run",
                f"Would provision Airbyte and test write-back for {connector_label}.",
                affected_objects=[connector_label],
                impact_summary=(
                    "provision_connector_airbyte then test_connector_writeback "
                    f"for {connector_label}"
                ),
                next_steps=["re-run with dry_run=False to provision and test"],
            )
        )

    try:
        provision_result = backend.provision_connector_airbyte(name)
    except Exception as exc:  # noqa: BLE001 - surface provision failure as error envelope
        return _json(
            format_mcp_response(
                "error",
                f"Provisioning Airbyte failed for {connector_label}.",
                affected_objects=[connector_label],
                warnings=[f"provision_connector_airbyte failed: {exc}"],
                next_steps=["fix the connector extract credentials, then re-run"],
            )
        )

    if _writeback_failed(provision_result):
        return _json(
            format_mcp_response(
                "error",
                f"Provisioning reported a failure for {connector_label}.",
                affected_objects=[connector_label],
                diff={"provision": provision_result},
                warnings=[
                    f"Provisioning failed for {connector_label}: {provision_result}"
                ],
                next_steps=["fix the connector extract credentials, then re-run"],
            )
        )

    try:
        writeback_result = backend.test_connector_writeback(name)
    except Exception as exc:  # noqa: BLE001 - provision ran but write-back test raised
        return _json(
            format_mcp_response(
                "error",
                f"Provisioned {connector_label} but the write-back test raised.",
                affected_objects=[connector_label],
                diff={"provision": provision_result},
                warnings=[f"test_connector_writeback failed: {exc}"],
                next_steps=["fix the connector write-back credentials, then re-run"],
            )
        )

    diff = {"provision": provision_result, "writeback": writeback_result}
    if _writeback_failed(writeback_result):
        return _json(
            format_mcp_response(
                "error",
                f"Provisioned {connector_label} but write-back test failed.",
                affected_objects=[connector_label],
                diff=diff,
                warnings=[
                    f"Write-back test failed for {connector_label}: {writeback_result}"
                ],
                next_steps=["fix the connector write-back credentials, then re-run"],
            )
        )

    return _json(
        format_mcp_response(
            "success",
            f"Provisioned Airbyte and verified write-back for {connector_label}.",
            affected_objects=[connector_label],
            diff=diff,
            next_steps=["run the Airbyte sync to extract data"],
        )
    )

# --- M6: onboard_new_entity composite ---------------------------------------

# Keys that may carry the entity's name in an onboarding spec, in priority order.
_ENTITY_NAME_KEYS = ("entity", "entity_name", "name")


def _entity_name(spec: dict[str, Any]) -> str | None:
    """Best-effort extraction of the entity name from an onboarding spec."""
    for key in _ENTITY_NAME_KEYS:
        value = spec.get(key)
        if value:
            return str(value)
    return None


def _entity_dimension_specs(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect dimension specs from a spec's ``dimension`` and/or ``dimensions``."""
    dims: list[dict[str, Any]] = []
    single = spec.get("dimension")
    if isinstance(single, dict):
        dims.append(single)
    listed = spec.get("dimensions")
    if isinstance(listed, list):
        dims.extend(item for item in listed if isinstance(item, dict))
    return dims


def _entity_plan(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Ordered list of objects to upsert for an entity (connector then dimensions).

    Each entry is ``{"kind": ..., "spec": ..., "key": ...}`` where ``kind`` is
    ``"connector"`` or ``"dimension"`` and ``key`` is the best-effort doc name.
    """
    plan: list[dict[str, Any]] = []
    connector = spec.get("connector")
    if isinstance(connector, dict):
        plan.append(
            {
                "kind": "connector",
                "spec": connector,
                "key": _doc_name(connector) or "new connector",
            }
        )
    for dim in _entity_dimension_specs(spec):
        plan.append(
            {
                "kind": "dimension",
                "spec": dim,
                "key": _doc_name(dim) or "new dimension",
            }
        )
    return plan


@mcp.tool()
def onboard_new_entity(spec: dict[str, Any], dry_run: bool = True) -> str:
    """Onboard a new entity: ensure its connector and dimension(s) (composite).

    Composes the ``upsert_connector`` / ``upsert_dimension`` backend primitives
    to stand up everything a new entity needs in one call. Nothing is published
    unless ``spec["publish"]`` is truthy, and even then mutations are routed
    through the governed upsert primitives — this never bypasses the publish
    gate.

    The ``spec`` is a dict describing the entity:

    - ``entity`` (required): the entity name.
    - ``connector`` (optional): a Connector spec dict to upsert.
    - ``dimension`` / ``dimensions`` (optional): one dict or a list of
      Dimension spec dicts to upsert.
    - ``publish`` (optional): when truthy, publish the upserted dimension(s).

    At least one of ``connector`` / ``dimension`` / ``dimensions`` is required.

    Args:
        spec: The entity onboarding spec described above.
        dry_run: When True (default) only preview the objects that would be
            created/updated — no upsert call.

    Returns:
        The serialized response envelope. ``validation_failed`` when ``spec``
        is not a dict, has no entity name, or describes no objects (never
        raises); ``dry_run`` for a preview; ``success`` after upserting.
    """
    if not isinstance(spec, dict):
        return _json(
            format_mcp_response(
                "validation_failed",
                "spec must be a mapping describing the entity.",
                warnings=[f"Expected a dict for spec, got {type(spec).__name__}."],
            )
        )

    entity = _entity_name(spec)
    if not entity:
        return _json(
            format_mcp_response(
                "validation_failed",
                "spec is missing an entity name.",
                warnings=["spec must include a non-empty 'entity' name."],
            )
        )

    plan = _entity_plan(spec)
    if not plan:
        return _json(
            format_mcp_response(
                "validation_failed",
                f"No objects to onboard for entity {entity}.",
                warnings=[
                    "spec must describe at least one of 'connector', "
                    "'dimension', or 'dimensions'."
                ],
            )
        )

    publish = bool(spec.get("publish"))
    affected = [{"kind": item["kind"], "key": item["key"]} for item in plan]
    impact = (
        f"{entity}: "
        + ", ".join(f"{item['kind']} {item['key']}" for item in plan)
    )

    if dry_run:
        return _json(
            format_mcp_response(
                "dry_run",
                f"Would onboard {len(plan)} object(s) for entity {entity}.",
                affected_objects=affected,
                impact_summary=impact,
                next_steps=["re-run with dry_run=False to create"],
            )
        )

    backend = _backend()
    results: dict[str, list[Any]] = {"connectors": [], "dimensions": []}
    for idx, item in enumerate(plan):
        try:
            if item["kind"] == "connector":
                results["connectors"].append(backend.upsert_connector(item["spec"]))
            else:  # dimension
                results["dimensions"].append(
                    backend.upsert_dimension(item["spec"], publish=publish)
                )
        except Exception as exc:  # noqa: BLE001 - record partial progress before failing
            applied = [{"kind": p["kind"], "key": p["key"]} for p in plan[:idx]]
            return _json(
                format_mcp_response(
                    "error",
                    f"Onboarded {idx} of {len(plan)} object(s) for entity {entity} "
                    f"before failing on {item['kind']} {item['key']}.",
                    affected_objects=applied,
                    diff={
                        "results": results,
                        "failed": {"kind": item["kind"], "key": item["key"]},
                        "not_attempted": [
                            {"kind": p["kind"], "key": p["key"]}
                            for p in plan[idx + 1 :]
                        ],
                    },
                    impact_summary=impact,
                    warnings=[
                        f"upsert failed for {item['kind']} {item['key']}: {exc}"
                    ],
                    next_steps=[
                        "resolve the error, then re-run to onboard the remaining objects"
                    ],
                )
            )

    warnings = [_PUBLISH_GATE_NOTE] if publish else None
    return _json(
        format_mcp_response(
            "success",
            f"Onboarded {len(plan)} object(s) for entity {entity}.",
            affected_objects=affected,
            diff=results,
            impact_summary=impact,
            warnings=warnings,
            next_steps=["publish_model_changes to go live"],
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
                "publish_model_changes to publish Draft models",
            ],
        )
    )


def main() -> None:
    mcp.run()