#!/usr/bin/env bash
# Start konsol-mcp with secrets + defaults from ~/.config/konsol.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/scripts/load-konsol-secrets.sh"

: "${KONSOL_URL:=http://localhost:8069}"
: "${KONSOL_SITE:=konsolidat.local}"
export KONSOL_URL KONSOL_SITE

exec "$ROOT/.venv/bin/konsol-mcp" "$@"