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


# --- M4: publish_model_changes composite -----------------------------------


class _PublishBackend:
    """Fake backend recording publish/apply calls for M4 tests."""

    def __init__(self, drafts=None):
        # drafts maps kind -> list of draft docs
        self._drafts = drafts or {
            "dimension": [{"name": "Region"}, {"name": "Entity"}],
            "measure": [{"measure_name": "GrossMargin"}],
            "fact_table": [],
        }
        self.published = []  # list of (kind, name)
        self.apply_schema_calls = []

    def list_dimensions(self, status=None):
        assert status == "Draft"
        return list(self._drafts["dimension"])

    def list_measures(self, status=None):
        assert status == "Draft"
        return list(self._drafts["measure"])

    def list_fact_tables(self, status=None):
        assert status == "Draft"
        return list(self._drafts["fact_table"])

    def publish_dimension(self, name):
        self.published.append(("dimension", name))
        return {"name": name, "status": "Published"}

    def publish_measure(self, name):
        self.published.append(("measure", name))
        return {"name": name, "status": "Published"}

    def publish_fact_table(self, name):
        self.published.append(("fact_table", name))
        return {"name": name, "status": "Published"}

    def apply_schema(self, run_dbt=False):
        self.apply_schema_calls.append(run_dbt)
        return {"applied": True}


def test_publish_model_changes_validation_failed_bad_kinds(monkeypatch):
    """An unknown kind is rejected before any backend call."""
    server = importlib.import_module("konsol_mcp.server")
    backend = _PublishBackend()
    monkeypatch.setattr(server, "_backend", lambda: backend)

    data = json.loads(server.publish_model_changes(kinds=["bogus"]))

    assert set(data) == ENVELOPE_KEYS
    assert data["status"] == "validation_failed"
    assert data["warnings"]
    assert backend.published == []
    assert backend.apply_schema_calls == []


def test_publish_model_changes_validation_failed_bad_names(monkeypatch):
    """A non-list names argument is rejected before any backend call."""
    server = importlib.import_module("konsol_mcp.server")
    backend = _PublishBackend()
    monkeypatch.setattr(server, "_backend", lambda: backend)

    data = json.loads(server.publish_model_changes(names="Region"))

    assert data["status"] == "validation_failed"
    assert backend.published == []
    assert backend.apply_schema_calls == []


def test_publish_model_changes_dry_run_discovers_without_mutating(monkeypatch):
    """dry_run (default) lists discovered drafts but never publishes/applies."""
    server = importlib.import_module("konsol_mcp.server")
    backend = _PublishBackend()
    monkeypatch.setattr(server, "_backend", lambda: backend)

    data = json.loads(server.publish_model_changes())

    assert set(data) == ENVELOPE_KEYS
    assert data["status"] == "dry_run"
    assert backend.published == []
    assert backend.apply_schema_calls == []
    keys = {obj["key"] for obj in data["affected_objects"]}
    assert {"Region", "Entity", "GrossMargin"} <= keys
    assert data["next_steps"]


def test_publish_model_changes_dry_run_respects_kinds(monkeypatch):
    """The kinds filter narrows discovery to the requested doctypes."""
    server = importlib.import_module("konsol_mcp.server")
    backend = _PublishBackend()
    monkeypatch.setattr(server, "_backend", lambda: backend)

    data = json.loads(server.publish_model_changes(kinds=["measure"]))

    kinds = {obj["kind"] for obj in data["affected_objects"]}
    assert kinds == {"measure"}


def test_publish_model_changes_apply_publishes_each_then_applies_schema(monkeypatch):
    """dry_run=False publishes every discovered item then applies schema once."""
    server = importlib.import_module("konsol_mcp.server")
    backend = _PublishBackend()
    monkeypatch.setattr(server, "_backend", lambda: backend)

    data = json.loads(server.publish_model_changes(dry_run=False))

    assert data["status"] == "success"
    assert ("dimension", "Region") in backend.published
    assert ("dimension", "Entity") in backend.published
    assert ("measure", "GrossMargin") in backend.published
    assert backend.apply_schema_calls == [False]
    assert data["warnings"]  # publish-gate note
    names = set(data["affected_objects"])
    assert {"Region", "Entity", "GrossMargin"} <= names


def test_publish_model_changes_explicit_names(monkeypatch):
    """Explicit names are published without draft discovery."""
    server = importlib.import_module("konsol_mcp.server")
    backend = _PublishBackend()
    monkeypatch.setattr(server, "_backend", lambda: backend)

    data = json.loads(
        server.publish_model_changes(
            names=["Region"], kinds=["dimension"], dry_run=False
        )
    )

    assert data["status"] == "success"
    assert backend.published == [("dimension", "Region")]
    assert backend.apply_schema_calls == [False]


