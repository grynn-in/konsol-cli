"""Shared structured-response envelope for konsol MCP tools (PRD M1).

Every MCP tool and composite returns the dict produced by
:func:`format_mcp_response`, giving callers a stable, predictable shape
regardless of which underlying operation ran. This module is a pure
function with no I/O so it can be unit-tested in isolation and reused by
both thin wrappers and high-level composites.
"""
from __future__ import annotations

import uuid
from typing import Any

# The full set of status values a tool may report.
STATUS_VALUES = ("success", "dry_run", "validation_failed", "error")


def format_mcp_response(
    status: str,
    message: str,
    *,
    affected_objects: list | None = None,
    diff: dict | None = None,
    warnings: list | None = None,
    impact_summary: str | None = None,
    next_steps: list | None = None,
    tool_call_id: str | None = None,
) -> dict[str, Any]:
    """Build the standard MCP response envelope.

    Args:
        status: One of ``success``, ``dry_run``, ``validation_failed`` or
            ``error``. Not enforced, but callers should use these values.
        message: Human-readable summary of what happened (or would happen).
        affected_objects: Docs/objects touched or that would be touched.
            Defaults to an empty list.
        diff: Structured before/after or config diff, or ``None``.
        warnings: Non-fatal warnings (e.g. publish-gate notes). Defaults to
            an empty list.
        impact_summary: Optional human-readable impact description.
        next_steps: Suggested follow-up actions. Defaults to an empty list.
        tool_call_id: Caller-supplied correlation id. When omitted a fresh
            ``uuid.uuid4().hex`` (32-char hex) is generated.

    Returns:
        A dict with exactly these keys: ``status``, ``message``,
        ``affected_objects``, ``diff``, ``warnings``, ``impact_summary``,
        ``next_steps``, ``tool_call_id``.
    """
    return {
        "status": status,
        "message": message,
        "affected_objects": affected_objects if affected_objects is not None else [],
        "diff": diff,
        "warnings": warnings if warnings is not None else [],
        "impact_summary": impact_summary,
        "next_steps": next_steps if next_steps is not None else [],
        "tool_call_id": tool_call_id if tool_call_id is not None else uuid.uuid4().hex,
    }
