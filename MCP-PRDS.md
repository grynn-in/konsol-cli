# konsol-cli MCP composite tools — PRD backlog (ralph loop)

Genuine gaps only (verified: P&L/BS/variance/`=EPM()` templates/ownership+driver macros already exist; this loop is the *new* MCP work). Context + envelope contract + loop protocol: `MCP-HANDOFF.md`. Branch `feat/mcp-composite-tools`. One PRD per agent; strict TDD (`python -m pytest tests/ -q`); each PRD reviewed ≤2× then fixed.

## P2 — structured output foundation
- [x] **M1 — `format_mcp_response` helper.** `src/konsol_mcp/responses.py` + `tests/test_mcp_responses.py`. The envelope contract in the handoff (status/message/affected_objects/diff/warnings/impact_summary/next_steps/tool_call_id; uuid4 hex when id omitted). Pure function, no I/O.
- [x] **M2 — Envelope on all existing tools.** Wrap every current `@mcp.tool()` in `server.py` so it returns `_json(format_mcp_response(...))` instead of raw `_json(data)`: reads → `status="success"`, data in `affected_objects` (lists) or `diff` (diff_config/export); mutators (upsert/publish/unpublish/apply/provision/delete) → `status="success"`, `affected_objects=[name]`, publish-gate notes in `warnings`. Extend `tests/test_mcp_server.py` to assert the envelope keys on a representative read + mutate tool. Keep tool names/signatures unchanged (backward compatible surface).

## P1 — composite tools (compose existing `ApiBackend` primitives; `dry_run=True` default)
- [x] **M3 — `apply_model_from_gitops(bundle_path, dry_run=True, publish=False, prune=False)`.** Load the bundle (mirror `commands/config.py` `_load_bundle`), call `diff_config(bundle)` → put the diff in `diff` + counts in `impact_summary`; if `dry_run` return `status="dry_run"` (no mutation); else `apply_config(bundle, publish, prune)` → `status="success"`, `affected_objects` from the diff, `next_steps` (e.g. "publish to rebuild"). Validate the path/bundle (`validation_failed` on bad input). Tests mock the backend.
- [ ] **M4 — `publish_model_changes(names=None, kinds=None, dry_run=True)`.** Discover Draft/changed models via `list_dimensions/measures/fact_tables(status="Draft")` (or the given `names`); `dry_run` → list them in `affected_objects` with `status="dry_run"`; else call the matching `publish_*` per item then `apply_schema(run_dbt=False)` → `status="success"`, warnings if nothing to publish. Tests mock the backend.
- [ ] **M5 — `provision_and_test_connector(name, dry_run=True)`.** Validate the connector exists (`get_connector`); `dry_run` → preview (`status="dry_run"`, next_steps); else `provision_connector_airbyte(name)` then `test_connector_writeback(name)` → fold both results into `affected_objects`/`diff`; surface a failed writeback as `warnings` + `status` accordingly. Tests mock the backend.
- [ ] **M6 — `onboard_new_entity(spec, dry_run=True)`.** Compose: create/ensure a connector (`upsert_connector`) + the entity's dimension(s) (`upsert_dimension`) and any source from `spec`; `dry_run` previews every object in `affected_objects` with `status="dry_run"`; else upsert each (no publish unless `spec.publish`), return `next_steps` ("publish_model_changes to go live"). Validate required `spec` fields. Tests mock the backend.

## P3 — impact preview
- [ ] **M7 — `preview_impact(bundle_path=None, names=None)` (config.preview_impact).** Read-only. Combine `diff_config` (what changes) with `get_schema_status` to report **downstream affected objects** (published models/measures/fact-tables touched) in `affected_objects` + a human `impact_summary`; always `status="dry_run"`. No mutation, no publish. If the backend lacks a true blast-radius endpoint, derive impact from the diff + schema status and note the limitation in `warnings`. Tests mock the backend.

## Backlog — NOT in this loop (need new primitives or another repo)
- **create_scenario** — needs a Scenario primitive in `ApiBackend` + a konsol Frappe API endpoint (Scenario Definition doctype exists; no CLI/MCP wrapper yet).
- **setup_driver_based_allocation** — needs Allocation primitives in `ApiBackend` (allocation_rule/driver/tier/run doctypes exist; no wrapper).
- **P4 SOCE** (Statement of Changes in Equity) — dbt model in the **konsolidat** repo (different harness); P&L/BS/variance/templates already exist.
- **multi-GAAP macros**, **scenario branching** — konsol/konsolidat; real gaps, separate effort.
