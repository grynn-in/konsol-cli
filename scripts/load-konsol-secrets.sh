#!/usr/bin/env bash
# Source API credentials into the current shell without printing them.
# Usage:  source /path/to/konsol_cli/scripts/load-konsol-secrets.sh
#
# Reads ~/.config/konsol/secrets.toml (or KONSOL_SECRETS). For Grok MCP, run this
# before starting Grok so ${KONSOL_API_KEY} resolves in .grok/config.toml.
set -euo pipefail

SECRETS_PATH="${KONSOL_SECRETS:-$HOME/.config/konsol/secrets.toml}"
if [ ! -f "$SECRETS_PATH" ]; then
  echo "konsol secrets not found: $SECRETS_PATH" >&2
  return 1 2>/dev/null || exit 1
fi

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