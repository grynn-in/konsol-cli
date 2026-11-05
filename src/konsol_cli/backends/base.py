"""Backend protocol for konsol configuration operations."""
from __future__ import annotations

from typing import Any, Protocol


class ConfigBackend(Protocol):
    def apply_schema(self, run_dbt: bool = False) -> dict[str, Any]: ...

    def get_schema_status(self) -> dict[str, Any]: ...

    def export_config(self, status: str | None = None) -> dict[str, Any]: ...

    def apply_config(
        self, spec: dict[str, Any], publish: bool = False, prune: bool = False
    ) -> dict[str, Any]: ...

    def diff_config(
        self, spec: dict[str, Any], status: str | None = None
    ) -> dict[str, Any]: ...
