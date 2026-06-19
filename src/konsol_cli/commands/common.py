"""Shared CLI options and backend factory."""
from __future__ import annotations

import typer

from konsol_cli.backends.api import ApiBackend
from konsol_cli.backends.base import ConfigBackend
from konsol_cli.backends.bench import BenchBackend
from konsol_cli.backends.errors import BackendError
from konsol_cli.settings import Settings


def get_backend(ctx: typer.Context) -> ConfigBackend:
    settings = ctx.ensure_object(Settings)
    return make_backend(settings)


def make_backend(settings: Settings) -> ConfigBackend:
    backend = settings.backend.lower()
    if backend == "api":
        return ApiBackend(settings)
    if backend == "bench":
        return BenchBackend(settings)
    raise BackendError(f"Unknown backend '{settings.backend}'. Use 'bench' or 'api'.")


def status_option() -> str | None:
    return typer.Option(
        None,
        "--status",
        help="Filter by lifecycle status: Draft, Published, or Inactive.",
    )