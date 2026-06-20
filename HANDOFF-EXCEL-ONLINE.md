# Excel Online add-in — session handoff

Last updated: 2026-06-20 (**resolved** — v2.0.0.0 verified on Excel Online Mac)

Point the next agent at this file first for Excel add-in / `=K.EPM()` work. Demo admin credentials live on the Hetzner server only — do not commit to git.

---

## Status: resolved

**`=K.EPM()` works on Excel Online Mac** against `https://demo.konsolidat.com` (admin-managed deploy, v2.0.0.0).

| Test | Result |
|------|--------|
| `=K.PING()` | `1` |
| `=K.EPM("AMUS", 2024, 6, "4010")` | `861245` |
| Pane auth | Token auth (`excel_addin_auth` → `localStorage` → `X-Konsolidat-Token`) |
| Diag | `associate=yes`, name registration OK |

---

## Root cause (confirmed)

**`#NAME?` was a cross-origin metadata fetch failure on Excel web**, not an `associate` or API problem.

| Layer | Symptom if broken |
|-------|-------------------|
| **`functions.json` name registration** (Excel web fetches cross-origin from `*.office.com`) | **`#NAME?`** (`names=no`) |
| **`CustomFunctions.associate`** | `#GETTING_DATA` / calc error — never `#NAME?` |
| **`epm_batch` API** | Value/auth errors — not `#NAME?` |

**Fix that unlocked registration:** Caddy `Access-Control-Allow-Origin "*"` on all `/assets/konsol/excel-addin/*` responses. Without CORS, Excel web silently failed to register `K.*` names while the same-origin iframe pane worked fine.

**Supporting fixes (still required, but did not alone fix `#NAME?`):**

- `Cache-Control: public, max-age=300` on `functions.json` (was `no-store`)
- `Content-Security-Policy: frame-ancestors *` + strip `X-Frame-Options` from Frappe
- Token auth (iframe cookies unreliable; `functions.js` uses `X-Konsolidat-Token`)
- M365 Admin Center deploy (not sideload) for Excel Online production

---

## Live deployment

| Item | Value |
|------|--------|
| **Version** | **v2.0.0.0** |
| **Manifest ID** | `c3d7e9f1-2a4b-5c6d-8e0f-1a2b3c4d5e6f` |
| **URL** | `https://demo.konsolidat.com/assets/konsol/excel-addin/` |
| **Deploy** | M365 Admin Center → Integrated apps (admin-managed) |
| **CORS** | `access-control-allow-origin: *` on `functions.json`, `functions.js`, `index.html` |

Verify CORS live:

```bash
curl -sI https://demo.konsolidat.com/assets/konsol/excel-addin/functions.json | grep -i access-control
# → access-control-allow-origin: *
```

---

## Infrastructure

| Item | Value |
|------|--------|
| Server | Hetzner `178.105.252.186`, SSH `hetzner-konsolidat` |
| Stack path | `/root/konsolidat` |
| Domain | `demo.konsolidat.com` |
| Frappe site | `konsolidat.local` |
| Container path | `/home/frappe/frappe-bench/apps/konsol/konsol/public/excel-addin/` |

**Deploy full add-in:**

```bash
konsol_cli/scripts/deploy-excel-full.sh
```

Deploy restarts `frappe_backend`, `frappe_worker`, `frappe_scheduler`. Caddy changes require `docker compose exec caddy caddy reload` (or redeploy Caddyfile via scp + reload).

---

## Source files

| Path | Role |
|------|------|
| `konsolidat/repo/excel-addin/src/index.html` | Task pane (login + diag) |
| `konsolidat/repo/excel-addin/src/functions.js` | `=K.EPM()` + token headers |
| `konsolidat/repo/excel-addin/src/functions.json` | Function metadata |
| `konsolidat/repo/excel-addin/manifest.demo.xml` | Full manifest (source of truth) |
| `konsolidat/repo/docker/caddy/Caddyfile` | CORS, framing, cache headers for add-in assets |
| `konsolidat/repo/docker/frappe/konsol/konsol/api.py` | `excel_addin_auth`, `epm_batch` |
| `konsolidat/repo/docker/frappe/konsol/konsol/excel_addin_auth.py` | Bearer tokens |

Guest/demo APIs (`excel_addin_demo`, `excel_addin_batch`, `excel_epm_plain`) and pane value-insert workarounds were **removed in v2.0.0.0** — do not re-add.

---

## User test procedure (regression)

1. New blank workbook in Excel Online
2. Open admin-managed **Konsolidat** add-in (v2.0.0.0)
3. Sign in via pane
4. `=K.PING()` → `1`
5. `=K.EPM("AMUS", 2024, 6, "4010")` → `861245`

---

## If formulas break again

Check in order:

1. **CORS** — `curl -sI …/functions.json` must show `access-control-allow-origin: *`
2. **Cache** — `functions.json` must be `public, max-age=300`; pane assets `no-cache`
3. **Auth** — pane signed in; token in `localStorage` (`konsol_token`)
4. **Deploy path** — admin-managed manifest URL matches live `manifest.xml` version
5. **Do not** retry associate retry loops, manifest GUID bumps, or pane insert workarounds

---

## Resume prompt (next agent)

```
Excel Online =K.EPM() is WORKING on demo.konsolidat.com (v2.0.0.0).
Root cause of prior #NAME?: missing CORS on add-in assets for Excel web cross-origin
functions.json fetch. Fix: Access-Control-Allow-Origin * in Caddy @excel_addin* blocks.
Verified: =K.PING()=1, =K.EPM("AMUS",2024,6,"4010")=861245 on Excel Online Mac.
Use M365 Admin Center deploy for production. Do not re-add guest APIs or pane workarounds.
```

---

## Related docs

- `konsolidat/repo/docs/prd/PRD-EXCEL-CUSTOM-FUNCTIONS.md`
- `konsolidat/repo/excel-addin/README.md`
- `konsol_cli/HANDOFF.md` — broader session context