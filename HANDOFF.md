# Konsolidat / konsol — session handoff

Last updated: 2026-06-20 (hot-deploy @ 31db0fa + writeback smoke)

Point the next agent at this file first. Credentials: `~/.config/konsol/secrets.env` only — never in git, HANDOFF, or chat.

**Excel Online add-in (`=K.EPM()`):** see **[HANDOFF-EXCEL-ONLINE.md](./HANDOFF-EXCEL-ONLINE.md)** — **resolved** v2.0.0.0 on Excel Online Mac; fix was Caddy `Access-Control-Allow-Origin *` on add-in assets (cross-origin `functions.json` fetch).

---

## Executive summary

| Track | Status |
|-------|--------|
| **Product (EPM engine)** | Strong — consolidation, allocations, Excel, dbt assertions on `grynn-in/konsolidat` main |
| **konsol control plane** | PR stack **#34 → #36 → #35 merged** to `main` @ `31db0fa` |
| **konsol-cli** | **v0.10.0** on GitHub; MCP tools for writeback/Airbyte provision |
| **ERP connectors (data)** | D365 F&O + ERPNext Airbyte sources + dbt adapters; **SAP not built** |
| **Live tenant proof** | ERPNext loopback **pass** (CONN-00001); D365 OAuth **blocked** — no sandbox creds in `.env` |
| **GTM (konsolidat.com)** | **Out of scope here** — Claude working on `sites/www` + `sites/docs` separately |
| **Revenue** | 2 SAP leads inbound; founder is D365 consultant — sell **hub + pilot-funded spokes** |

---

## Repos (verified 2026-06-20)

| Repo | Remote | Local path | `main` SHA | Notes |
|------|--------|------------|------------|-------|
| **konsolidat** | `grynn-in/konsolidat` | `.../konsolidat/repo/` | `9b8681a` | Stack, dbt, Airbyte sources, demo seeds |
| **konsol** | `grynn-in/konsol` | `.../repo/docker/frappe/konsol/` | `31db0fa` | Frappe app; Connector v2 + Airbyte provision + writeback resolver on `main` |
| **konsol-cli** | `grynn-in/konsol-cli` | `.../konsolidat/konsol_cli/` | `6986f68` | Tag **v0.10.0** pushed |
| **konsolidat.com** | (Netlify / `sites/www`) | `.../konsolidat/sites/www/` | — | **Out of scope** — Claude owns www/docs GTM |

---

## What's done (code)

### grynn-in/konsolidat (`main`)

- Docker stack (`docker-compose.yml`), `deploy.sh`, Caddy, ClickHouse, Cube.js, Frappe
- **85+ dbt models**, 26 assertion categories, D365-shaped **demo seeds** (works without live ERP)
- **Airbyte sources:** `source-d365-fno/`, `source-erpnext/` (custom connectors)
- **dbt staging adapters:** `staging/d365_fo/`, `staging/erpnext/`, `staging/canonical/`
- Excel add-in (`excel/`), docs site (`sites/docs` → docs.konsolidat.com)
- **Not in repo:** `wire-d365-connector.sh` / `wire-erpnext-connector.sh` (HANDOFF previously claimed these — **they do not exist**)
- **Not in repo:** `source-sap-s4hana/`, `staging/sap_s4/` (PRD only)

### grynn-in/konsol (`main` @ `31db0fa`)

