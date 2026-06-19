# konsol-cli — session handoff

Last updated: 2026-06-19

Use this file to resume after clearing chat context. Point the agent at **`konsol_cli/HANDOFF.md`** first.

---

## What this project is

**konsol-cli** is the CLI + MCP client for the **konsol** Frappe app (Open EPM control plane for konsolidat).

**Golden rule:** all configuration goes through konsol (Frappe DocTypes → publish → `apply_schema` → dbt/ClickHouse). Never write to dbt, ClickHouse, or SQL directly.

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
| CLI (git) | https://github.com/grynn-in/konsol-cli — `/Users/deepakpai/Documents/grynn/konsolidat/konsol_cli/` |
| konsol app (git) | https://github.com/grynn-in/konsol — `/Users/deepakpai/Documents/grynn/konsolidat/repo/docker/frappe/konsol/` |
| konsolidat stack | `/Users/deepakpai/Documents/grynn/konsolidat/repo/` (`docker-compose.yml`) |

### Pinned versions (2026-06-19)

| Artifact | Ref |
|----------|-----|
| konsol-cli **tag** | `v0.9.0` — https://github.com/grynn-in/konsol-cli/releases/tag/v0.9.0 |
| konsol-cli **main** (ahead of tag) | `827871b` — secrets.env support, credential hygiene |
| konsol app **main** | `2a53263` — delete_connector, apply_config(prune=) |
| Docker image | `repo-frappe_backend:latest` → `3566f94c05d5` (includes konsol `2a53263`) |

**Docker rule:** `bench get-app` installs from git HEAD at image build time. After konsol pushes: `docker compose build frappe_backend && docker compose up -d frappe_backend`.

---

## Install & connect

```bash
cd konsol_cli
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pip install -e ".[mcp]"   # optional
```

### Credentials (never commit, never put in HANDOFF/chat)

```
~/.config/konsol/
  config.toml      # backend, url, site (non-secret)
  secrets.env      # KONSOL_API_KEY=...  (preferred, chmod 600)
  secrets.toml     # fallback, still supported
```

```bash
cp secrets.example.env ~/.config/konsol/secrets.env && chmod 600 ~/.config/konsol/secrets.env
# Generate keys: Frappe → User → API Access → Generate Keys
```

**Precedence:** CLI flags → shell env vars → `secrets.env` → `secrets.toml`.

**Stale env trap:** if `KONSOL_API_*` are exported in the shell, they override `secrets.env`. Run `unset KONSOL_API_KEY KONSOL_API_SECRET` when debugging auth.

**Grok MCP** (before starting Grok):

```bash
source scripts/load-konsol-secrets.sh   # does not print secrets
grok mcp doctor konsol                    # expect healthy, 25 tools
```

Project MCP config: `.grok/config.toml` uses `${KONSOL_API_KEY}` placeholders (safe to commit).

### Backends

| Mode | When |
|------|------|
| `bench` (default if no config) | `--compose-file ../repo/docker-compose.yml` |
| `api` | `~/.config/konsol/config.toml` with `backend = "api"` — omit `--backend` to respect file |

---

## Commands (v0.9.0+)

```bash
konsol dimension list|show|create|publish|unpublish
konsol measure list|show|create|publish|unpublish
konsol fact list|show|create|publish|unpublish
konsol connector list|show|create|delete
konsol source list
konsol config export|diff|apply [--publish] [--prune] [--dry-run]
konsol schema apply|status
konsol-mcp
```

### GitOps bundle keys

`api_version: konsol/v1` plus: `dimensions`, `measures`, `fact_tables`, `connectors` (matched by `connector_name`).

**`--prune`:** removes `only_on_site` entities for sections **declared** in the bundle. Connectors → delete; Published dims/measures/facts → unpublish; Draft/Inactive → delete.

Examples: `gitops/connectors.example.yaml`, `gitops/d365-connector.example.yaml`.

---

## konsol app surface (`config_service.py` + `cli_api.py`)

| Area | APIs |
|------|------|
| Dimensions / measures / facts | list, get, upsert, publish, **unpublish** |
| Connectors | list, get, upsert, **delete** |
| ERP sources | list_erp_sources |
| YAML | export_config, diff_config, apply_config(**prune=**) |
| Schema | apply_schema, get_schema_status |

Tests: `konsol/tests/test_config_service.py` (30+).

---

## Live Docker state (local)

| Item | State |
|------|--------|
| Stack | `docker compose up` in `repo/` — `konsolidat_backend` healthy on `:8069` |
| Connectors | **ERPNext Staging** (`CONN-00002`, disabled, entity `DEMO-CO`) |
| `source list` | `(none)` — expected while connector disabled |
| Demo data | ClickHouse seeded with **D365-shaped** demo (`generate_demo_data.py`) — works without any Connector |
| Airbyte | **Not installed** on this machine (`abctl` absent) |

