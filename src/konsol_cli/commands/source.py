"""ERP source (dbt erp_sources) commands."""
from __future__ import annotations

import typer
from rich.console import Console

from konsol_cli.commands.common import get_backend

app = typer.Typer(help="Inspect enabled ERP sources.")
console = Console()


@app.command("list")
def list_sources(ctx: typer.Context) -> None:
    """List enabled ERP source keys that drive dbt adapters."""
    result = get_backend(ctx).list_erp_sources()
    sources = result.get("erp_sources") or []
    console.print("[bold]Enabled ERP sources[/bold] (dbt vars.erp_sources):")
    for source in sources:
        console.print(f"  • {source}")
    if not sources:
        console.print("  [dim](none — add an enabled Connector)[/dim]")