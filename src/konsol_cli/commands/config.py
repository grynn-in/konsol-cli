"""GitOps-style config export, apply, and diff."""
from __future__ import annotations

import json
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.json import JSON
from rich.table import Table

from konsol_cli.commands.common import get_backend, status_option

app = typer.Typer(help="Export, apply, and diff konsol config bundles.")
console = Console()


def _load_bundle(path: Path) -> dict:
    text = path.read_text()
    if path.suffix in {".yaml", ".yml"}:
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise typer.BadParameter(f"{path} must contain a config object.")
    return data


def _write_bundle(path: Path, bundle: dict) -> None:
    if path.suffix in {".yaml", ".yml"}:
        path.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True))
    else:
        path.write_text(json.dumps(bundle, indent=2) + "\n")


def _count_diff(section: dict) -> tuple[int, int, int, int]:
    return (
        len(section.get("added", [])),
        len(section.get("modified", [])),
        len(section.get("unchanged", [])),
        len(section.get("only_on_site", [])),
    )


def _print_diff_section(title: str, section: dict) -> None:
    added, modified, unchanged, only_on_site = _count_diff(section)
    if not any((added, modified, unchanged, only_on_site)):
        return

    table = Table(title=title)
    table.add_column("Change")
    table.add_column("Key")
    table.add_column("Detail")

    for item in section.get("added", []):
        table.add_row("added", item["key"], "in file only")
    for item in section.get("modified", []):
        table.add_row("modified", item["key"], "differs from site")
    for key in section.get("unchanged", []):
        table.add_row("unchanged", key, "")
    for item in section.get("only_on_site", []):
        table.add_row("only on site", item["key"], "not in file")

    console.print(table)


@app.command("export")
def export_config(
    ctx: typer.Context,
    output: Path = typer.Option(..., "--output", "-o", help="YAML or JSON output path."),
    status: str | None = status_option(),
) -> None:
    """Export dimensions, measures, fact tables, and connectors to a config file."""
    bundle = get_backend(ctx).export_config(status=status)
    output.parent.mkdir(parents=True, exist_ok=True)
    _write_bundle(output, bundle)
    console.print(
        f"[green]Exported[/green] "
        f"{len(bundle.get('dimensions', []))} dimensions, "
        f"{len(bundle.get('measures', []))} measures, "
        f"{len(bundle.get('fact_tables', []))} fact tables, "
        f"{len(bundle.get('connectors', []))} connectors "
        f"to [bold]{output}[/bold]"
    )


@app.command("apply")
def apply_config(
    ctx: typer.Context,
    path: Path = typer.Argument(help="YAML or JSON config bundle."),
    publish: bool = typer.Option(
        False,
        "--publish",
        help="Publish each entity after save.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show diff only; do not write to the site.",
    ),
    prune: bool = typer.Option(
        False,
        "--prune",
        help="Remove entities on the site that are not in the bundle.",
    ),
) -> None:
    """Apply a config bundle to the konsol site."""
    bundle = _load_bundle(path)
    backend = get_backend(ctx)

    if dry_run:
        diff = backend.diff_config(bundle)
        console.print(f"[yellow]Dry run[/yellow] for [bold]{path}[/bold]")
        _print_diff_section("Dimensions", diff["dimensions"])
        _print_diff_section("Measures", diff["measures"])
        _print_diff_section("Fact Tables", diff["fact_tables"])
        _print_diff_section("Connectors", diff["connectors"])
        raise typer.Exit()

    summary = backend.apply_config(bundle, publish=publish, prune=prune)
    console.print(
        f"[green]Applied[/green] "
        f"{len(summary.get('dimensions', []))} dimensions, "
        f"{len(summary.get('measures', []))} measures, "
        f"{len(summary.get('fact_tables', []))} fact tables, "
        f"{len(summary.get('connectors', []))} connectors"
    )
    if prune:
        pruned = summary.get("pruned") or {}
        console.print(
            "[yellow]Pruned[/yellow] "
            f"{len(pruned.get('dimensions', []))} dimensions, "
            f"{len(pruned.get('measures', []))} measures, "
            f"{len(pruned.get('fact_tables', []))} fact tables, "
            f"{len(pruned.get('connectors', []))} connectors"
        )
    if publish:
        console.print("[yellow]Published entities — schema apply + build requests triggered.[/yellow]")


@app.command("diff")
def diff_config(
    ctx: typer.Context,
    path: Path = typer.Argument(help="YAML or JSON config bundle."),
    status: str | None = status_option(),
    json_output: bool = typer.Option(False, "--json", help="Print raw diff JSON."),
) -> None:
    """Diff a config bundle against the live site."""
    bundle = _load_bundle(path)
    diff = get_backend(ctx).diff_config(bundle, status=status)

    if json_output:
        console.print(JSON(json.dumps(diff)))
        return

    console.print(f"Diff for [bold]{path}[/bold]")
    _print_diff_section("Dimensions", diff["dimensions"])
    _print_diff_section("Measures", diff["measures"])
    _print_diff_section("Fact Tables", diff["fact_tables"])
    _print_diff_section("Connectors", diff["connectors"])