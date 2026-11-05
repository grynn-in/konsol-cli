"""konsol-cli talks to exactly five konsol endpoints (konsol#379, 5 Nov 2026).

konsol keeps five whitelisted methods in ``konsol.cli_api``; the other
wrappers were removed, and that work is done in the Frappe Desk or with
``frappectl``. These tests pin the CLI commands, the backend methods and the
MCP tools to those five, with the HTTP verb each one needs: a write sent as
GET is rolled back by Frappe at the end of the request.
"""
from __future__ import annotations

import asyncio
import importlib
import inspect
import json
from unittest.mock import MagicMock

import pytest
import typer.main

from konsol_cli.backends.api import ApiBackend
from konsol_cli.backends.base import ConfigBackend
from konsol_cli.backends.bench import BenchBackend
from konsol_cli.settings import Settings

FIVE_ENDPOINTS = {
    "konsol.cli_api.apply_schema_api",
    "konsol.cli_api.get_schema_status_api",
    "konsol.cli_api.export_config_api",
    "konsol.cli_api.diff_config_api",
    "konsol.cli_api.apply_config_api",
}

BACKEND_METHODS = {
    "apply_schema",
    "get_schema_status",
    "export_config",
    "diff_config",
    "apply_config",
}

# (backend method, call args, endpoint, HTTP verb, expected request payload)
# diff_config sends the bundle as a JSON body: the endpoint accepts POST, it
# writes nothing, and a large bundle does not fit in a query string.
API_CALLS = [
    ("apply_schema", (), {"run_dbt": True}, "konsol.cli_api.apply_schema_api", "POST", {"run_dbt": 1}),
    ("get_schema_status", (), {}, "konsol.cli_api.get_schema_status_api", "GET", None),
    ("export_config", (), {"status": "Published"}, "konsol.cli_api.export_config_api", "GET", {"status": "Published"}),
    (
        "diff_config",
        ({"dimensions": []},),
        {},
        "konsol.cli_api.diff_config_api",
        "POST",
        {"spec": {"dimensions": []}},
    ),
    (
        "apply_config",
        ({"dimensions": []},),
        {"publish": True, "prune": True},
        "konsol.cli_api.apply_config_api",
        "POST",
        {"spec": {"dimensions": []}, "publish": 1, "prune": 1},
    ),
]


def _api_settings() -> Settings:
    return Settings(
        backend="api",
        site="konsolidat.local",
        compose_file=None,
        compose_service="frappe_backend",
        url="http://localhost:8069",
        api_key="k",
        api_secret="s",
    )


def _public_methods(cls) -> set[str]:
    return {
        name
        for name, _ in inspect.getmembers(cls, predicate=inspect.isfunction)
        if not name.startswith("_")
    }


# --- CLI commands ------------------------------------------------------------


def _command_tree() -> dict[str, set[str] | None]:
    from konsol_cli.main import app

    root = typer.main.get_command(app)
    tree: dict[str, set[str] | None] = {}
    for name, command in root.commands.items():
        sub = getattr(command, "commands", None)
        tree[name] = set(sub) if sub is not None else None
    return tree


def test_cli_offers_only_config_and_schema_commands():
    assert _command_tree() == {
        "config": {"export", "diff", "apply"},
        "schema": {"apply", "status"},
        "version": None,
    }


def test_config_apply_keeps_publish_prune_and_dry_run():
    from konsol_cli.main import app

    apply_cmd = typer.main.get_command(app).commands["config"].commands["apply"]
    flags = {opt for param in apply_cmd.params for opt in getattr(param, "opts", [])}
    assert {"--publish", "--prune", "--dry-run"} <= flags


# --- Backends ----------------------------------------------------------------


@pytest.mark.parametrize("cls", [ApiBackend, BenchBackend, ConfigBackend])
def test_backend_exposes_only_the_five_operations(cls):
    assert _public_methods(cls) == BACKEND_METHODS


@pytest.mark.parametrize("method_name,args,kwargs,endpoint,verb,payload", API_CALLS)
def test_api_backend_calls_one_of_five_endpoints_with_the_right_verb(
    method_name, args, kwargs, endpoint, verb, payload
):
    assert endpoint in FIVE_ENDPOINTS
    backend = ApiBackend(_api_settings())
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"message": {}}
    sent: dict = {}

    def fake_post(url, json=None, timeout=None):
        sent.update(verb="POST", url=url, payload=json)
        return response

    def fake_get(url, params=None, timeout=None):
        sent.update(verb="GET", url=url, payload=params)
        return response

    backend._session.post = fake_post
    backend._session.get = fake_get

    getattr(backend, method_name)(*args, **kwargs)

    assert sent["verb"] == verb
    assert sent["url"] == f"http://localhost:8069/api/method/{endpoint}"
    assert sent["payload"] == payload


@pytest.mark.parametrize("method_name,args,kwargs,endpoint,verb,payload", API_CALLS)
def test_bench_backend_calls_one_of_five_endpoints(
    method_name, args, kwargs, endpoint, verb, payload, monkeypatch
):
    backend = BenchBackend(
        Settings(
            backend="bench",
            site="konsolidat.local",
            compose_file="/compose.yml",
            compose_service="frappe_backend",
            url=None,
            api_key=None,
            api_secret=None,
        )
    )
    called: list[str] = []
    monkeypatch.setattr(
        backend, "_call", lambda method, **kw: called.append(method) or {}
    )
    getattr(backend, method_name)(*args, **kwargs)
    assert called == [endpoint]


# --- MCP server --------------------------------------------------------------

MCP_TOOLS = {
    "export_config",
    "diff_config",
    "apply_config",
    "apply_schema",
    "get_schema_status",
    "apply_model_from_gitops",
    "preview_impact",
}


def _mcp_tool_names() -> set[str]:
    server = importlib.import_module("konsol_mcp.server")
    return {tool.name for tool in asyncio.run(server.mcp.list_tools())}


def test_mcp_offers_only_tools_built_on_the_five_endpoints():
    assert _mcp_tool_names() == MCP_TOOLS


class _ReadOnlyBackend:
    def diff_config(self, spec, status=None):
        return {"dimensions": {"added": [{"key": "Region"}]}}

    def get_schema_status(self):
        return {"registry": {"dimensions": {"Published": 2}}}

    def apply_config(self, spec, publish=False, prune=False):
        return {"dimensions": ["Region"]}


@pytest.mark.parametrize(
    "tool,kwargs",
    [
        ("apply_model_from_gitops", {"dry_run": True}),
        ("apply_model_from_gitops", {"dry_run": False}),
        ("preview_impact", {}),
    ],
)
def test_mcp_next_steps_name_only_existing_tools(tool, kwargs, monkeypatch, tmp_path):
    server = importlib.import_module("konsol_mcp.server")
    monkeypatch.setattr(server, "_backend", lambda: _ReadOnlyBackend())
    bundle = tmp_path / "model.yaml"
    bundle.write_text("dimensions:\n  - dimension_name: Region\n")

    data = json.loads(getattr(server, tool)(bundle_path=str(bundle), **kwargs))

    tools = _mcp_tool_names()
    for step in data["next_steps"]:
        first_word = step.split()[0]
        if "_" in first_word:
            assert first_word in tools, f"{tool} points at removed tool {first_word!r}"
