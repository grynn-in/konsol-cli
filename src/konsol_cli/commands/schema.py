"""Schema apply and status commands."""
from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.json import JSON
from rich.table import Table

from konsol_cli.commands.common import get_backend

app = typer.Typer(help="Apply schema and inspect build status.")
console = Console()


def _print_registry(registry: dict) -> None:
    table = Table(title="Config Registry", show_header=True, header_style="bold")
    table.add_column("DocType")
    table.add_column("Draft", justify="right")
    table.add_column("Published", justify="right")
    table.add_column("Inactive", justify="right")

    labels = {
        "dimensions": "Dimension",
        "measures": "Measure",
        "fact_tables": "Dataset",
    }
    for key, label in labels.items():
        counts = registry.get(key)
        if not counts:
            continue
        table.add_row(
            label,
            str(counts.get("Draft", 0)),
            str(counts.get("Published", 0)),
            str(counts.get("Inactive", 0)),
        )

    console.print(table)


def _print_builds(title: str, rows: list[dict]) -> None:
    if not rows:
        console.print(f"[dim]{title}: none[/dim]")
        return

    table = Table(title=title, show_header=True, header_style="bold")
    table.add_column("Name")
    table.add_column("Scope")
    table.add_column("State")
    table.add_column("Risk")
    table.add_column("Trigger")
    table.add_column("Modified")

    for row in rows:
        trigger = row.get("trigger_doctype") or ""
        if row.get("trigger_docname"):
            trigger = f"{trigger} {row['trigger_docname']}".strip()
        table.add_row(
            str(row.get("name", "")),
            str(row.get("build_scope", "")),
            str(row.get("workflow_state", "")),
            str(row.get("risk_level", "")),
            trigger,
            str(row.get("modified", "")),
        )

    console.print(table)


@app.command("apply")
def apply_schema(
    ctx: typer.Context,
    run_dbt: bool = typer.Option(
        False,
        "--run-dbt",
        help="Enqueue a background dbt build after schema changes.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Print raw JSON summary."),
) -> None:
    """Apply schema from published config (dbt vars, ClickHouse DDL, budget fields)."""
    summary = get_backend(ctx).apply_schema(run_dbt=run_dbt)

    if json_output:
        console.print(JSON(json.dumps(summary)))
        return

    console.print("[green]Schema apply complete.[/green]")
    console.print(f"vars_updated: {summary.get('vars_updated')}")
    console.print(f"columns_added: {len(summary.get('columns_added') or [])}")
    console.print(f"facts_created: {len(summary.get('facts_created') or [])}")
    console.print(f"sources_written: {len(summary.get('sources_written') or [])}")
    console.print(
        f"budget_fields_synced: {len(summary.get('budget_fields_synced') or [])}"
    )
    console.print(f"dbt_triggered: {summary.get('dbt_triggered')}")

    errors = summary.get("errors") or []
    if errors:
        console.print("[yellow]Errors:[/yellow]")
        for error in errors:
            console.print(f"  - {error}")


@app.command("status")
def schema_status(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Print raw JSON status."),
) -> None:
    """Show config registry counts and pipeline build request status."""
    status = get_backend(ctx).get_schema_status()

    if json_output:
        console.print(JSON(json.dumps(status)))
        return

    _print_registry(status.get("registry") or {})
    _print_builds("Pending Build Requests", status.get("pending_builds") or [])
    _print_builds("Recent Build Requests", status.get("recent_builds") or [])