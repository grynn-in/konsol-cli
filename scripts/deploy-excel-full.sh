#!/usr/bin/env bash
# Deploy full Excel add-in (custom functions + task pane) to demo.konsolidat.com.
# Source: grynn-in/konsol → konsol/public/excel-addin/ + konsol/*.py
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
KONSOL_APP="${ROOT}/konsolidat/repo/docker/frappe/konsol"
ADDIN="${KONSOL_APP}/konsol/public/excel-addin"
KONSOL_PY="${KONSOL_APP}/konsol"
REPO="${ROOT}/konsolidat/repo"
SSH_HOST="${KONSOL_SSH_HOST:-hetzner-konsolidat}"
REMOTE_DIR="/root/konsolidat"
SITE="${KONSOL_SITE:-konsolidat.local}"
CONTAINER_PATH="/home/frappe/frappe-bench/apps/konsol/konsol"
DEST="${CONTAINER_PATH}/public/excel-addin"

if [[ ! -f "${ADDIN}/index.html" ]]; then
  echo "error: ${ADDIN}/index.html not found — clone grynn-in/konsol at ${KONSOL_APP}" >&2
  exit 1
fi

echo "==> Packaging Excel add-in from konsol app (${ADDIN})"
tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

cp "$ADDIN/index.html" "$tmpdir/index.html"
cp "$ADDIN/functions.js" "$tmpdir/functions.js"
cp "$ADDIN/functions.json" "$tmpdir/functions.json"
cp "$ADDIN/manifest.demo.xml" "$tmpdir/manifest.xml"
cp -R "$ADDIN/assets" "$tmpdir/assets"
cp "$REPO/docker/caddy/Caddyfile" "$tmpdir/Caddyfile"
cp "$KONSOL_PY/api.py" "$tmpdir/api.py"
cp "$KONSOL_PY/report_compiler.py" "$tmpdir/report_compiler.py"
cp "$KONSOL_PY/excel_addin_auth.py" "$tmpdir/excel_addin_auth.py"
cp "$KONSOL_PY/excel_addin_cookies.py" "$tmpdir/excel_addin_cookies.py"
cp "$KONSOL_PY/hooks.py" "$tmpdir/hooks.py"

echo "==> Uploading to ${SSH_HOST}"
ssh "${SSH_HOST}" "rm -rf /tmp/excel-addin-full && mkdir -p /tmp/excel-addin-full"
scp -r "$tmpdir/"* "${SSH_HOST}:/tmp/excel-addin-full/"

echo "==> Applying on server"
ssh "${SSH_HOST}" bash -s <<EOF
set -euo pipefail
cd ${REMOTE_DIR}
docker compose cp /tmp/excel-addin-full/index.html frappe_backend:${DEST}/index.html
docker compose cp /tmp/excel-addin-full/functions.js frappe_backend:${DEST}/functions.js
docker compose cp /tmp/excel-addin-full/functions.json frappe_backend:${DEST}/functions.json
docker compose cp /tmp/excel-addin-full/manifest.xml frappe_backend:${DEST}/manifest.xml
docker compose exec -T frappe_backend rm -f ${DEST}/pane-minimal.html ${DEST}/manifest.online.xml ${DEST}/taskpane.js ${DEST}/taskpane.css
echo "==> Copying konsol Python modules"
docker compose cp /tmp/excel-addin-full/api.py frappe_backend:${CONTAINER_PATH}/api.py
docker compose cp /tmp/excel-addin-full/report_compiler.py frappe_backend:${CONTAINER_PATH}/report_compiler.py
docker compose cp /tmp/excel-addin-full/excel_addin_auth.py frappe_backend:${CONTAINER_PATH}/excel_addin_auth.py
docker compose cp /tmp/excel-addin-full/excel_addin_cookies.py frappe_backend:${CONTAINER_PATH}/excel_addin_cookies.py
docker compose cp /tmp/excel-addin-full/hooks.py frappe_backend:${CONTAINER_PATH}/hooks.py
docker compose exec -T frappe_backend grep -q "def build_cell_map" ${CONTAINER_PATH}/api.py
docker compose exec -T frappe_backend grep -q "def build_snapshot" ${CONTAINER_PATH}/api.py
docker compose exec -T frappe_backend test -f ${CONTAINER_PATH}/report_compiler.py
for icon in icon-16.png icon-32.png icon-64.png icon-80.png; do
  docker compose cp /tmp/excel-addin-full/assets/\$icon frappe_backend:${DEST}/assets/\$icon
done
docker compose exec -T frappe_backend bench --site ${SITE} clear-cache
docker compose restart frappe_backend frappe_worker frappe_scheduler
cp /tmp/excel-addin-full/Caddyfile ${REMOTE_DIR}/docker/caddy/Caddyfile
docker compose exec -T caddy caddy reload --config /etc/caddy/Caddyfile
EOF

echo "==> Verify"
curl -s "https://demo.konsolidat.com/assets/konsol/excel-addin/manifest.xml" | grep -E '<Version>|<Id>|KonsolidatAddin'
curl -s "https://demo.konsolidat.com/assets/konsol/excel-addin/index.html" | grep -oE 'v[0-9]+\.[0-9.]+'
curl -sI "https://demo.konsolidat.com/assets/konsol/excel-addin/functions.json" | grep -iE 'cache-control|access-control-allow-origin'
ssh "${SSH_HOST}" "cd ${REMOTE_DIR} && docker compose exec -T frappe_backend grep -q 'def build_cell_map' ${CONTAINER_PATH}/api.py && docker compose exec -T frappe_backend grep -q 'def build_snapshot' ${CONTAINER_PATH}/api.py && echo 'build_snapshot: ok'"

echo "Done. M365 Admin Center manifest URL:"
echo "  https://demo.konsolidat.com/assets/konsol/excel-addin/manifest.xml"