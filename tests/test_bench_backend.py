"""Tests for the bench transport backend."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from konsol_cli.backends.bench import BenchBackend
from konsol_cli.backends.errors import BackendError
from konsol_cli.settings import Settings


def _settings(compose_file: str = "/tmp/docker-compose.yml") -> Settings:
    return Settings(
        backend="bench",
        site="konsolidat.local",
        compose_file=compose_file,
        compose_service="frappe_backend",
        url=None,
        api_key=None,
        api_secret=None,
    )


def test_bench_backend_requires_compose_file():
    with pytest.raises(BackendError, match="compose_file is required"):
        BenchBackend(_settings(compose_file=None))


def test_list_dimensions_calls_bench_execute(monkeypatch):
    backend = BenchBackend(_settings())
    captured: dict = {}

    def fake_run(command, check, capture_output, text):
        captured["command"] = command
        result = MagicMock()
        result.returncode = 0
        result.stdout = json.dumps([{"dimension_name": "dim_cost_center"}])
        result.stderr = ""
        return result

    monkeypatch.setattr("konsol_cli.backends.bench.subprocess.run", fake_run)

    rows = backend.list_dimensions(status="Published")

    assert rows == [{"dimension_name": "dim_cost_center"}]
    command = captured["command"]
    assert command[0:3] == ["docker", "compose", "-f"]
    assert command[3] == "/tmp/docker-compose.yml"
    assert "exec" in command
    assert "frappe_backend" in command
    assert "konsol.cli_api.list_dimensions_api" in command
    assert command[-2:] == ["--kwargs", json.dumps({"status": "Published"})]


def test_parse_output_supports_python_literal(monkeypatch):
    backend = BenchBackend(_settings())

    def fake_run(command, check, capture_output, text):
        result = MagicMock()
        result.returncode = 0
        result.stdout = "[{'measure_name': 'period_net_amount'}]"
        result.stderr = ""
        return result

    monkeypatch.setattr("konsol_cli.backends.bench.subprocess.run", fake_run)

    rows = backend.list_measures()

    assert rows == [{"measure_name": "period_net_amount"}]


def test_bench_execute_failure_raises(monkeypatch):
    backend = BenchBackend(_settings())

    def fake_run(command, check, capture_output, text):
        result = MagicMock()
        result.returncode = 1
        result.stdout = ""
        result.stderr = "site not found"
        return result

    monkeypatch.setattr("konsol_cli.backends.bench.subprocess.run", fake_run)

    with pytest.raises(BackendError, match="site not found"):
        backend.list_dimensions()


def test_serialize_bench_kwargs_uses_python_literals():
    payload = BenchBackend._serialize_bench_kwargs(
        {"publish": False, "spec": {"in_budget": True, "label": None}}
    )
    assert payload == (
        '{"publish": False, "spec": {"in_budget": True, "label": None}}'
    )


def test_upsert_dimension_passes_spec_and_publish(monkeypatch):
    backend = BenchBackend(_settings())
    captured: dict = {}

    def fake_run(command, check, capture_output, text):
        captured["command"] = command
        result = MagicMock()
        result.returncode = 0
        result.stdout = json.dumps({"created": True, "published": False, "dimension": {}})
        result.stderr = ""
        return result

    monkeypatch.setattr("konsol_cli.backends.bench.subprocess.run", fake_run)

    spec = {
        "dimension_name": "dim_project",
        "source_column": "Project",
        "label": "Project",
    }
    backend.upsert_dimension(spec, publish=False)

    kwargs_text = captured["command"][-1]
    assert '"publish": False' in kwargs_text
    assert "dim_project" in kwargs_text
    assert "konsol.cli_api.upsert_dimension_api" in captured["command"]


def test_upsert_measure_calls_bench_execute(monkeypatch):
    backend = BenchBackend(_settings())
    captured: dict = {}

    def fake_run(command, check, capture_output, text):
        captured["command"] = command
        result = MagicMock()
        result.returncode = 0
        result.stdout = json.dumps({"created": True, "published": False, "measure": {}})
        result.stderr = ""
        return result

    monkeypatch.setattr("konsol_cli.backends.bench.subprocess.run", fake_run)

    backend.upsert_measure(
        {
            "measure_name": "period_headcount",
            "expression": "sum(headcount)",
            "label": "Headcount",
        }
    )

    assert "konsol.cli_api.upsert_measure_api" in captured["command"]


def test_apply_schema_calls_bench_execute(monkeypatch):
    backend = BenchBackend(_settings())
    captured: dict = {}

    def fake_run(command, check, capture_output, text):
        captured["command"] = command
        result = MagicMock()
        result.returncode = 0
        result.stdout = json.dumps({"vars_updated": True, "errors": []})
        result.stderr = ""
        return result

    monkeypatch.setattr("konsol_cli.backends.bench.subprocess.run", fake_run)

    summary = backend.apply_schema(run_dbt=True)

    assert summary["vars_updated"] is True
    assert "konsol.cli_api.apply_schema_api" in captured["command"]
    assert '"run_dbt": True' in captured["command"][-1]


def test_get_schema_status_calls_bench_execute(monkeypatch):
    backend = BenchBackend(_settings())

    def fake_run(command, check, capture_output, text):
        result = MagicMock()
        result.returncode = 0
        result.stdout = json.dumps({"registry": {}, "pending_builds": [], "recent_builds": []})
        result.stderr = ""
        return result

    monkeypatch.setattr("konsol_cli.backends.bench.subprocess.run", fake_run)

    status = backend.get_schema_status()

    assert status["pending_builds"] == []


def test_list_fact_tables_calls_bench_execute(monkeypatch):
    backend = BenchBackend(_settings())
    captured: dict = {}

    def fake_run(command, check, capture_output, text):
        captured["command"] = command
        result = MagicMock()
        result.returncode = 0
        result.stdout = json.dumps([{"fact_name": "headcount"}])
        result.stderr = ""
        return result

    monkeypatch.setattr("konsol_cli.backends.bench.subprocess.run", fake_run)

    rows = backend.list_fact_tables()

    assert rows == [{"fact_name": "headcount"}]
    assert "konsol.cli_api.list_fact_tables_api" in captured["command"]


def test_export_config_calls_bench_execute(monkeypatch):
    backend = BenchBackend(_settings())

    def fake_run(command, check, capture_output, text):
        result = MagicMock()
        result.returncode = 0
        result.stdout = json.dumps({"api_version": "konsol/v1", "dimensions": []})
        result.stderr = ""
        return result

    monkeypatch.setattr("konsol_cli.backends.bench.subprocess.run", fake_run)

    bundle = backend.export_config(status="Published")

    assert bundle["api_version"] == "konsol/v1"