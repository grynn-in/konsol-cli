#!/usr/bin/env bash
# Source API credentials into the current shell without printing them.
# Usage:  source /path/to/konsol_cli/scripts/load-konsol-secrets.sh
#
# Prefers ~/.config/konsol/secrets.env, then secrets.toml (or KONSOL_SECRETS).
# For Grok MCP, run this before starting Grok so ${KONSOL_API_KEY} resolves.
set -euo pipefail

if [ -n "${KONSOL_SECRETS:-}" ]; then
  SECRETS_PATH="$KONSOL_SECRETS"
elif [ -f "$HOME/.config/konsol/secrets.env" ]; then
  SECRETS_PATH="$HOME/.config/konsol/secrets.env"
else
  SECRETS_PATH="$HOME/.config/konsol/secrets.toml"
fi

if [ ! -f "$SECRETS_PATH" ]; then
  echo "konsol secrets not found (tried secrets.env / secrets.toml)" >&2
  return 1 2>/dev/null || exit 1
fi

case "$SECRETS_PATH" in
  *.env)
    set -a
    # shellcheck disable=SC1090
    source "$SECRETS_PATH"
    set +a
    ;;
  *)
    eval "$(SECRETS_PATH="$SECRETS_PATH" python3 - <<'PY'
import os, tomllib
from pathlib import Path
path = Path(os.environ["SECRETS_PATH"])
data = tomllib.load(path.open("rb")).get("default", {})
for env_name, key in (("KONSOL_API_KEY", "api_key"), ("KONSOL_API_SECRET", "api_secret")):
    value = data.get(key)
    if value:
        print(f"export {env_name}={value!r}")
PY
)"
    ;;
esac