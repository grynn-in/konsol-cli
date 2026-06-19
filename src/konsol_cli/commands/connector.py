"""Connector registry commands."""
from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.json import JSON

from konsol_cli.commands.common import get_backend
from konsol_cli.output import print_rows

app = typer.Typer(help="Manage ERP connector registry.")
console = Console()


@app.command("list")
def list_connectors(
    ctx: typer.Context,
    enabled: bool | None = typer.Option(
        None,
        "--enabled/--disabled",
        help="Filter by enabled flag.",
    ),
) -> None:
    """List connectors from the konsol site."""
    rows = get_backend(ctx).list_connectors(enabled=enabled)
    print_rows(
        console,
        "Connectors",
        rows,
        [
            ("ID", "name"),
            ("Name", "connector_name"),
            ("ERP Type", "erp_type"),
            ("Enabled", "enabled"),
            ("Sync Status", "last_sync_status"),
            ("Adapter", "dbt_adapter_prefix"),
        ],
    )


@app.command("show")
def show_connector(
    ctx: typer.Context,
    name: str = typer.Argument(help="Connector ID, e.g. CONN-00001."),
) -> None:
    """Show a single connector."""
    row = get_backend(ctx).get_connector(name)
    console.print(JSON(json.dumps(row)))


@app.command("create")
def create_connector(
    ctx: typer.Context,
    connector_name: str = typer.Option(..., "--name", help="Display name."),
    erp_type: str = typer.Option(
        ...,
        "--erp-type",
        help="d365_fo, d365_bc, sap_s4, sap_ecc, sap_b1, or erpnext.",
    ),
    airbyte_connection_id: str | None = typer.Option(None, "--airbyte-connection-id"),
    enabled: bool = typer.Option(True, "--enabled/--disabled"),
    entity_id: list[str] = typer.Option([], "--entity-id", help="Legal entity ID (repeatable)."),
) -> None:
    """Create or update a connector (matched by --name)."""
    spec = {
        "connector_name": connector_name,
        "erp_type": erp_type,
        "enabled": enabled,
    }
    if airbyte_connection_id:
        spec["airbyte_connection_id"] = airbyte_connection_id
    if entity_id:
        spec["legal_entities"] = entity_id

    result = get_backend(ctx).upsert_connector(spec)
    action = "created" if result.get("created") else "updated"
    connector = result["connector"]
    console.print(
        f"[green]{action.title()}[/green] connector [bold]{connector['name']}[/bold] "
        f"({connector['connector_name']}, enabled={connector['enabled']})"
    )