#!/usr/bin/env bash
# Deploy full Excel add-in (custom functions + task pane) to demo.konsolidat.com.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
REPO="${ROOT}/konsolidat/repo"
ADDIN="${REPO}/excel-addin"
SSH_HOST="${KONSOL_SSH_HOST:-hetzner-konsolidat}"
REMOTE_DIR="/root/konsolidat"
SITE="${KONSOL_SITE:-konsolidat.local}"
CONTAINER_PATH="/home/frappe/frappe-bench/apps/konsol/konsol"
DEST="${CONTAINER_PATH}/public/excel-addin"

echo "==> Packaging full Excel add-in"
tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

cp "$ADDIN/src/index.html" "$tmpdir/index.html"
cp "$ADDIN/src/functions.js" "$tmpdir/functions.js"
cp "$ADDIN/src/functions.json" "$tmpdir/functions.json"
cp "$ADDIN/manifest.demo.xml" "$tmpdir/manifest.xml"
cp -R "$ADDIN/src/assets" "$tmpdir/assets"
cp "$REPO/docker/caddy/Caddyfile" "$tmpdir/Caddyfile"
cp "$REPO/docker/frappe/konsol/konsol/api.py" "$tmpdir/api.py"
cp "$REPO/docker/frappe/konsol/konsol/excel_addin_auth.py" "$tmpdir/excel_addin_auth.py"
cp "$REPO/docker/frappe/konsol/konsol/excel_addin_cookies.py" "$tmpdir/excel_addin_cookies.py"
cp "$REPO/docker/frappe/konsol/konsol/hooks.py" "$tmpdir/hooks.py"

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
docker compose cp /tmp/excel-addin-full/api.py frappe_backend:${CONTAINER_PATH}/api.py
docker compose cp /tmp/excel-addin-full/excel_addin_auth.py frappe_backend:${CONTAINER_PATH}/excel_addin_auth.py
docker compose cp /tmp/excel-addin-full/excel_addin_cookies.py frappe_backend:${CONTAINER_PATH}/excel_addin_cookies.py
docker compose cp /tmp/excel-addin-full/hooks.py frappe_backend:${CONTAINER_PATH}/hooks.py
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
curl -s "https://demo.konsolidat.com/assets/konsol/excel-addin/index.html" | grep -o 'v1\.[0-9.]*'
curl -sI "https://demo.konsolidat.com/assets/konsol/excel-addin/functions.json" | grep -i cache-control

echo "Done. Sideload fresh manifest:"
echo "  curl -o ~/Downloads/Konsolidat-Excel-Full.xml 'https://demo.konsolidat.com/assets/konsol/excel-addin/manifest.xml'"