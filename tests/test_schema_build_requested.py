"""`schema apply --run-dbt` requests a governed build; it does not run dbt
(konsol#170 review, grynn-in/konsol#392).

konsol's apply_schema now returns ``build_requested``, ``build_approval`` and
``build_approval_state`` instead of ``dbt_triggered``: a full refresh is high
risk and waits for review under the default workflow, so "triggered" was
wrong. The CLI and the MCP tool name the approval and its state.
"""
from __future__ import annotations

import importlib
import json

from typer.testing import CliRunner

SUMMARY = {
    "vars_updated": True,
    "columns_added": [],
    "facts_created": [],
    "sources_written": [],
    "budget_fields_synced": [],
    "errors": [],
    "build_requested": True,
    "build_approval": "BAPR-00042",
    "build_approval_state": "Pending Review",
}


class _Backend:
    def __init__(self, summary):
        self.summary = summary

    def apply_schema(self, run_dbt=False):
        return dict(self.summary)


def _cli_output(monkeypatch, summary):
    schema = importlib.import_module("konsol_cli.commands.schema")
    monkeypatch.setattr(schema, "get_backend", lambda ctx: _Backend(summary))
    result = CliRunner().invoke(schema.app, ["apply", "--run-dbt"])
    assert result.exit_code == 0, result.output
    return result.output


def test_the_cli_names_the_build_approval_and_its_state(monkeypatch):
    out = _cli_output(monkeypatch, SUMMARY)
    assert "dbt_triggered" not in out, out
    assert "BAPR-00042" in out and "Pending Review" in out, out


def test_the_cli_says_no_build_was_requested(monkeypatch):
    out = _cli_output(monkeypatch, dict(SUMMARY, build_requested=False, build_approval=None,
                                        build_approval_state=None))
    assert "dbt_triggered" not in out and "BAPR" not in out, out
    assert "build_requested: False" in out, out


def test_the_mcp_tool_names_the_build_approval_and_its_state(monkeypatch):
    server = importlib.import_module("konsol_mcp.server")
    monkeypatch.setattr(server, "_backend", lambda: _Backend(SUMMARY))
    data = json.loads(server.apply_schema(run_dbt=True))
    text = data["message"] + " ".join(data.get("warnings") or [])
    assert "BAPR-00042" in text and "Pending Review" in text, data
    assert data["diff"]["build_requested"] is True
