"""Tests for the shared MCP structured-response envelope (PRD M1)."""
from __future__ import annotations

import re

from konsol_mcp.responses import format_mcp_response

EXPECTED_KEYS = {
    "status",
    "message",
    "affected_objects",
    "diff",
    "warnings",
    "impact_summary",
    "next_steps",
    "tool_call_id",
}


def test_envelope_has_exactly_the_documented_keys():
    resp = format_mcp_response("success", "ok")
    assert set(resp.keys()) == EXPECTED_KEYS


def test_defaults_are_empty_collections_and_none():
    resp = format_mcp_response("success", "ok")
    assert resp["status"] == "success"
    assert resp["message"] == "ok"
    assert resp["affected_objects"] == []
    assert resp["warnings"] == []
    assert resp["next_steps"] == []
    assert resp["diff"] is None
    assert resp["impact_summary"] is None


def test_generated_tool_call_id_is_32_char_hex_when_omitted():
    resp = format_mcp_response("success", "ok")
    tcid = resp["tool_call_id"]
    assert isinstance(tcid, str)
    assert len(tcid) == 32
    assert re.fullmatch(r"[0-9a-f]{32}", tcid)


def test_passed_tool_call_id_round_trips():
    resp = format_mcp_response("success", "ok", tool_call_id="caller-123")
    assert resp["tool_call_id"] == "caller-123"


def test_each_status_value_is_accepted():
    for status in ("success", "dry_run", "validation_failed", "error"):
        resp = format_mcp_response(status, "msg")
        assert resp["status"] == status


def test_optional_fields_round_trip():
    diff = {"added": ["a"], "removed": []}
    resp = format_mcp_response(
        "dry_run",
        "preview",
        affected_objects=["dim_a"],
        diff=diff,
        warnings=["heads up"],
        impact_summary="1 object",
        next_steps=["publish to rebuild"],
    )
    assert resp["affected_objects"] == ["dim_a"]
    assert resp["diff"] == diff
    assert resp["warnings"] == ["heads up"]
    assert resp["impact_summary"] == "1 object"
    assert resp["next_steps"] == ["publish to rebuild"]


def test_default_collections_are_not_shared_between_calls():
    first = format_mcp_response("success", "a")
    first["affected_objects"].append("mutated")
    second = format_mcp_response("success", "b")
    assert second["affected_objects"] == []
