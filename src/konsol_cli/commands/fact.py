"""Dataset commands."""
from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.json import JSON

from konsol_cli.commands.common import get_backend, status_option
from konsol_cli.output import print_rows

app = typer.Typer(help="Manage EPM datasets.")
console = Console()


@app.command("list")
def list_fact_tables(
    ctx: typer.Context,
    status: str | None = status_option(),
) -> None:
    """List datasets from the konsol site."""
    rows = get_backend(ctx).list_fact_tables(status=status)
    print_rows(
        console,
        "Datasets",
        rows,
        [
            ("Name", "fact_name"),
            ("Label", "label"),
            ("Source Type", "source_type"),
            ("Scenario", "scenario_key"),
            ("ClickHouse Table", "clickhouse_table"),
            ("Status", "status"),
        ],
    )


@app.command("show")
def show_fact_table(
    ctx: typer.Context,
    name: str = typer.Argument(help="Dataset name, e.g. headcount."),
) -> None:
    """Show a single dataset."""
    row = get_backend(ctx).get_fact_table(name)
    console.print(JSON(json.dumps(row)))


@app.command("create")
def create_fact_table(
    ctx: typer.Context,
    name: str = typer.Argument(help="Dataset name, e.g. headcount."),
    label: str = typer.Option(..., "--label", help="Human-readable label."),
    source_type: str = typer.Option(
        ...,
        "--source-type",
        help="ERP GL, Budget, Statistical, or Sub-ledger.",
    ),
    clickhouse_table: str = typer.Option(
        ...,
        "--clickhouse-table",
        help="schema.table in lowercase, e.g. epm_staging.fact_headcount.",
    ),
    scenario_key: str = typer.Option(..., "--scenario-key", help="Scenario key, e.g. actuals."),
    dbt_model: str | None = typer.Option(None, "--dbt-model"),
    measure: list[str] = typer.Option([], "--measure", help="Measure name (repeatable)."),
    dimension: list[str] = typer.Option([], "--dimension", help="Dimension name (repeatable)."),
    generates_source: bool = typer.Option(
        False,
        "--generates-source/--no-generates-source",
        help="Create ClickHouse table + dbt source on publish.",
    ),
    publish: bool = typer.Option(
        False,
        "--publish",
        help="Publish immediately after save (triggers schema apply + build request).",
    ),
) -> None:
    """Create or update a fact table as Draft unless --publish is passed."""
    spec = {
        "fact_name": name,
        "label": label,
        "source_type": source_type,
        "clickhouse_table": clickhouse_table,
        "scenario_key": scenario_key,
        "generates_source": generates_source,
    }
    if dbt_model:
        spec["dbt_model"] = dbt_model
    if measure:
        spec["measures"] = measure
    if dimension:
        spec["dimensions"] = dimension

    result = get_backend(ctx).upsert_fact_table(spec, publish=publish)
    action = "created" if result.get("created") else "updated"
    console.print(
        f"[green]{action.title()}[/green] dataset [bold]{name}[/bold] "
        f"(status={result['fact_table']['status']})"
    )
    if result.get("published"):
        console.print("[yellow]Published — schema apply + build request triggered.[/yellow]")


@app.command("publish")
def publish_fact_table(
    ctx: typer.Context,
    name: str = typer.Argument(help="Dataset name to publish."),
) -> None:
    """Publish a dataset and trigger schema apply + governed rebuild."""
    result = get_backend(ctx).publish_fact_table(name)
    console.print(
        f"[green]Published[/green] dataset [bold]{name}[/bold] "
        f"(status={result['fact_table']['status']})"
    )
    console.print("[yellow]Schema apply + build request triggered.[/yellow]")


@app.command("unpublish")
def unpublish_fact_table(
    ctx: typer.Context,
    name: str = typer.Argument(help="Dataset name to unpublish."),
) -> None:
    """Unpublish a dataset (Inactive) and trigger schema apply + rebuild."""
    result = get_backend(ctx).unpublish_fact_table(name)
    console.print(
        f"[green]Unpublished[/green] dataset [bold]{name}[/bold] "
        f"(status={result['fact_table']['status']})"
    )
    console.print("[yellow]Schema apply + build request triggered.[/yellow]")