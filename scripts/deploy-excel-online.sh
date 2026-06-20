#!/usr/bin/env bash
# Deploy Excel Online add-in assets to demo.konsolidat.com (Hetzner).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
REPO="${ROOT}/konsolidat/repo"
SSH_HOST="${KONSOL_SSH_HOST:-hetzner-konsolidat}"
REMOTE_DIR="/root/konsolidat"
SITE="${KONSOL_SITE:-konsolidat.local}"
CONTAINER_PATH="/home/frappe/frappe-bench/apps/konsol/konsol"

echo "==> Packaging Excel Online add-in"
tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

cp "$REPO/excel-addin/src/pane-minimal.html" "$tmpdir/pane-minimal.html"
cp "$REPO/excel-addin/manifest.online.xml" "$tmpdir/manifest.online.xml"
cp "$REPO/docker/caddy/Caddyfile" "$tmpdir/Caddyfile"
cp "$REPO/docker/frappe/konsol/konsol/excel_addin_cookies.py" "$tmpdir/excel_addin_cookies.py"
cp "$REPO/docker/frappe/konsol/konsol/hooks.py" "$tmpdir/hooks.py"

echo "==> Uploading to ${SSH_HOST}"
scp "$tmpdir/pane-minimal.html" "$tmpdir/manifest.online.xml" \
    "$tmpdir/excel_addin_cookies.py" "$tmpdir/hooks.py" \
    "${SSH_HOST}:/tmp/"
scp "$tmpdir/Caddyfile" "${SSH_HOST}:${REMOTE_DIR}/docker/caddy/Caddyfile"

echo "==> Applying on server"
ssh "${SSH_HOST}" bash -s <<EOF
set -euo pipefail
cd ${REMOTE_DIR}
docker compose cp /tmp/pane-minimal.html frappe_backend:${CONTAINER_PATH}/public/excel-addin/pane-minimal.html
docker compose cp /tmp/manifest.online.xml frappe_backend:${CONTAINER_PATH}/public/excel-addin/manifest.online.xml
docker compose cp /tmp/excel_addin_cookies.py frappe_backend:${CONTAINER_PATH}/excel_addin_cookies.py
docker compose cp /tmp/hooks.py frappe_backend:${CONTAINER_PATH}/hooks.py
docker compose exec -T caddy caddy reload --config /etc/caddy/Caddyfile
docker compose exec -T frappe_backend bench --site ${SITE} clear-cache
docker compose restart frappe_backend
EOF

echo "==> Verify"
curl -sI "https://demo.konsolidat.com/assets/konsol/excel-addin/pane-minimal.html" | grep -iE 'content-security-policy|cache-control'
curl -s "https://demo.konsolidat.com/assets/konsol/excel-addin/manifest.online.xml" | grep '<Version>'

echo "Done. Sideload Konsolidat-Excel-Online.xml (version must match hosted manifest)."