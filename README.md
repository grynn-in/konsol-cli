# konsol-cli

Config-as-code and schema client for the [konsol](https://github.com/grynn-in/konsol) Frappe app.

konsol-cli does two things:

- **config**: export a site's configuration (dimensions, measures, datasets, connectors) to a YAML or JSON file, diff a file against a site, and apply a file to a site.
- **schema**: apply the published configuration to the warehouse, and show its status.

To create, edit, publish or delete one dimension, measure, dataset or connector, use the Frappe Desk or the generic Frappe client `frappectl`. konsol-cli no longer has commands for that work (konsol#379).

konsol-cli calls these five konsol endpoints, and no others:

| Endpoint | HTTP | Used by |
|----------|------|---------|
| `konsol.cli_api.export_config_api` | GET | `config export` |
| `konsol.cli_api.diff_config_api` | POST | `config diff`, `config apply --dry-run` |
| `konsol.cli_api.apply_config_api` | POST | `config apply` |
| `konsol.cli_api.apply_schema_api` | POST | `schema apply` |
| `konsol.cli_api.get_schema_status_api` | GET | `schema status` |

Writes are POST because Frappe rolls back a GET request. `diff_config_api` writes nothing, but the bundle goes in a POST body because it is too large for a query string.

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
konsol --compose-file ../repo/docker-compose.yml schema status
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
  schema status
```

When connecting to `localhost:8069`, keep `--site` set — the CLI sends it as the `Host` header so Frappe routes to the right site.

**Optional config file** — copy `config.example.toml` to `~/.config/konsol/config.toml` (connection settings only).

**Credentials (pick one, never commit):**

```bash
cp secrets.example.env ~/.config/konsol/secrets.env && chmod 600 ~/.config/konsol/secrets.env
# or: secrets.example.toml → ~/.config/konsol/secrets.toml
```

The CLI loads `secrets.env` first, then `secrets.toml`. Shell env vars take precedence.

**Grok MCP** — configs use `${KONSOL_API_KEY}` placeholders. Before starting Grok:

```bash
source scripts/load-konsol-secrets.sh   # exports vars, does not print them
grok mcp doctor konsol
```

See `.grok/config.toml` (project-scoped, safe to commit) — not plaintext secrets.

## Commands

```bash
# Config (GitOps YAML)
konsol config export -o model.yaml
konsol config diff model.yaml
konsol config apply model.yaml [--publish] [--prune] [--dry-run]

# Schema
konsol schema apply [--run-dbt]
konsol schema status
```

## MCP (AI clients)

Install the optional extra, then add `mcp.example.json` to your MCP client config (Cursor, Claude Desktop, etc.):

```bash
pip install -e ".[mcp]"
```

Set `KONSOL_URL`, `KONSOL_SITE`, `KONSOL_API_KEY`, and `KONSOL_API_SECRET` in the server env block, then run `konsol-mcp` (stdio transport).

The server has seven tools. Each one calls only the five endpoints above:

| Tool | What it does |
|------|--------------|
| `export_config` | Export the site configuration as a bundle. |
| `diff_config` | Diff a bundle against the site. |
| `apply_config` | Apply a bundle (`publish`, `prune`). |
| `apply_schema` | Apply the published configuration to the warehouse. |
| `get_schema_status` | Show registry counts and build requests. |
| `apply_model_from_gitops` | Diff a bundle file, then apply it when `dry_run=False` (default `True`). |
| `preview_impact` | Read-only: diff a bundle file and show the schema status. |

The tools for single dimensions, measures, datasets and connectors, and the composites built on them (`publish_model_changes`, `provision_and_test_connector`, `onboard_new_entity`), were removed in v0.11.0.

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
  → bench execute  or  HTTP /api/method/konsol.cli_api.<five endpoints>
  → konsol.config_service  →  Frappe DocTypes
  → publish / apply_schema  →  dbt vars, ClickHouse DDL, Pipeline Build Request
```

## Tests

```bash
cd konsol_cli && .venv/bin/python -m pytest tests/ -q
cd repo/docker/frappe/konsol && PYTHONPATH=konsol .venv/bin/python -m pytest konsol/tests/test_config_service.py -q
```