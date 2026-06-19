"""API backend — calls konsol.cli_api over the Frappe HTTP API."""
from __future__ import annotations

from typing import Any

import requests

from konsol_cli.backends.errors import BackendError
from konsol_cli.settings import Settings


class ApiBackend:
    def __init__(self, settings: Settings):
        self.settings = settings
        if not settings.url:
            raise BackendError(
                "url is required for the api backend. "
                "Pass --url or set KONSOL_URL."
            )
        if not settings.api_key or not settings.api_secret:
            raise BackendError(
                "api_key and api_secret are required for the api backend. "
                "Pass --api-key/--api-secret or set KONSOL_API_KEY/KONSOL_API_SECRET."
            )

        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"token {settings.api_key}:{settings.api_secret}",
                "Accept": "application/json",
            }
        )
        if settings.site:
            self._session.headers["Host"] = settings.site

    def list_dimensions(self, status: str | None = None) -> list[dict[str, Any]]:
        return self._call("konsol.cli_api.list_dimensions_api", status=status)

    def get_dimension(self, name: str) -> dict[str, Any]:
        return self._call("konsol.cli_api.get_dimension_api", name=name)

    def upsert_dimension(
        self, spec: dict[str, Any], publish: bool = False
    ) -> dict[str, Any]:
        return self._call(
            "konsol.cli_api.upsert_dimension_api",
            use_post=True,
            spec=spec,
            publish=int(publish),
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
            use_post=True,
            spec=spec,
            publish=int(publish),
        )

    def publish_measure(self, name: str) -> dict[str, Any]:
        return self._call("konsol.cli_api.publish_measure_api", name=name)

    def unpublish_measure(self, name: str) -> dict[str, Any]:
        return self._call("konsol.cli_api.unpublish_measure_api", name=name)

    def apply_schema(self, run_dbt: bool = False) -> dict[str, Any]:
        return self._call(
            "konsol.cli_api.apply_schema_api",
            use_post=True,
            run_dbt=int(run_dbt),
        )

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
            use_post=True,
            spec=spec,
            publish=int(publish),
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
            use_post=True,
            spec=spec,
            publish=int(publish),
            prune=int(prune),
        )

    def diff_config(
        self, spec: dict[str, Any], status: str | None = None
    ) -> dict[str, Any]:
        return self._call(
            "konsol.cli_api.diff_config_api",
            use_post=True,
            spec=spec,
            status=status,
        )

    def list_connectors(self, enabled: bool | None = None) -> list[dict[str, Any]]:
        kwargs: dict[str, Any] = {}
        if enabled is not None:
            kwargs["enabled"] = int(enabled)
        return self._call("konsol.cli_api.list_connectors_api", **kwargs)

    def get_connector(self, name: str) -> dict[str, Any]:
        return self._call("konsol.cli_api.get_connector_api", name=name)

    def upsert_connector(self, spec: dict[str, Any]) -> dict[str, Any]:
        return self._call(
            "konsol.cli_api.upsert_connector_api",
            use_post=True,
            spec=spec,
        )

    def delete_connector(self, name: str) -> dict[str, Any]:
        return self._call("konsol.cli_api.delete_connector_api", name=name)

    def list_erp_sources(self) -> dict[str, Any]:
        return self._call("konsol.cli_api.list_erp_sources_api")

    def _call(self, method: str, *, use_post: bool = False, **kwargs: Any) -> Any:
        kwargs = {key: value for key, value in kwargs.items() if value is not None}
        url = f"{self.settings.url.rstrip('/')}/api/method/{method}"

        if use_post:
            response = self._session.post(url, json=kwargs, timeout=120)
        elif kwargs:
            response = self._session.get(url, params=kwargs, timeout=120)
        else:
            response = self._session.get(url, timeout=120)

        return self._parse_response(response)

    @staticmethod
    def _parse_response(response: requests.Response) -> Any:
        try:
            payload = response.json()
        except ValueError as exc:
            raise BackendError(
                f"Invalid response from Frappe ({response.status_code}): "
                f"{response.text[:200]}"
            ) from exc

        if response.status_code >= 400 or payload.get("exc"):
            message = payload.get("exception") or payload.get("exc") or response.text
            raise BackendError(f"Frappe API error: {message}")

        if "message" in payload:
            return payload["message"]
        return payload