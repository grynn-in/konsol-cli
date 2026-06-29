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


# --- M3: apply_model_from_gitops composite ---------------------------------

_FAKE_DIFF = {
    "dimensions": {
        "added": [{"key": "Region"}],
        "modified": [{"key": "Entity"}],
        "unchanged": ["Account"],
        "only_on_site": [{"key": "Legacy"}],
    },
    "measures": {"added": [], "modified": [], "unchanged": [], "only_on_site": []},
    "fact_tables": {"added": [], "modified": [], "unchanged": [], "only_on_site": []},
    "connectors": {"added": [], "modified": [], "unchanged": [], "only_on_site": []},
}


class _GitOpsBackend:
    def __init__(self):
        self.diff_calls = []
        self.apply_calls = []

    def diff_config(self, spec, status=None):
        self.diff_calls.append(spec)
        return _FAKE_DIFF

    def apply_config(self, spec, publish=False, prune=False):
        self.apply_calls.append((spec, publish, prune))
        return {
            "dimensions": ["Region", "Entity"],
            "measures": [],
            "fact_tables": [],
            "connectors": [],
        }


def _write_bundle(tmp_path):
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps({"dimensions": [{"key": "Region"}]}))
    return path


def test_apply_model_from_gitops_validation_failed_missing_file(monkeypatch, tmp_path):
    """A missing/unreadable bundle path returns validation_failed, never raises."""
    server = importlib.import_module("konsol_mcp.server")
    backend = _GitOpsBackend()
    monkeypatch.setattr(server, "_backend", lambda: backend)

    data = json.loads(
        server.apply_model_from_gitops(str(tmp_path / "nope.json"))
    )

    assert set(data) == ENVELOPE_KEYS
    assert data["status"] == "validation_failed"
    assert data["warnings"]
    assert backend.diff_calls == []
    assert backend.apply_calls == []


def test_apply_model_from_gitops_validation_failed_empty_path(monkeypatch):
    """An empty bundle_path is rejected before any backend call."""
    server = importlib.import_module("konsol_mcp.server")
    backend = _GitOpsBackend()
    monkeypatch.setattr(server, "_backend", lambda: backend)

    data = json.loads(server.apply_model_from_gitops("   "))

    assert data["status"] == "validation_failed"
    assert backend.diff_calls == []


def test_apply_model_from_gitops_dry_run_does_not_apply(monkeypatch, tmp_path):
    """dry_run (default) diffs but never calls apply_config."""
    server = importlib.import_module("konsol_mcp.server")
    backend = _GitOpsBackend()
    monkeypatch.setattr(server, "_backend", lambda: backend)
    path = _write_bundle(tmp_path)

    data = json.loads(server.apply_model_from_gitops(str(path)))

    assert set(data) == ENVELOPE_KEYS
    assert data["status"] == "dry_run"
    assert backend.diff_calls  # diffed
    assert backend.apply_calls == []  # but never applied
    assert data["diff"] == _FAKE_DIFF
    keys = {obj["key"] for obj in data["affected_objects"]}
    assert {"Region", "Entity"} <= keys
    assert data["impact_summary"]
    assert data["next_steps"]


def test_apply_model_from_gitops_apply_path(monkeypatch, tmp_path):
    """dry_run=False applies the bundle and reports success."""
    server = importlib.import_module("konsol_mcp.server")
    backend = _GitOpsBackend()
    monkeypatch.setattr(server, "_backend", lambda: backend)
    path = _write_bundle(tmp_path)

    data = json.loads(
        server.apply_model_from_gitops(str(path), dry_run=False, publish=True)
    )

    assert set(data) == ENVELOPE_KEYS
    assert data["status"] == "success"
    assert len(backend.apply_calls) == 1
    spec, publish, prune = backend.apply_calls[0]
    assert publish is True and prune is False
    assert data["warnings"]  # publish-gate note
    assert data["affected_objects"]