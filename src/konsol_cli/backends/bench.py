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

    def list_dimensions(self, status: str | None = None) -> list[dict[str, Any]]:
        return self._call("konsol.cli_api.list_dimensions_api", status=status)

    def get_dimension(self, name: str) -> dict[str, Any]:
        return self._call("konsol.cli_api.get_dimension_api", name=name)

    def upsert_dimension(
        self, spec: dict[str, Any], publish: bool = False
    ) -> dict[str, Any]:
        return self._call(
            "konsol.cli_api.upsert_dimension_api",
            spec=spec,
            publish=publish,
        )

    def publish_dimension(self, name: str) -> dict[str, Any]:
        return self._call("konsol.cli_api.publish_dimension_api", name=name)

    def unpublish_dimension(self, name: str) -> dict[str, Any]:
        return self._call("konsol.cli_api.unpublish_dimension_api", name=name)

    def get_measure(self, name: str) -> dict[str, Any]:
        return self._call("konsol.cli_api.get_measure_api", name=name)

    def upsert_measure(
        self, spec: dict[str, Any], publish: bool = False
    ) -> dict[str, Any]:
        return self._call(
            "konsol.cli_api.upsert_measure_api",
            spec=spec,
            publish=publish,
        )

    def publish_measure(self, name: str) -> dict[str, Any]:
        return self._call("konsol.cli_api.publish_measure_api", name=name)

    def unpublish_measure(self, name: str) -> dict[str, Any]:
        return self._call("konsol.cli_api.unpublish_measure_api", name=name)

    def apply_schema(self, run_dbt: bool = False) -> dict[str, Any]:
        return self._call("konsol.cli_api.apply_schema_api", run_dbt=run_dbt)

    def get_schema_status(self) -> dict[str, Any]:
        return self._call("konsol.cli_api.get_schema_status_api")

    def list_measures(self, status: str | None = None) -> list[dict[str, Any]]:
        return self._call("konsol.cli_api.list_measures_api", status=status)

    def get_fact_table(self, name: str) -> dict[str, Any]:
        return self._call("konsol.cli_api.get_fact_table_api", name=name)

    def upsert_fact_table(
        self, spec: dict[str, Any], publish: bool = False
    ) -> dict[str, Any]:
        return self._call(
            "konsol.cli_api.upsert_fact_table_api",
            spec=spec,
            publish=publish,
        )

    def publish_fact_table(self, name: str) -> dict[str, Any]:
        return self._call("konsol.cli_api.publish_fact_table_api", name=name)

    def unpublish_fact_table(self, name: str) -> dict[str, Any]:
        return self._call("konsol.cli_api.unpublish_fact_table_api", name=name)

    def list_fact_tables(self, status: str | None = None) -> list[dict[str, Any]]:
        return self._call("konsol.cli_api.list_fact_tables_api", status=status)

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

    def list_connectors(self, enabled: bool | None = None) -> list[dict[str, Any]]:
        kwargs: dict[str, Any] = {}
        if enabled is not None:
            kwargs["enabled"] = enabled
        return self._call("konsol.cli_api.list_connectors_api", **kwargs)

    def get_connector(self, name: str) -> dict[str, Any]:
        return self._call("konsol.cli_api.get_connector_api", name=name)

    def upsert_connector(self, spec: dict[str, Any]) -> dict[str, Any]:
        return self._call("konsol.cli_api.upsert_connector_api", spec=spec)

    def delete_connector(self, name: str) -> dict[str, Any]:
        return self._call("konsol.cli_api.delete_connector_api", name=name)

    def list_erp_sources(self) -> dict[str, Any]:
        return self._call("konsol.cli_api.list_erp_sources_api")

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