def test_publish_model_changes_nothing_to_publish(monkeypatch):
    """No drafts -> success with a warning and no mutation."""
    server = importlib.import_module("konsol_mcp.server")
    backend = _PublishBackend(
        drafts={"dimension": [], "measure": [], "fact_table": []}
    )
    monkeypatch.setattr(server, "_backend", lambda: backend)

    data = json.loads(server.publish_model_changes(dry_run=False))

    assert data["status"] == "success"
    assert data["affected_objects"] == []
    assert data["warnings"]
    assert backend.published == []
    assert backend.apply_schema_calls == []


# --- M5: provision_and_test_connector composite ----------------------------


class _ConnectorBackend:
    """Fake backend recording provision/test calls for M5 tests."""

    def __init__(self, connector=None, writeback=None, raise_on_get=False):
        # ``connector`` is what get_connector returns (None => missing).
        self._connector = (
            connector
            if connector is not None
            else {"name": "CONN-00001", "connector_name": "D365 Prod"}
        )
        self._writeback = writeback if writeback is not None else {"ok": True}
        self._raise_on_get = raise_on_get
        self.get_calls = []
        self.provision_calls = []
        self.test_calls = []

    def get_connector(self, name):
        self.get_calls.append(name)
        if self._raise_on_get:
            raise RuntimeError("boom")
        return self._connector

    def provision_connector_airbyte(self, name):
        self.provision_calls.append(name)
        return {"source_id": "src-1", "connection_id": "conn-1"}

    def test_connector_writeback(self, name):
        self.test_calls.append(name)
        return self._writeback


def test_provision_and_test_connector_validation_failed_missing(monkeypatch):
    """A connector get that returns nothing is rejected before provisioning."""
    server = importlib.import_module("konsol_mcp.server")
    backend = _ConnectorBackend(connector={})
    monkeypatch.setattr(server, "_backend", lambda: backend)

    data = json.loads(server.provision_and_test_connector("CONN-99999"))

    assert set(data) == ENVELOPE_KEYS
    assert data["status"] == "validation_failed"
    assert data["warnings"]
    assert backend.provision_calls == []
    assert backend.test_calls == []


def test_provision_and_test_connector_validation_failed_blank_name(monkeypatch):
    """A blank name is rejected before any backend call."""
    server = importlib.import_module("konsol_mcp.server")
    backend = _ConnectorBackend()
    monkeypatch.setattr(server, "_backend", lambda: backend)

    data = json.loads(server.provision_and_test_connector("   "))

    assert data["status"] == "validation_failed"
    assert backend.get_calls == []
    assert backend.provision_calls == []
    assert backend.test_calls == []


def test_provision_and_test_connector_validation_failed_get_raises(monkeypatch):
    """A get_connector that raises is treated as validation_failed, not propagated."""
    server = importlib.import_module("konsol_mcp.server")
    backend = _ConnectorBackend(raise_on_get=True)
    monkeypatch.setattr(server, "_backend", lambda: backend)

    data = json.loads(server.provision_and_test_connector("CONN-00001"))

    assert data["status"] == "validation_failed"
    assert backend.provision_calls == []
    assert backend.test_calls == []


def test_provision_and_test_connector_dry_run_previews(monkeypatch):
    """dry_run (default) previews without provisioning or testing."""
    server = importlib.import_module("konsol_mcp.server")
    backend = _ConnectorBackend()
    monkeypatch.setattr(server, "_backend", lambda: backend)

    data = json.loads(server.provision_and_test_connector("CONN-00001"))

    assert set(data) == ENVELOPE_KEYS
    assert data["status"] == "dry_run"
    assert backend.provision_calls == []
    assert backend.test_calls == []
    assert data["next_steps"]
    assert data["affected_objects"]


def test_provision_and_test_connector_apply_success(monkeypatch):
    """dry_run=False provisions then tests once each; clean writeback => success."""
    server = importlib.import_module("konsol_mcp.server")
    backend = _ConnectorBackend()
    monkeypatch.setattr(server, "_backend", lambda: backend)

    data = json.loads(
        server.provision_and_test_connector("CONN-00001", dry_run=False)
    )

    assert data["status"] == "success"
    assert backend.provision_calls == ["CONN-00001"]
    assert backend.test_calls == ["CONN-00001"]
    assert data["affected_objects"]


def test_provision_and_test_connector_failed_writeback_warns(monkeypatch):
    """A failed write-back is surfaced as a warning with status=error."""
    server = importlib.import_module("konsol_mcp.server")
    backend = _ConnectorBackend(writeback={"ok": False, "error": "bad creds"})
    monkeypatch.setattr(server, "_backend", lambda: backend)

    data = json.loads(
        server.provision_and_test_connector("CONN-00001", dry_run=False)
    )

    assert data["status"] == "error"
    assert backend.provision_calls == ["CONN-00001"]
    assert backend.test_calls == ["CONN-00001"]


# --- M6: onboard_new_entity composite --------------------------------------


