# konsol-cli

Command-line client for configuring the [konsol](https://github.com/grynn-in/konsol) Frappe app.

All configuration goes through konsol — never dbt or ClickHouse directly.

## Install

```bash
cd konsol_cli
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Optional MCP server:

```bash
pip install -e ".[mcp]"
```

## Two ways to connect

### 1. Local Docker (default)

Talks to konsol by running `bench execute` inside your Docker stack.

```bash
konsol dimension list --compose-file ../repo/docker-compose.yml
```

### 2. Remote HTTP API

Talks to any running konsol site over the Frappe API. Use this from your laptop against a remote server, in CI, or with MCP.

**First, create API keys in Frappe:**

1. Log into the site as an EPM Admin user
2. Go to **User** → your user → **Settings** tab → **API Access**
3. Click **Generate Keys** and save the key + secret

**Then run commands:**

```bash
konsol --backend api \
  --url http://localhost:8069 \
  --site konsolidat.local \
  --api-key YOUR_KEY \
  --api-secret YOUR_SECRET \
  dimension list
```

When connecting to `localhost:8069`, keep `--site` set — the CLI sends it as the `Host` header so Frappe routes to the right site.

**Optional config file** — copy `config.example.toml` to `~/.config/konsol/config.toml` so you don't pass flags every time.

## Commands

```bash
# Dimensions
konsol dimension list
konsol dimension show dim_cost_center
konsol dimension create dim_project --source-column Project --label "Project"
konsol dimension publish dim_project

# Measures
konsol measure list
konsol measure create period_headcount --expression "sum(headcount)" --label "Headcount"

# Fact tables
konsol fact list
konsol fact show headcount
konsol fact create my_fact --label "My Fact" --source-type Statistical \
  --clickhouse-table epm_staging.fact_x --scenario-key statistical
konsol fact publish my_fact
konsol fact unpublish my_fact

# Connectors & ERP sources
konsol connector list
konsol connector show CONN-00001
konsol connector create --name "ERPNext Demo" --erp-type erpnext --entity-id ENT01
konsol source list

# Config (GitOps YAML)
konsol config export -o model.yaml
konsol config diff model.yaml
konsol config apply model.yaml [--publish] [--dry-run]

# Schema
konsol schema apply
konsol schema status
```

## MCP (AI clients)

Install the optional extra, then add `mcp.example.json` to your MCP client config (Cursor, Claude Desktop, etc.):

```bash
pip install -e ".[mcp]"
```

Set `KONSOL_URL`, `KONSOL_SITE`, `KONSOL_API_KEY`, and `KONSOL_API_SECRET` in the server env block, then run `konsol-mcp` (stdio transport).

Debug with the MCP Inspector:

```bash
npx @modelcontextprotocol/inspector konsol-mcp
```

## Environment variables

| Variable | Purpose |
|----------|---------|
| `KONSOL_BACKEND` | `bench` (default) or `api` |
| `KONSOL_SITE` | Frappe site name |
| `KONSOL_URL` | Site URL for api backend |
| `KONSOL_API_KEY` | Frappe API key |
| `KONSOL_API_SECRET` | Frappe API secret |
| `KONSOL_COMPOSE_FILE` | Path to docker-compose.yml for bench backend |

## Docker deploy note

`bench get-app` installs konsol from **git HEAD**, not uncommitted files. Commit konsol changes before `docker compose build frappe_backend`.

## Architecture

```
konsol-cli / konsol-mcp
  → bench execute  or  HTTP /api/method/konsol.cli_api.*
  → konsol.config_service  →  Frappe DocTypes
  → publish / apply_schema  →  dbt vars, ClickHouse DDL, Pipeline Build Request
```

## Tests

```bash
cd konsol_cli && .venv/bin/python -m pytest tests/ -q
cd repo/docker/frappe/konsol && PYTHONPATH=konsol .venv/bin/python -m pytest konsol/tests/test_config_service.py -q
```