"""Tests for settings and secret loading."""
from __future__ import annotations

from konsol_cli.settings import Settings


def test_settings_loads_api_credentials_from_secrets_env(
    monkeypatch, tmp_path
) -> None:
    secrets = tmp_path / "secrets.env"
    secrets.write_text(
        "KONSOL_API_KEY=from-dotenv\nKONSOL_API_SECRET=from-dotenv-too\n"
    )
    monkeypatch.delenv("KONSOL_API_KEY", raising=False)
    monkeypatch.delenv("KONSOL_API_SECRET", raising=False)
    monkeypatch.setenv("KONSOL_SECRETS", str(secrets))

    settings = Settings.from_env()

    assert settings.api_key == "from-dotenv"
    assert settings.api_secret == "from-dotenv-too"


def test_settings_loads_api_credentials_from_secrets_toml(
    monkeypatch, tmp_path
) -> None:
    secrets = tmp_path / "secrets.toml"
    secrets.write_text(
        '[default]\napi_key = "from-secrets"\napi_secret = "from-secrets-too"\n'
    )
    monkeypatch.delenv("KONSOL_API_KEY", raising=False)
    monkeypatch.delenv("KONSOL_API_SECRET", raising=False)
    monkeypatch.setenv("KONSOL_SECRETS", str(secrets))

    settings = Settings.from_env()

    assert settings.api_key == "from-secrets"
    assert settings.api_secret == "from-secrets-too"

def test_settings_reads_site_from_config_file(monkeypatch, tmp_path) -> None:
    """A site in config.toml must win over the built-in default.

    Regression: ``--site`` used to carry a non-None typer default
    ("konsolidat.local"), so the ``site or env or file_cfg`` chain in
    ``Settings.from_env`` short-circuited on the default and the config-file
    key was unreachable.
    """
    config = tmp_path / "config.toml"
    config.write_text('[default]\nsite = "demo.example.com"\n')
    monkeypatch.delenv("KONSOL_SITE", raising=False)
    monkeypatch.setenv("KONSOL_CONFIG", str(config))

    settings = Settings.from_env()

    assert settings.site == "demo.example.com"


def test_cli_site_option_has_no_default() -> None:
    """``--site`` must default to None so config.toml can be reached.

    Guards the typer layer directly: any non-None default here silently
    disables the config-file lookup regardless of settings.py.
    """
    import inspect

    from konsol_cli.main import main

    default = inspect.signature(main).parameters["site"].default
    assert default.default is None
