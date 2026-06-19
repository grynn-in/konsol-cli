"""CLI rendering helpers."""
from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.table import Table


def print_rows(
    console: Console,
    title: str,
    rows: list[dict[str, Any]],
    columns: list[tuple[str, str]],
) -> None:
    if not rows:
        console.print(f"[yellow]No {title.lower()} found.[/yellow]")
        return

    table = Table(title=title, show_header=True, header_style="bold")
    for header, _ in columns:
        table.add_column(header)

    for row in rows:
        table.add_row(*(str(row.get(key, "")) for _, key in columns))

    console.print(table)