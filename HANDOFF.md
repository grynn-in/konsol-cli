# konsol-cli — session handoff

Last updated: 2026-06-19 (v0.8.0)

Use this file to resume work after clearing chat context. Point the agent at this file and `konsol_cli/` first.

---

## What this project is

**konsol-cli** is a command-line client for configuring the **konsol** Frappe app (Open EPM control plane for konsolidat).

**Golden rule:** all configuration goes through konsol (Frappe DocTypes → publish → `apply_schema` → dbt/ClickHouse). The CLI must never write to dbt, ClickHouse, or SQL directly.

```
konsol-cli / konsol-mcp
  → bench execute  OR  HTTP /api/method/konsol.cli_api.*
  → konsol.config_service  →  Frappe DocTypes (MariaDB)
  → publish / apply_schema  →  dbt vars, ClickHouse DDL, Pipeline Build Request
```

---

## Repos and paths

| What | Where |
|------|--------|
| CLI tool (git repo) | https://github.com/grynn-in/konsol-cli (`/Users/deepakpai/Documents/grynn/konsolidat/konsol_cli/`) |
| konsol app (local staging copy) | `/Users/deepakpai/Documents/grynn/konsolidat/repo/docker/frappe/konsol/` |
| konsol on GitHub | https://github.com/grynn-in/konsol |
| konsolidat stack | `/Users/deepakpai/Documents/grynn/konsolidat/repo/` (`docker-compose.yml`) |

---

## What was built (konsol app)

Pushed to `grynn-in/konsol` **main** (commit `bfd1c41`):

| Layer | Functions |
|-------|-----------|
| `config_service.py` | dimensions, measures, fact tables (incl. unpublish), connectors, erp_sources, YAML export/apply/diff (incl. connectors), schema |
| `cli_api.py` | Whitelisted `*_api` wrappers for every `config_service` entrypoint |
| `tests/test_config_service.py` | Structural + mocked tests (28+) |

**Docker deploy rule:** `bench get-app` installs from **git HEAD**. Commit konsol before `docker compose build frappe_backend`.

---

## What was built (konsol-cli v0.8.0)

Install:

```bash
cd konsol_cli
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pip install -e ".[mcp]"   # optional MCP server
```

### Commands

```bash
konsol dimension list|show|create|publish|unpublish
konsol measure list|show|create|publish|unpublish
konsol fact list|show|create|publish|unpublish
konsol connector list|show|create
konsol source list
konsol config export|diff|apply
konsol schema apply|status
konsol-mcp   # stdio MCP server (API backend)
```

### Architecture

```
src/konsol_cli/
  main.py, settings.py, output.py
  backends/   bench.py, api.py
  commands/   dimension, measure, fact, connector, source, config, schema
src/konsol_mcp/
  server.py   # 24 tools, 1:1 with cli_api
```

### Tests & CI

```bash
cd konsol_cli && .venv/bin/python -m pytest tests/ -q
cd repo/docker/frappe/konsol && PYTHONPATH=konsol .venv/bin/python -m pytest konsol/tests/test_config_service.py -q
```

GitHub Actions: `.github/workflows/ci.yml` (CLI tests + konsol config_service tests).

### MCP setup

Copy `mcp.example.json` into Cursor / Claude Desktop MCP config. Set `KONSOL_URL`, `KONSOL_SITE`, `KONSOL_API_KEY`, `KONSOL_API_SECRET`.

Debug: `npx @modelcontextprotocol/inspector konsol-mcp`

---

## Linear queue (1–7) — status

| # | Task | Status |
|---|------|--------|
| 1 | Push konsol to `grynn-in/konsol` main | Done (`d618392`) |
| 2 | Init git for `konsol_cli/`, commit v0.7.0 | Done — https://github.com/grynn-in/konsol-cli (`8e2e9cc`) |
| 3 | Update README + HANDOFF | Done |
| 4 | CI smoke test in GitHub Actions | Done (`.github/workflows/ci.yml`) |
| 5 | MCP config snippet + Inspector | Done (`mcp.example.json`, README) |
| 6 | `konsol fact unpublish` | Done |
| 7 | Connector + source commands | Done (`connector list/show/create`, `source list`) |

---

## Recommended next steps

| Priority | Task | Why |
|----------|------|-----|
| A | Push konsol v0.7.0 + publish `grynn-in/konsol-cli` | Done |
| B | Rebuild Docker image after konsol push | Done — image `685b1e04e3be` (v0.8.0) |
| C | Smoke-test `fact unpublish`, `connector list/create`, `source list` on live Docker | Done (2026-06-19) |
| D | Add connectors to YAML export/apply bundle | Done (v0.8.0) |
| E | `dimension/measure unpublish` CLI commands | Done (v0.8.0) |
| F | Push konsol v0.8.0 + rebuild Docker + publish `konsol-cli` v0.8.0 | Done — image `685b1e04e3be`, API smoke passed |
| G | Git tag + release v0.8.0 | Done — tag `v0.8.0` on GitHub |
| H | GitOps round-trip (connector in YAML) | Done — enable + legal entity via apply |
| I | MCP wired in Grok | Done — `grok mcp doctor konsol` healthy, 24 tools |

---

## How to resume with an AI agent

```
Read konsol_cli/HANDOFF.md and continue the konsol-cli project.
Next task: [connector delete CLI, config.toml-only workflow, or production deploy].
```

Read first:
- `konsol_cli/HANDOFF.md`
- `konsol_cli/README.md`
- `repo/docker/frappe/konsol/konsol/config_service.py`
- `repo/docker/frappe/konsol/konsol/cli_api.py`

---

## Decisions (don't re-litigate)

1. CLI + MCP are thin clients — logic stays in `config_service.py`
2. Not a bench site-management wrapper
3. Publish/unpublish delegate to DocType controllers
4. Connectors regenerate `erp_sources` on save (no separate publish)
5. YAML bundle keys: `dimensions`, `measures`, `fact_tables`, `connectors` (matched by `connector_name`)

Slices completed: list → create/publish → measures → schema → ApiBackend → facts → YAML → MCP → unpublish → connectors/sources → CI/docs/git → YAML connectors → dimension/measure unpublish.