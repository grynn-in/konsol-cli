"""Tests for the konsol-mcp tools (see test_five_endpoints.py for the tool set)."""
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
    """apply_config returns the envelope with the apply summary in ``diff``."""
    server = importlib.import_module("konsol_mcp.server")

    class FakeBackend:
        def apply_config(self, spec, publish=False, prune=False):
            return {"dimensions": ["Region"], "measures": []}

    monkeypatch.setattr(server, "_backend", lambda: FakeBackend())
    data = json.loads(server.apply_config({"dimensions": []}, publish=True))

    assert set(data) == ENVELOPE_KEYS
    assert data["status"] == "success"
    assert data["diff"] == {"dimensions": ["Region"], "measures": []}
    assert data["warnings"]


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


def test_apply_model_from_gitops_apply_backend_error_returns_envelope(
    monkeypatch, tmp_path
):
    """A backend raise during apply_config becomes a status=error envelope (M3)."""
    server = importlib.import_module("konsol_mcp.server")
    backend = _GitOpsBackend()

    def _boom(spec, publish=False, prune=False):
        raise RuntimeError("Frappe API error: 500")

    backend.apply_config = _boom
    monkeypatch.setattr(server, "_backend", lambda: backend)
    path = _write_bundle(tmp_path)

    data = json.loads(server.apply_model_from_gitops(str(path), dry_run=False))

    assert set(data) == ENVELOPE_KEYS
    assert data["status"] == "error"
    assert data["warnings"]
    assert data["affected_objects"]  # records what would have been touched


# --- M7: preview_impact composite (read-only) ------------------------------


class _PreviewBackend:
    """Read-only fake backend for M7 tests (diff_config + get_schema_status only).

    Deliberately exposes no mutating methods, so any accidental
    upsert/publish/apply call surfaces as an AttributeError and fails the test.
    """

    def __init__(self):
        self.diff_calls = []
        self.status_calls = 0

    def diff_config(self, spec, status=None):
        self.diff_calls.append(spec)
        return _FAKE_DIFF

    def get_schema_status(self):
        self.status_calls += 1
        return {
            "registry": {
                "dimension": {"Published": 5, "Draft": 2},
                "measure": {"Published": 3},
            },
            "pending_builds": [],
        }


def test_preview_impact_validation_failed_no_input(monkeypatch):
    """Neither bundle_path nor names given is rejected before any backend call."""
    server = importlib.import_module("konsol_mcp.server")
    backend = _PreviewBackend()
    monkeypatch.setattr(server, "_backend", lambda: backend)

    data = json.loads(server.preview_impact())

    assert set(data) == ENVELOPE_KEYS
    assert data["status"] == "validation_failed"
    assert data["warnings"]
    assert backend.diff_calls == []
    assert backend.status_calls == 0


def test_preview_impact_validation_failed_bad_names(monkeypatch):
    """A non-list names argument is rejected before any backend call."""
    server = importlib.import_module("konsol_mcp.server")
    backend = _PreviewBackend()
    monkeypatch.setattr(server, "_backend", lambda: backend)

    data = json.loads(server.preview_impact(names="Region"))

    assert data["status"] == "validation_failed"
    assert backend.diff_calls == []
    assert backend.status_calls == 0


def test_preview_impact_validation_failed_missing_file(monkeypatch, tmp_path):
    """A missing/unreadable bundle path returns validation_failed, never raises."""
    server = importlib.import_module("konsol_mcp.server")
    backend = _PreviewBackend()
    monkeypatch.setattr(server, "_backend", lambda: backend)

    data = json.loads(server.preview_impact(bundle_path=str(tmp_path / "nope.json")))

    assert data["status"] == "validation_failed"
    assert data["warnings"]
    assert backend.diff_calls == []
    assert backend.status_calls == 0


def test_preview_impact_validation_failed_unparseable_file(monkeypatch, tmp_path):
    """An unparseable bundle file returns validation_failed, never raises."""
    server = importlib.import_module("konsol_mcp.server")
    backend = _PreviewBackend()
    monkeypatch.setattr(server, "_backend", lambda: backend)
    path = tmp_path / "bad.json"
    path.write_text("[1, 2, 3]")  # a list is not a config object

    data = json.loads(server.preview_impact(bundle_path=str(path)))

    assert data["status"] == "validation_failed"
    assert backend.diff_calls == []
    assert backend.status_calls == 0


def test_preview_impact_bundle_path_is_read_only(monkeypatch, tmp_path):
    """bundle_path path: diff flattened into affected_objects, status reflected, no mutation."""
    server = importlib.import_module("konsol_mcp.server")
    backend = _PreviewBackend()
    monkeypatch.setattr(server, "_backend", lambda: backend)
    path = _write_bundle(tmp_path)

    data = json.loads(server.preview_impact(bundle_path=str(path)))

    assert set(data) == ENVELOPE_KEYS
    assert data["status"] == "dry_run"
    # composed both read-only primitives, exactly once each
    assert len(backend.diff_calls) == 1
    assert backend.status_calls == 1
    # would-be-touched objects flattened from the diff
    keys = {obj["key"] for obj in data["affected_objects"]}
    assert {"Region", "Entity"} <= keys
    # schema status reflected in the impact summary (8 published)
    assert "8" in data["impact_summary"]
    # limitation about missing transitive lineage noted in warnings
    assert any("lineage" in w.lower() or "blast" in w.lower() for w in data["warnings"])
    assert data["next_steps"]


def test_preview_impact_names_only(monkeypatch):
    """names-only path: affected_objects built from the names, schema status fetched."""
    server = importlib.import_module("konsol_mcp.server")
    backend = _PreviewBackend()
    monkeypatch.setattr(server, "_backend", lambda: backend)

    data = json.loads(server.preview_impact(names=["Region", "GrossMargin"]))

    assert data["status"] == "dry_run"
    # no bundle => no diff_config call, but schema status still consulted
    assert backend.diff_calls == []
    assert backend.status_calls == 1
    keys = {obj["key"] for obj in data["affected_objects"]}
    assert {"Region", "GrossMargin"} <= keys
    assert data["warnings"]
    assert data["next_steps"]
    assert data["warnings"]