"""Structural tests for konsol-mcp tool surface."""
from __future__ import annotations

import importlib


def test_mcp_exposes_connector_airbyte_tools():
    server = importlib.import_module("konsol_mcp.server")
    assert callable(server.test_connector_writeback)
    assert callable(server.provision_connector_airbyte)