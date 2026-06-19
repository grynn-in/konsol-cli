"""Measure commands."""
from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.json import JSON

from konsol_cli.commands.common import get_backend, status_option
from konsol_cli.output import print_rows

app = typer.Typer(help="Manage EPM measures.")
console = Console()


@app.command("list")
def list_measures(
    ctx: typer.Context,
    status: str | None = status_option(),
) -> None:
    """List measures from the konsol site."""
    rows = get_backend(ctx).list_measures(status=status)
    print_rows(
        console,
        "Measures",
        rows,
        [
            ("Name", "measure_name"),
            ("Label", "label"),
            ("Expression", "expression"),
            ("Cube Type", "cube_type"),
            ("Status", "status"),
        ],
    )


@app.command("show")
def show_measure(
    ctx: typer.Context,
    name: str = typer.Argument(help="Measure name, e.g. period_net_amount."),
) -> None:
    """Show a single measure."""
    row = get_backend(ctx).get_measure(name)
    console.print(JSON(json.dumps(row)))


@app.command("create")
def create_measure(
    ctx: typer.Context,
    name: str = typer.Argument(help="Measure name, e.g. period_headcount."),
    expression: str = typer.Option(..., "--expression", help="SQL expression."),
    label: str = typer.Option(..., "--label", help="Human-readable label."),
    cube_type: str = typer.Option("sum", "--cube-type", help="sum, count, or avg."),
    publish: bool = typer.Option(
        False,
        "--publish",
        help="Publish immediately after save (triggers schema apply + build request).",
    ),
) -> None:
    """Create or update a measure as Draft unless --publish is passed."""
    spec = {
        "measure_name": name,
        "expression": expression,
        "label": label,
        "cube_type": cube_type,
    }

    result = get_backend(ctx).upsert_measure(spec, publish=publish)
    action = "created" if result.get("created") else "updated"
    console.print(
        f"[green]{action.title()}[/green] measure [bold]{name}[/bold] "
        f"(status={result['measure']['status']})"
    )
    if result.get("published"):
        console.print("[yellow]Published — schema apply + build request triggered.[/yellow]")


@app.command("publish")
def publish_measure(
    ctx: typer.Context,
    name: str = typer.Argument(help="Measure name to publish."),
) -> None:
    """Publish a measure and trigger schema apply + governed rebuild."""
    result = get_backend(ctx).publish_measure(name)
    console.print(
        f"[green]Published[/green] measure [bold]{name}[/bold] "
        f"(status={result['measure']['status']})"
    )
    console.print("[yellow]Schema apply + build request triggered.[/yellow]")