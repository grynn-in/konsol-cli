"""konsol CLI entrypoint."""
from __future__ import annotations

import typer

from konsol_cli import __version__
from konsol_cli.backends.errors import BackendError
from konsol_cli.commands import config, connector, dimension, fact, measure, schema, source
from konsol_cli.settings import Settings

app = typer.Typer(
    name="konsol",
    help="Configure konsol (Frappe EPM app). All writes go through konsol — never dbt or SQL.",
    no_args_is_help=True,
)
app.add_typer(dimension.app, name="dimension")
app.add_typer(measure.app, name="measure")
app.add_typer(fact.app, name="fact")
app.add_typer(config.app, name="config")
app.add_typer(connector.app, name="connector")
app.add_typer(source.app, name="source")
app.add_typer(schema.app, name="schema")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
    backend: str | None = typer.Option(
        None,
        "--backend",
        help="Connection mode: bench (local Docker) or api (remote HTTP).",
        envvar="KONSOL_BACKEND",
    ),
    site: str | None = typer.Option(
        None,
        "--site",
        help="Frappe site name (also sent as Host header for api backend).",
        envvar="KONSOL_SITE",
    ),
    url: str | None = typer.Option(
        None,
        "--url",
        help="Frappe site URL for api backend, e.g. https://epm.example.com",
        envvar="KONSOL_URL",
    ),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        help="Frappe API key for api backend.",
        envvar="KONSOL_API_KEY",
    ),
    api_secret: str | None = typer.Option(
        None,
        "--api-secret",
        help="Frappe API secret for api backend.",
        envvar="KONSOL_API_SECRET",
    ),
    compose_file: str | None = typer.Option(
        None,
        "--compose-file",
        help="docker-compose.yml path for bench backend.",
        envvar="KONSOL_COMPOSE_FILE",
    ),
    compose_service: str = typer.Option(
        "frappe_backend",
        "--compose-service",
        help="Docker Compose service running bench.",
        envvar="KONSOL_COMPOSE_SERVICE",
    ),
) -> None:
    """konsol CLI root."""
    ctx.obj = Settings.from_env(
        backend=backend,
        site=site,
        url=url,
        api_key=api_key,
        api_secret=api_secret,
        compose_file=compose_file,
        compose_service=compose_service,
    )


@app.command("version")
def version_cmd() -> None:
    typer.echo(__version__)


def run() -> None:
    try:
        app()
    except BackendError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc


if __name__ == "__main__":
    run()