- Full Frappe EPM app: dimensions, measures, facts, connectors, consolidation, allocations, budget
- **D365 budget write-back** (`d365_writeback.py`) — now resolves config from Connector by entity (`writeback_config.py`, PR #35)
- **Connector credential profiles** — separate extract/writeback creds on Connector DocType (PR #34)
- **Airbyte provision** — `airbyte_service.py`, extract check, provision + test APIs, `connector.js` UI (PR #36)
- `cli_api` + `config_service`: dimensions, measures, facts, connectors, YAML GitOps, prune
- Excel add-in sync (#33)

**Merged 2026-06-20** (order: #34 → #36 → #35; retargeted #36/#35 base to `main` before merge):

| PR | Scope |
|----|-------|
| [#34](https://github.com/grynn-in/konsol/pull/34) | Extract/writeback credential profiles; `connector_credentials.py`; migration patch |
| [#36](https://github.com/grynn-in/konsol/pull/36) | `airbyte_service.py`, `extract_check.py`, provision + test extract/writeback APIs, `connector.js` |
| [#35](https://github.com/grynn-in/konsol/pull/35) | `writeback_config.py`; `get_config(entity_id)` → Connector; budget_input entity-scoped |

**19 tests** pass on connector/airbyte/writeback suites (local `main` @ `31db0fa`).

**Unblocks:** konsol-cli v0.10.0 MCP tools `test_connector_writeback` / `provision_connector_airbyte` once site is rebuilt from `main`.

### grynn-in/konsol-cli (`main` @ `6986f68`, tag `v0.10.0`)

- CLI: dimension/measure/fact/connector/config/schema/source commands
- MCP: +`test_connector_writeback`, +`provision_connector_airbyte` (v0.10.0)
- `secrets.env` credential hygiene; **23 tests** passing
- GitHub **release** may lag tag (tag `v0.10.0` on remote; latest GitHub Release may still show v0.9.0)

---

## What's done (ops / smoke)

**Deploy (2026-06-20):**
- `docker compose build frappe_backend` **failed** — PyPI timeout inside Docker (`setuptools` fetch). Workaround: **hot-copied** `docker/frappe/konsol` @ `31db0fa` into `konsolidat_backend`, `bench migrate`, restart.
- Fresh `repo_frappe_sites` volume — new site `konsolidat.local`. Frappe API keys regenerated; `~/.config/konsol/secrets.env` synced.

**Writeback smoke (konsol-cli API + MCP `test_connector_writeback`):**
| Connector | Result |
|-----------|--------|
| `CONN-00001` ERPNext loopback (`http://localhost:8069`) | **pass** — credentials validated |
| `CONN-00002` D365 F&O placeholder | **fail** (expected) — `D365 connection error` (no real tenant creds) |
| `resolve_d365_writeback_config("USMF")` | **pass** — resolves from Connector `CONN-00002`, `source=connector` |

**D365 live proof still needs:** uncomment/set `D365_TENANT_ID`, `D365_CLIENT_ID`, `D365_CLIENT_SECRET`, `D365_ENVIRONMENT_URL` in `repo/.env`, update `CONN-00002` creds, rerun `test_connector_writeback CONN-00002`, then one budget push.

- **Airbyte:** not installed locally (`abctl` absent)
- Smoke connectors on local site — clean up before prod

---

## GTM / konsolidat.com (gap vs plan)

**Strong:** problem/solution, technical depth, SAP BPC landing, 146-feature comparison, MIT story, Calendly CTA.

**Weak / overstated:**

| Site claim | Reality |
|------------|---------|
| SAP connector ✓ / Live | **PRD only** — pilot-funded build |
| D365 F&O "Live" | Extract adapter exists; **live tenant writeback unproven** |
| Hosted pricing | "Contact us" only — **no $3.5K/mo anchor, no POC SKU** |
| konsol-cli / GitOps / MCP | **Not marketed** |

**Out of scope for this workspace.** Claude is executing `sites/www/` GTM (pilot page, honest ERP badges, D365 landing, implementer page). Do not edit www/docs from konsol-cli sessions.

---

## Business model (sharpened)

**One product (hub):** Excel-native consolidation + planning + assertions — ERP-agnostic.

**Connector packs (spokes):**

| ERP | Product status | GTM status |
|-----|----------------|------------|
| D365 F&O | **Available** (extract + writeback code) | Underplayed on site |
| ERPNext | **Available** | Demo / dev |
| SAP S/4 | **Not built** | **2 leads** — sell **4-week pilot** that funds adapter |
| SAP ECC / D365 BC / SAP B1 | Roadmap | Do not sell |

**Funnel:** SEO/docs/GitHub → Calendly → **Paid pilot ($25K+)** → **Hosted MRR ($3.5K+/mo)**.

**Founder constraint:** D365 consulting credibility; SAP delivery via pilot scope + partner/basis contact — not pretending self-serve SAP.

---

## Priority next steps

| # | Task | Owner | Unblocks |
|---|------|-------|----------|
| **1** | ~~Merge konsol PR #34 → #36 → #35~~ **done** | Dev | — |
| **2** | ~~Hot-deploy konsol @ `31db0fa`~~ **done**; **image rebuild** still blocked (Docker→PyPI timeout) | Dev | Reproducible deploy |
| **3** | **`sites/www` GTM** (pilot pricing, honest ERP status) | Claude (out of scope here) | SAP leads + procurement |
| **4** | **D365 live proof** — add sandbox creds to `.env` → update `CONN-00002` → `test_connector_writeback` + budget push | Dev + founder | D365 velocity lane |
| **5** | **SAP lead 1 pilot SOW** — 4-week scope, customer OData checklist | Founder | Revenue + `source-sap-s4hana` |
| **6** | Publish **v0.10.0 GitHub Release** (if tag-only) | Dev | CLI consumers |
| **7** | Update this HANDOFF after each merge | Either | Context continuity |

**Deprioritize until pilot revenue:** broad SAP ECC/BC, wire shell scripts (never existed), Airbyte on laptop (use pilot env).

---

## Quick verify

```bash
# konsol-cli
cd konsol_cli && .venv/bin/python -m pytest tests/ -q

# konsol PR branch tests
cd repo/docker/frappe/konsol && .venv/bin/pytest konsol/tests/test_connector_credentials.py \
  konsol/tests/test_airbyte_service.py konsol/tests/test_writeback_config.py -q

# PR status
gh pr list --repo grynn-in/konsol --state open

# Live site (after merge + deploy)
source ~/.config/konsol/secrets.env  # or load-konsol-secrets.sh
konsol --backend api connector list
```

---

## Architecture (unchanged golden rule)

```
konsol-cli / konsol-mcp
  → bench execute  OR  HTTP /api/method/konsol.cli_api.*
  → konsol.config_service  →  Frappe DocTypes
  → publish / apply_schema  →  dbt vars, ClickHouse DDL
```

Never configure dbt/ClickHouse/SQL directly from the CLI.

---

## Decisions (don't re-litigate)

1. Multi-ERP **marketing** yes; multi-ERP **self-serve** only for D365 F&O + ERPNext today
2. SAP S/4 adapter is **pilot-funded**, not pre-build
3. Connector extract ≠ writeback credentials (separate profiles on Connector)
4. Secrets: `secrets.env` / env vars only
5. konsolidat.com must **not** claim SAP connector is live until `source-sap-s4hana` ships
6. **SSO is Frappe-native** (OIDC / SAML / LDAP incl. Entra ID). Per-client IdP config during onboarding **is** the product — same as every enterprise EPM; it cannot be more turnkey than that. Fresh `deploy.sh` uses local `Administrator`; hosted/pilot wires the customer's Entra/OIDC. Site ✓ is correct.

---

## Resume prompts

**Engineering:**
```
Read konsol_cli/HANDOFF.md. Fix Docker→PyPI build (or bake image in CI), add D365 sandbox creds to repo/.env, rerun test_connector_writeback CONN-00002 + budget push.
```

**GTM (Claude — not this repo):**
```
sites/www + sites/docs only. See Claude session. Do not touch from konsol-cli workspace.
```

**SAP pilot:**
```
Read konsol_cli/HANDOFF.md. Draft 4-week SAP S/4 pilot SOW from PRD-SAP-S4HANA-CONNECTOR.md + customer OData checklist.
```