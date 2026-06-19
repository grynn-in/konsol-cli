"""Tests for settings and secret loading."""
from __future__ import annotations

from konsol_cli.settings import Settings


def test_settings_loads_api_credentials_from_secrets_file(
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