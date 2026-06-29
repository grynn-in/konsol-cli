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
**Done:** M1 — `format_mcp_response` in `src/konsol_mcp/responses.py` (commit `94f1532`). M2 — envelope on all existing tools (commit `560844a`): every `@mcp.tool()` returns `_json(format_mcp_response(...))` via `_read_list`/`_read_diff`/`_mutated` helpers; `_doc_name(*candidates)` extracts the doc name. **M3 — `apply_model_from_gitops` (first P1 composite)** (commit `76fb66a`): new `@mcp.tool()` in `src/konsol_mcp/server.py`. Validates `bundle_path` first (empty / not-a-file / unparseable / empty-dict → `status="validation_failed"` with the reason in `warnings`, never raises — no backend call). Loads YAML/JSON via `_load_bundle_file` (mirrors `commands/config.py` `_load_bundle`). Composes `backend.diff_config(bundle)` → flattens to `affected_objects` via `_bundle_affected_objects` (one `{kind,key,change}` dict per added/modified/only_on_site item across the 4 sections `dimensions/measures/fact_tables/connectors`) + `_bundle_impact_summary` (per-section `+a ~m -o` counts) in `impact_summary`. `dry_run=True` (default) → `status="dry_run"`, full diff in `diff`, `next_steps=["re-run with dry_run=False to apply"]`, **no `apply_config` call**. `dry_run=False` → `backend.apply_config(bundle, publish, prune)` → `status="success"`, apply summary in `diff`, `_PUBLISH_GATE_NOTE` in `warnings` when `publish=True`, `next_steps=["publish_model_changes to rebuild"]`. New imports in server.py: `pathlib.Path`, `yaml`. Tests in `tests/test_mcp_server.py` (4 new) monkeypatch `server._backend` + use a temp bundle file: validation_failed (missing file + empty path), dry_run (asserts `apply_calls == []`), apply path. **M4 — `publish_model_changes(names=None, kinds=None, dry_run=True)`** (commit `9263efb`): new `@mcp.tool()` in `src/konsol_mcp/server.py`. Validates first — `names` not a list / `kinds` not a list / unknown kind → `status="validation_failed"` (reason in `warnings`), never raises, **no backend call**. Discovers Draft models per selected kind via `backend.list_dimensions/list_measures/list_fact_tables(status="Draft")` (kinds default to all of `_MODEL_KINDS=("dimension","measure","fact_table")`; module maps `_LIST_BY_KIND`/`_PUBLISH_BY_KIND` translate kind→backend method); names extracted with the existing `_doc_name`. When `names` given, the discovered items are filtered to that allow-list (kind comes from discovery, not guessed). Nothing discovered → `status="success"`, `warnings=["nothing to publish"]`, empty `affected_objects`, no mutation. `dry_run=True` (default) → `status="dry_run"`, `affected_objects=[{kind,key}, ...]`, `next_steps=["re-run with dry_run=False to publish"]`, **no publish/apply**. `dry_run=False` → calls the matching `backend.publish_*(key)` per item, then `backend.apply_schema(run_dbt=False)` **once** → `status="success"`, `affected_objects`=published names (plain strings), `_PUBLISH_GATE_NOTE` in `warnings`. Tests (8 new in `tests/test_mcp_server.py`) use a `_PublishBackend` fake recording `published`/`apply_schema_calls`: validation_failed (bad kinds + bad names), dry_run (no mutation), kinds filter, apply path (publish per item + one apply_schema), explicit names, nothing-to-publish. Full suite green (**44 passed**). **Run tests with `rtk proxy python -m pytest tests/ -q`** — plain `python -m pytest` collected 0 tests in this env.

## Next
**M5 — `provision_and_test_connector(name, dry_run=True)`** (P1 composite). Add as a new `@mcp.tool()` in `src/konsol_mcp/server.py`. Validate the connector exists first via `backend.get_connector(name)` — empty/blank `name`, or a get that returns nothing / raises → `status="validation_failed"` with the reason in `warnings`, never raise (wrap the `get_connector` call in try/except and treat a missing connector as validation_failed). `dry_run=True` (default): preview only → `status="dry_run"`, the connector in `affected_objects`, `next_steps=["re-run with dry_run=False to provision and test"]`, **no `provision_*`/`test_*` call**. `dry_run=False`: call `backend.provision_connector_airbyte(name)` then `backend.test_connector_writeback(name)`; fold both results into the envelope (e.g. provision summary in `diff`, connector in `affected_objects`). A failed write-back (inspect the test result — e.g. a falsy `ok`/`success` flag or an `error` key) → surface it in `warnings` and set `status` accordingly (e.g. keep `status="error"` or `status="success"` with a warning — pick one and document it); a clean run → `status="success"`. Compose existing backend methods only; don't bypass provisioning/test primitives. Strict TDD: new `tests/test_mcp_server.py` cases mock `server._backend` (a fake with `get_connector`, `provision_connector_airbyte`, `test_connector_writeback` + counters) — cover validation_failed (missing connector), dry_run (no provision/test calls), apply path (both called once, success), and a failed-writeback path (warning surfaced). RED→GREEN→full suite (`rtk proxy python -m pytest tests/ -q`)→commit `feat(mcp): M5 ...`. Then point *Next* at M6.
