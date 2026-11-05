"""Bench backend — runs konsol.cli_api methods inside a Frappe bench site."""
from __future__ import annotations

import ast
import json
import subprocess
from typing import Any

from konsol_cli.backends.errors import BackendError
from konsol_cli.settings import Settings


class BenchBackend:
    def __init__(self, settings: Settings):
        self.settings = settings
        if not settings.compose_file:
            raise BackendError(
                "compose_file is required for the bench backend. "
                "Pass --compose-file or set KONSOL_COMPOSE_FILE."
            )

    def apply_schema(self, run_dbt: bool = False) -> dict[str, Any]:
        return self._call("konsol.cli_api.apply_schema_api", run_dbt=run_dbt)

    def get_schema_status(self) -> dict[str, Any]:
        return self._call("konsol.cli_api.get_schema_status_api")

    def export_config(self, status: str | None = None) -> dict[str, Any]:
        return self._call("konsol.cli_api.export_config_api", status=status)

    def apply_config(
        self, spec: dict[str, Any], publish: bool = False, prune: bool = False
    ) -> dict[str, Any]:
        return self._call(
            "konsol.cli_api.apply_config_api",
            spec=spec,
            publish=publish,
            prune=prune,
        )

    def diff_config(
        self, spec: dict[str, Any], status: str | None = None
    ) -> dict[str, Any]:
        return self._call(
            "konsol.cli_api.diff_config_api",
            spec=spec,
            status=status,
        )

    @staticmethod
    def _serialize_bench_kwargs(kwargs: dict[str, Any]) -> str:
        """Frappe bench execute uses eval(), so booleans must be Python literals."""
        return (
            json.dumps(kwargs)
            .replace("false", "False")
            .replace("true", "True")
            .replace("null", "None")
        )

    def _call(self, method: str, **kwargs: Any) -> Any:
        kwargs = {key: value for key, value in kwargs.items() if value is not None}
        command = [
            "docker",
            "compose",
            "-f",
            self.settings.compose_file,
            "exec",
            "-T",
            self.settings.compose_service,
            "bench",
            "--site",
            self.settings.site,
            "execute",
            method,
        ]
        if kwargs:
            command.extend(["--kwargs", self._serialize_bench_kwargs(kwargs)])

        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
            raise BackendError(f"bench execute failed: {detail}")

        return self._parse_output(result.stdout)

    @staticmethod
    def _parse_output(stdout: str) -> Any:
        text = stdout.strip()
        if not text:
            return []

        for parser in (json.loads, ast.literal_eval):
            try:
                return parser(text)
            except (json.JSONDecodeError, SyntaxError, ValueError):
                continue

        raise BackendError(f"could not parse bench output: {text[:200]}")
