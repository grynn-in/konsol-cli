"""Structural tests for konsol-mcp tool surface."""
from __future__ import annotations

import importlib
import json

ENVELOPE_KEYS = {
    "status",
    "message",
    "affected_objects",
    "diff",
    "warnings",
    "impact_summary",
    "next_steps",
    "tool_call_id",
}


def test_mcp_exposes_connector_airbyte_tools():
    server = importlib.import_module("konsol_mcp.server")
    assert callable(server.test_connector_writeback)
    assert callable(server.provision_connector_airbyte)


def test_read_tool_returns_envelope(monkeypatch):
    """A representative read tool wraps its data in the response envelope."""
    server = importlib.import_module("konsol_mcp.server")

    class FakeBackend:
        def list_dimensions(self, status=None):
            return [{"name": "Entity"}, {"name": "Account"}]

    monkeypatch.setattr(server, "_backend", lambda: FakeBackend())
    data = json.loads(server.list_dimensions())

    assert set(data) == ENVELOPE_KEYS
    assert data["status"] == "success"
    assert data["affected_objects"] == [{"name": "Entity"}, {"name": "Account"}]
    assert isinstance(data["tool_call_id"], str) and data["tool_call_id"]


def test_diff_read_tool_routes_data_to_diff(monkeypatch):
    """diff_config/export_config put their payload in the ``diff`` field."""
    server = importlib.import_module("konsol_mcp.server")

    class FakeBackend:
        def diff_config(self, spec, status=None):
            return {"create": ["Region"], "update": [], "delete": []}

    monkeypatch.setattr(server, "_backend", lambda: FakeBackend())
    data = json.loads(server.diff_config({"dimensions": []}))

    assert set(data) == ENVELOPE_KEYS
    assert data["status"] == "success"
    assert data["diff"] == {"create": ["Region"], "update": [], "delete": []}


def test_mutate_tool_returns_envelope(monkeypatch):
    """A representative mutating tool reports the affected object + envelope."""
    server = importlib.import_module("konsol_mcp.server")

    class FakeBackend:
        def publish_dimension(self, name):
            return {"name": name, "status": "Published"}

    monkeypatch.setattr(server, "_backend", lambda: FakeBackend())
    data = json.loads(server.publish_dimension("Entity"))

    assert set(data) == ENVELOPE_KEYS
    assert data["status"] == "success"
    assert data["affected_objects"] == ["Entity"]