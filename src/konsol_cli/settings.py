"""Runtime settings for konsol-cli."""
from __future__ import annotations

import os
try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # Python 3.10 — use the tomli backport
    import tomli as tomllib
from dataclasses import dataclass, replace
from pathlib import Path


def _config_paths() -> list[Path]:
    paths = []
    if os.environ.get("KONSOL_CONFIG"):
        paths.append(Path(os.environ["KONSOL_CONFIG"]))
    paths.append(Path.home() / ".config" / "konsol" / "config.toml")
    return paths


def _load_config_file() -> dict:
    for path in _config_paths():
        if path.is_file():
            with path.open("rb") as handle:
                return tomllib.load(handle)
    return {}


def _secrets_dir() -> Path:
    return Path.home() / ".config" / "konsol"


def _parse_dotenv(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep:
            continue
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key] = value
    return values


def _load_dotenv_file(path: Path) -> dict[str, str]:
    return _parse_dotenv(path.read_text(encoding="utf-8"))


def _secrets_paths() -> list[Path]:
    if os.environ.get("KONSOL_SECRETS"):
        return [Path(os.environ["KONSOL_SECRETS"])]
    base = _secrets_dir()
    return [base / "secrets.env", base / "secrets.toml"]


def _load_secrets_file() -> dict:
    for path in _secrets_paths():
        if not path.is_file():
            continue
        if path.suffix == ".env" or path.name.endswith(".env"):
            dotenv = _load_dotenv_file(path)
            return {
                "api_key": dotenv.get("KONSOL_API_KEY"),
                "api_secret": dotenv.get("KONSOL_API_SECRET"),
            }
        with path.open("rb") as handle:
            return tomllib.load(handle).get("default", {})
    return {}


@dataclass(frozen=True)
class Settings:
    backend: str
    site: str
    compose_file: str | None
    compose_service: str
    url: str | None
    api_key: str | None
    api_secret: str | None

    @classmethod
    def from_env(
        cls,
        *,
        backend: str | None = None,
        site: str | None = None,
        compose_file: str | None = None,
        compose_service: str | None = None,
        url: str | None = None,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> Settings:
        file_cfg = _load_config_file().get("default", {})
        secrets_cfg = _load_secrets_file()
        return cls(
            backend=backend
            or os.environ.get("KONSOL_BACKEND")
            or file_cfg.get("backend", "bench"),
            site=site
            or os.environ.get("KONSOL_SITE")
            or file_cfg.get("site", "konsolidat.local"),
            compose_file=compose_file
            or os.environ.get("KONSOL_COMPOSE_FILE")
            or file_cfg.get("compose_file"),
            compose_service=compose_service
            or os.environ.get("KONSOL_COMPOSE_SERVICE")
            or file_cfg.get("compose_service", "frappe_backend"),
            url=url or os.environ.get("KONSOL_URL") or file_cfg.get("url"),
            api_key=api_key
            or os.environ.get("KONSOL_API_KEY")
            or secrets_cfg.get("api_key"),
            api_secret=api_secret
            or os.environ.get("KONSOL_API_SECRET")
            or secrets_cfg.get("api_secret"),
        )

    def merge(self, **overrides: str | None) -> Settings:
        cleaned = {key: value for key, value in overrides.items() if value is not None}
        return replace(self, **cleaned) if cleaned else self