**Cleaned up:** `CLI Smoke Test` connector deleted; API keys rotated after accidental chat exposure.

---

## ERP wiring (real data path)

Both follow: **Airbyte custom source → ClickHouse `epm_raw` → dbt `stg_*` → konsol Connector → `vars.erp_sources`**.

| ERP | Airbyte source | Wire script | konsol `erp_type` |
|-----|----------------|-------------|-------------------|
| D365 F&O | `repo/source-d365-fno/` | `bash repo/scripts/wire-d365-connector.sh` | `d365_fo` |
| ERPNext | `repo/source-erpnext/` | `bash repo/scripts/wire-erpnext-connector.sh` | `erpnext` |

```bash
# 1. One-time Airbyte install
bash repo/scripts/setup-airbyte.sh

# 2. Airbyte UI (localhost:8000): load custom connector, source, ClickHouse dest, connection

# 3. Register in konsol (env vars only — never commit)
export AIRBYTE_CONNECTION_ID=<uuid>
# D365: D365_TENANT_ID, D365_CLIENT_ID, D365_CLIENT_SECRET, D365_ENVIRONMENT_URL
# ERPNext: ERPNEXT_HOST_URL, ERPNEXT_API_KEY, ERPNEXT_API_SECRET
bash repo/scripts/wire-d365-connector.sh   # or wire-erpnext-connector.sh
```

**D365 nuance:** dbt defaults to `erp_sources: [d365_fo]` for demo; ERPNext is opt-in via enabled Connector.

---

## Completed work (session log)

| ID | Task | Status |
|----|------|--------|
| 1–7 | Core CLI (dims, measures, facts, schema, YAML, MCP, connectors) | Done |
| A–I | Push, Docker rebuild, smoke tests, GitOps round-trip, MCP in Grok | Done |
| J | Tag v0.8.1 (config.toml defaults) | Done |
| K | v0.9.0: `connector delete`, `config apply --prune` | Done |
| L | ERPNext + D365 wire scripts, GitOps examples | Done |
| M | Docker rebuild with konsol `2a53263` | Done — image `3566f94c05d5` |
| P | Credential hygiene: secrets.env, no secrets in git/MCP/HANDOFF | Done — main `827871b`, not yet tagged |

### Smoke tests passed

- Bench + API: connector list/create/delete, fact/dimension/measure unpublish, config export/diff/apply/prune
- Grok: `grok mcp doctor konsol` healthy

---

## Recommended next steps

| Priority | Task | Why |
|----------|------|-----|
| **1** | Tag **v0.9.1** on konsol-cli (`827871b`) | Ship secrets.env + credential hygiene |
| **2** | Install Airbyte + first real sync | `setup-airbyte.sh` → wire script with live creds |
| **3** | CI GitOps guard | `konsol config diff gitops/model.yaml` in Actions against staging |
| **4** | Enable or remove `ERPNext Staging` | Placeholder connector on site |
| **5** | Push konsolidat wire scripts | `wire-d365-connector.sh` on branch `verify/integration` — merge to main |

---

## How to resume with an AI agent

```
Read konsol_cli/HANDOFF.md and continue the konsol-cli project.
Next task: [pick from Recommended next steps above].
```

Read first:

- `konsol_cli/HANDOFF.md` (this file)
- `konsol_cli/README.md`
- `repo/docker/frappe/konsol/konsol/config_service.py`
- `repo/docker/frappe/konsol/konsol/cli_api.py`

Quick verify:

```bash
cd konsol_cli && .venv/bin/python -m pytest tests/ -q
konsol connector list --compose-file ../repo/docker-compose.yml
```

---

## Decisions (don't re-litigate)

1. CLI + MCP are thin clients — logic stays in `config_service.py`
2. Not a bench site-management wrapper
3. Publish/unpublish delegate to DocType controllers
4. Connectors regenerate `erp_sources` on save/delete (no separate publish)
5. YAML bundle keys: `dimensions`, `measures`, `fact_tables`, `connectors`
6. `--prune` is section-scoped (only keys present in bundle)
7. **Secrets:** `secrets.env` or env vars only — never in git, HANDOFF, or committed MCP configs
8. Wire scripts read credentials from **environment** at runtime only

---

## Slices completed

list → create/publish → measures → schema → ApiBackend → facts → YAML → MCP → unpublish → connectors/sources → CI/docs/git → YAML connectors → dimension/measure unpublish → delete/prune → D365/ERPNext wire scripts → Docker smoke → GitOps round-trip → credential hygiene → secrets.env.