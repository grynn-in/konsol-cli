"""Tests for the HTTP API transport backend."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from konsol_cli.backends.api import ApiBackend
from konsol_cli.backends.errors import BackendError
from konsol_cli.settings import Settings


def _settings() -> Settings:
    return Settings(
        backend="api",
        site="konsolidat.local",
        compose_file=None,
        compose_service="frappe_backend",
        url="http://localhost:8069",
        api_key="test-key",
        api_secret="test-secret",
    )


def test_api_backend_requires_url():
    with pytest.raises(BackendError, match="url is required"):
        ApiBackend(
            Settings(
                backend="api",
                site="konsolidat.local",
                compose_file=None,
                compose_service="frappe_backend",
                url=None,
                api_key="k",
                api_secret="s",
            )
        )


def test_api_backend_requires_credentials():
    with pytest.raises(BackendError, match="api_key and api_secret"):
        ApiBackend(
            Settings(
                backend="api",
                site="konsolidat.local",
                compose_file=None,
                compose_service="frappe_backend",
                url="http://localhost:8069",
                api_key=None,
                api_secret=None,
            )
        )


def test_export_config_uses_frappe_api(monkeypatch):
    backend = ApiBackend(_settings())
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "message": {"dimensions": [{"dimension_name": "dim_cost_center"}]},
    }

    captured: dict = {}

    def fake_get(url, params=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        return response

    backend._session.get = fake_get

    bundle = backend.export_config(status="Published")

    assert bundle == {"dimensions": [{"dimension_name": "dim_cost_center"}]}
    assert captured["url"] == (
        "http://localhost:8069/api/method/konsol.cli_api.export_config_api"
    )
    assert captured["params"] == {"status": "Published"}
    assert backend._session.headers["Authorization"] == "token test-key:test-secret"
    assert backend._session.headers["Host"] == "konsolidat.local"


def test_frappe_exception_raises_backend_error():
    backend = ApiBackend(_settings())
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"exc": "Traceback...", "exception": "PermissionError"}

    backend._session.get = MagicMock(return_value=response)

    with pytest.raises(BackendError, match="PermissionError"):
        backend.get_schema_status()


def test_apply_config_posts_json():
    backend = ApiBackend(_settings())
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"message": {"dimensions": [], "measures": [], "fact_tables": []}}

    captured: dict = {}

    def fake_post(url, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        return response

    backend._session.post = fake_post

    spec = {"api_version": "konsol/v1", "dimensions": []}
    backend.apply_config(spec, publish=True)

    assert captured["url"].endswith("konsol.cli_api.apply_config_api")
    assert captured["json"]["spec"] == spec
    assert captured["json"]["publish"] == 1
