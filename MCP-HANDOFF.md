# konsol-cli MCP composite tools — durable handoff (read me first)

You are a fresh agent. This file + `MCP-PRDS.md` are the source of truth. Do **exactly one PRD** (or one review/fix pass), then stop. No prior memory is assumed.

## Goal
Expand the konsol-cli **MCP server** with (P2) a shared structured-response envelope on every tool, and (P1) safe high-level **composite tools** that orchestrate the existing thin wrappers. The atomic primitives already exist; you compose them. All config goes through the **konsol Frappe API** via `ApiBackend` — never direct DB/dbt.

## Where things are (work in THIS worktree)
- **Worktree (cwd):** `/home/pd/konsol-cli-wt-mcp` — branch `feat/mcp-composite-tools` (never commit to main).
- **MCP server:** `src/konsol_mcp/server.py` — `FastMCP("konsol")`, ~27 `@mcp.tool()` wrappers, each returns `_json(_backend().<method>(...))`. `_backend()` builds an `ApiBackend`. `_json(data)` = `json.dumps(data, indent=2, default=str)`.
- **Backend:** `src/konsol_cli/backends/api.py` (`ApiBackend`) — the primitives the composites call: `list/get/upsert/publish/unpublish_dimension|measure|fact_table`, `apply_schema`, `get_schema_status`, `export_config`, `apply_config(bundle, publish, prune)`, `diff_config(bundle)`, `list/get/upsert/delete_connector`, `test_connector_writeback`, `provision_connector_airbyte`, `list_erp_sources`. Base interface in `backends/base.py`.
- **CLI commands** (patterns to mirror): `src/konsol_cli/commands/*.py` (config.py has the GitOps `apply --dry-run` + `diff`).
- **Tests:** `tests/` — `test_mcp_server.py`, `test_api_backend.py`, etc. `ApiBackend` is exercised with mocked HTTP; mirror that style (mock the backend / its `_call`).

## TDD harness
- Deps are already installed editable (`pip install -e ".[mcp]"`). If imports fail, run that once in the worktree.
- Run tests: `cd /home/pd/konsol-cli-wt-mcp && python -m pytest tests/ -q`. New tests go in `tests/` (e.g. `tests/test_mcp_responses.py`, extend `tests/test_mcp_server.py`).
- **Strict TDD:** write the failing test first, confirm RED, implement, GREEN, then run the FULL suite (must stay green), commit.

## The response envelope (P2 — the contract every tool/composite uses)
`format_mcp_response()` (PRD M1, in `src/konsol_mcp/responses.py`) returns a dict:
```python
{
  "status": "success" | "dry_run" | "validation_failed" | "error",
  "message": str,                 # human-readable summary
  "affected_objects": list,       # [] default — docs/objects touched or that would be
  "diff": dict | None,            # structured before/after or config diff
  "warnings": list,               # [] default
  "impact_summary": str | None,
  "next_steps": list,             # [] default
  "tool_call_id": str,            # caller-supplied, else a generated uuid4 hex
}
```
Signature: `format_mcp_response(status, message, *, affected_objects=None, diff=None, warnings=None, impact_summary=None, next_steps=None, tool_call_id=None) -> dict`. Generate `tool_call_id` with `uuid.uuid4().hex` when not provided. MCP tools serialize it with the existing `_json(...)`.

## Conventions
- Composites: **call `ApiBackend` methods** (compose, don't duplicate); **validate inputs first** (return `status="validation_failed"` with `warnings` on bad input, never raise to the caller); **respect `dry_run`** (default `True` for anything mutating — preview via `diff`/`affected_objects` with `status="dry_run"`, only mutate when `dry_run=False`); always return the envelope.
- Respect **publish gates / permissions / audit** — go through the backend's publish/apply methods; never bypass.
- Type hints + docstrings on every new function. Keep existing style.
- Backward compatible: don't rename/remove existing tools or backend methods; add new ones.
- Commit subject: `feat(mcp): M-N <title>` (or `test(mcp): ...`) + trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

## Loop protocol
**Build agent:** take the first unchecked PRD in `MCP-PRDS.md`. RED→GREEN→full-suite-green→commit→tick the PRD `[x]`→update this file's *Current state*/*Next*→commit docs→STOP. Return the status object.
**Review agent:** review ONLY that PRD's diff (`git show`/`git diff`) for correctness, safety (dry-run, validation, publish gates), envelope consistency, test quality, backward compat. Return blocking findings (empty = approved). Do not edit code.
**Fix agent:** apply the review's blocking findings, keep tests green, commit (`fix(mcp): M-N address review`), STOP.

## Current state
**Done:** M1 — `format_mcp_response` in `src/konsol_mcp/responses.py` (commit `94f1532`). **M2 — envelope on all existing tools** (commit `560844a`): every `@mcp.tool()` in `src/konsol_mcp/server.py` now returns `_json(format_mcp_response(...))` via three private helpers — `_read_list` (list/get reads → payload in `affected_objects`), `_read_diff` (`diff_config`/`export_config`/`get_schema_status`/`list_erp_sources` → payload in `diff`), and `_mutated` (upsert/publish/unpublish/delete/test/provision/apply → `affected_objects=[name]`, raw result in `diff`, `_PUBLISH_GATE_NOTE` in `warnings` for publish/unpublish/apply and publish=True upserts). `_doc_name(*candidates)` extracts the doc name from result/spec. Tool names/signatures unchanged. Tests in `tests/test_mcp_server.py` assert the 8 envelope keys on a representative read, a diff-read, and a mutate (backend monkeypatched via `server._backend`). Full suite green (33 passed). **Run tests with `rtk proxy python -m pytest tests/ -q`** — plain `python -m pytest` collected 0 tests in this env.

## Next
**M3 — `apply_model_from_gitops(bundle_path, dry_run=True, publish=False, prune=False)`** (first composite — P1). Add it as a new `@mcp.tool()` in `src/konsol_mcp/server.py` (or a `composites.py` it imports — keep server thin). Validate `bundle_path` first: missing/empty/unreadable → `status="validation_failed"` with the reason in `warnings`, never raise. Load the bundle by mirroring `commands/config.py` `_load_bundle` (look there for the exact JSON/dir loader). Call `ApiBackend.diff_config(bundle)` → put the diff in `diff` and human counts in `impact_summary`. If `dry_run` (the default): return `status="dry_run"`, no mutation, list would-be-touched objects in `affected_objects`, `next_steps=["re-run with dry_run=False to apply"]`. Else: `apply_config(bundle, publish, prune)` → `status="success"`, `affected_objects` from the diff, `next_steps` (e.g. "publish_model_changes to rebuild"). Compose existing backend methods only — don't duplicate apply logic. Strict TDD: new `tests/` cases mock the backend (monkeypatch `server._backend`) and a temp bundle file — cover validation_failed, dry_run (no apply call), and apply paths. RED→GREEN→full suite (`rtk proxy python -m pytest tests/ -q`)→commit `feat(mcp): M3 ...`. Then point *Next* at M4.