class _OnboardBackend:
    """Fake backend recording connector/dimension upserts for M6 tests."""

    def __init__(self):
        self.connectors = []  # list of upserted connector specs
        self.dimensions = []  # list of (spec, publish) tuples

    def upsert_connector(self, spec):
        self.connectors.append(spec)
        return {"name": spec.get("connector_name", "CONN-NEW"), **spec}

    def upsert_dimension(self, spec, publish=False):
        self.dimensions.append((spec, publish))
        return {"name": spec.get("dimension_name", "DIM-NEW"), **spec}


def _entity_spec(**overrides):
    spec = {
        "entity": "JPMF",
        "connector": {"connector_name": "JPMF D365", "erp_source": "d365"},
        "dimension": {"dimension_name": "Entity", "source_columns": ["dataareaid"]},
    }
    spec.update(overrides)
    return spec


def test_onboard_new_entity_validation_failed_not_dict(monkeypatch):
    """A non-dict spec is rejected before any backend call."""
    server = importlib.import_module("konsol_mcp.server")
    backend = _OnboardBackend()
    monkeypatch.setattr(server, "_backend", lambda: backend)

    data = json.loads(server.onboard_new_entity("not-a-dict"))

    assert set(data) == ENVELOPE_KEYS
    assert data["status"] == "validation_failed"
    assert data["warnings"]
    assert backend.connectors == []
    assert backend.dimensions == []


def test_onboard_new_entity_validation_failed_missing_entity(monkeypatch):
    """A spec without an entity name is rejected."""
    server = importlib.import_module("konsol_mcp.server")
    backend = _OnboardBackend()
    monkeypatch.setattr(server, "_backend", lambda: backend)

    data = json.loads(
        server.onboard_new_entity({"connector": {"connector_name": "X"}})
    )

    assert data["status"] == "validation_failed"
    assert backend.connectors == []
    assert backend.dimensions == []


def test_onboard_new_entity_validation_failed_no_objects(monkeypatch):
    """An entity with neither a connector nor a dimension is rejected."""
    server = importlib.import_module("konsol_mcp.server")
    backend = _OnboardBackend()
    monkeypatch.setattr(server, "_backend", lambda: backend)

    data = json.loads(server.onboard_new_entity({"entity": "JPMF"}))

    assert data["status"] == "validation_failed"
    assert backend.connectors == []
    assert backend.dimensions == []


def test_onboard_new_entity_dry_run_previews(monkeypatch):
    """dry_run (default) previews every object without upserting."""
    server = importlib.import_module("konsol_mcp.server")
    backend = _OnboardBackend()
    monkeypatch.setattr(server, "_backend", lambda: backend)

    data = json.loads(server.onboard_new_entity(_entity_spec()))

    assert set(data) == ENVELOPE_KEYS
    assert data["status"] == "dry_run"
    assert backend.connectors == []
    assert backend.dimensions == []
    assert data["next_steps"]
    # one entry for the connector + one for the dimension
    kinds = [obj["kind"] for obj in data["affected_objects"]]
    assert kinds.count("connector") == 1
    assert kinds.count("dimension") == 1


def test_onboard_new_entity_dry_run_multiple_dimensions(monkeypatch):
    """A ``dimensions`` list previews one entry per dimension."""
    server = importlib.import_module("konsol_mcp.server")
    backend = _OnboardBackend()
    monkeypatch.setattr(server, "_backend", lambda: backend)

    spec = {
        "entity": "JPMF",
        "dimensions": [
            {"dimension_name": "Entity"},
            {"dimension_name": "Account"},
        ],
    }
    data = json.loads(server.onboard_new_entity(spec))

    assert data["status"] == "dry_run"
    dim_keys = [o["key"] for o in data["affected_objects"] if o["kind"] == "dimension"]
    assert dim_keys == ["Entity", "Account"]
    assert backend.dimensions == []


def test_onboard_new_entity_apply_upserts_each_once(monkeypatch):
    """dry_run=False upserts each object once and does not publish by default."""
    server = importlib.import_module("konsol_mcp.server")
    backend = _OnboardBackend()
    monkeypatch.setattr(server, "_backend", lambda: backend)

    data = json.loads(server.onboard_new_entity(_entity_spec(), dry_run=False))

    assert data["status"] == "success"
    assert len(backend.connectors) == 1
    assert len(backend.dimensions) == 1
    # publish defaults to False
    assert backend.dimensions[0][1] is False
    assert data["affected_objects"]
    assert data["next_steps"]
    # no publish-gate warning when not publishing
    assert not data["warnings"]


def test_onboard_new_entity_apply_publish_propagates(monkeypatch):
    """spec.publish=True propagates to dimension upserts + adds the gate warning."""
    server = importlib.import_module("konsol_mcp.server")
    backend = _OnboardBackend()
    monkeypatch.setattr(server, "_backend", lambda: backend)

    data = json.loads(
        server.onboard_new_entity(_entity_spec(publish=True), dry_run=False)
    )

    assert data["status"] == "success"
    assert backend.dimensions[0][1] is True
    assert data["warnings"]
    assert any("publish gate" in w.lower() for w in data["warnings"])


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