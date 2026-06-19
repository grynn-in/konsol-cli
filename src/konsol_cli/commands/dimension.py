"""Dimension commands."""
from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.json import JSON

from konsol_cli.commands.common import get_backend, status_option
from konsol_cli.output import print_rows

app = typer.Typer(help="Manage EPM dimensions.")
console = Console()


@app.command("list")
def list_dimensions(
    ctx: typer.Context,
    status: str | None = status_option(),
) -> None:
    """List dimensions from the konsol site."""
    rows = get_backend(ctx).list_dimensions(status=status)
    print_rows(
        console,
        "Dimensions",
        rows,
        [
            ("Name", "dimension_name"),
            ("Label", "label"),
            ("Source Column", "source_column"),
            ("Status", "status"),
            ("In Budget", "in_budget"),
        ],
    )


@app.command("show")
def show_dimension(
    ctx: typer.Context,
    name: str = typer.Argument(help="Dimension name, e.g. dim_cost_center."),
) -> None:
    """Show a single dimension."""
    row = get_backend(ctx).get_dimension(name)
    console.print(JSON(json.dumps(row)))


@app.command("create")
def create_dimension(
    ctx: typer.Context,
    name: str = typer.Argument(help="Dimension name, e.g. dim_project."),
    source_column: str = typer.Option(..., "--source-column", help="ERP source field name."),
    label: str = typer.Option(..., "--label", help="Human-readable label."),
    cube_type: str = typer.Option("string", "--cube-type", help="string or number."),
    in_budget: bool = typer.Option(False, "--in-budget/--no-in-budget"),
    allocation_role: str | None = typer.Option(None, "--allocation-role"),
    permission_doctype: str | None = typer.Option(None, "--permission-doctype"),
    publish: bool = typer.Option(
        False,
        "--publish",
        help="Publish immediately after save (triggers schema apply + build request).",
    ),
) -> None:
    """Create or update a dimension as Draft unless --publish is passed."""
    spec = {
        "dimension_name": name,
        "source_column": source_column,
        "label": label,
        "cube_type": cube_type,
        "in_budget": in_budget,
    }
    if allocation_role:
        spec["allocation_role"] = allocation_role
    if permission_doctype:
        spec["permission_doctype"] = permission_doctype

    result = get_backend(ctx).upsert_dimension(spec, publish=publish)
    action = "created" if result.get("created") else "updated"
    console.print(
        f"[green]{action.title()}[/green] dimension [bold]{name}[/bold] "
        f"(status={result['dimension']['status']})"
    )
    if result.get("published"):
        console.print("[yellow]Published — schema apply + build request triggered.[/yellow]")


@app.command("publish")
def publish_dimension(
    ctx: typer.Context,
    name: str = typer.Argument(help="Dimension name to publish."),
) -> None:
    """Publish a dimension and trigger schema apply + governed rebuild."""
    result = get_backend(ctx).publish_dimension(name)
    console.print(
        f"[green]Published[/green] dimension [bold]{name}[/bold] "
        f"(status={result['dimension']['status']})"
    )
    console.print("[yellow]Schema apply + build request triggered.[/yellow]")