# konsol-cli — session handoff

Last updated: 2026-06-19 (v0.9.0)

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

Pushed to `grynn-in/konsol` **main** — pending push for v0.9.0 (`delete_connector`, `apply_config(prune=)`):

| Layer | Functions |
|-------|-----------|
| `config_service.py` | dimensions, measures, fact tables (incl. unpublish), connectors (incl. delete), erp_sources, YAML export/apply/diff/prune, schema |
| `cli_api.py` | Whitelisted `*_api` wrappers for every `config_service` entrypoint |
| `tests/test_config_service.py` | Structural + mocked tests (30+) |

**Docker deploy rule:** `bench get-app` installs from **git HEAD**. Commit konsol before `docker compose build frappe_backend`.

---

## What was built (konsol-cli v0.9.0)

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
konsol connector list|show|create|delete
konsol source list
konsol config export|diff|apply [--prune]
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
  server.py   # 25 tools, 1:1 with cli_api
gitops/
  connectors.example.yaml
```

### Tests & CI

```bash
cd konsol_cli && .venv/bin/python -m pytest tests/ -q
cd repo/docker/frappe/konsol && PYTHONPATH=konsol .venv/bin/python -m pytest konsol/tests/test_config_service.py -q
```

GitHub Actions: `.github/workflows/ci.yml` (CLI tests + konsol config_service tests).

### MCP setup

Copy `mcp.example.json` into Cursor / Claude Desktop MCP config. Use `${KONSOL_API_KEY}` env placeholders — credentials in `~/.config/konsol/secrets.toml` (chmod 600), never in git or HANDOFF.

Grok: `grok mcp doctor konsol` — see `.grok/config.toml` in this repo.

Debug: `npx @modelcontextprotocol/inspector konsol-mcp`

### ERP wiring scripts

```bash
# After Airbyte is installed (scripts/setup-airbyte.sh):

# D365 F&O
export D365_TENANT_ID=... D365_CLIENT_ID=... D365_CLIENT_SECRET=...
export D365_ENVIRONMENT_URL=https://mycompany.operations.dynamics.com
export AIRBYTE_CONNECTION_ID=<uuid>   # optional on first run
bash repo/scripts/wire-d365-connector.sh

# ERPNext
export ERPNEXT_HOST_URL=... ERPNEXT_API_KEY=... ERPNEXT_API_SECRET=...
bash repo/scripts/wire-erpnext-connector.sh
```

Local demo stack seeds D365-shaped data in ClickHouse without a Connector — see `generate_demo_data.py`.

---

## Linear queue — status

| # | Task | Status |
|---|------|--------|
| 1–7 | Core CLI slices | Done |
| A–I | Deploy, smoke, GitOps, MCP | Done |
| J | Tag v0.8.1 | Done |
| K | `connector delete` + `config apply --prune` | Done (v0.9.0) |
| L | ERPNext wire script + staging connector | Done — Airbyte sync still manual |

---

## Recommended next steps

| Priority | Task | Why |
|----------|------|-----|
| M | Push konsol v0.9.0 + rebuild Docker | Bake delete/prune into image |
| N | Install Airbyte + run first ERPNext sync | Completes lane 3 data path |
| O | CI `config diff` against staging | GitOps guardrail |

---

## How to resume with an AI agent

```
Read konsol_cli/HANDOFF.md and continue the konsol-cli project.
Next task: [M/N/O from above].
```

---

## Decisions (don't re-litigate)

1. CLI + MCP are thin clients — logic stays in `config_service.py`
2. Not a bench site-management wrapper
3. Publish/unpublish delegate to DocType controllers
4. Connectors regenerate `erp_sources` on save (no separate publish)
5. YAML bundle keys: `dimensions`, `measures`, `fact_tables`, `connectors` (matched by `connector_name`)
6. `--prune` only affects sections **present** in the bundle; Published → unpublish, Draft/Inactive → delete (connectors always delete)

Slices completed: list → create/publish → measures → schema → ApiBackend → facts → YAML → MCP → unpublish → connectors/sources → CI/docs/git → YAML connectors → dimension/measure unpublish → delete/prune → ERPNext wire script.