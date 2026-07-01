"""Caso de uso: geração da especificação OpenAPI a partir de endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from ...domain.ports.openapi import IOpenApiGenerator
from ...domain.ports.storage import IArtifactStore


class GenerateOpenApiUseCase:
    """Converte endpoints em um documento OpenAPI e persiste os artefatos."""

    def __init__(self, generator: IOpenApiGenerator, store: IArtifactStore) -> None:
        self._generator = generator
        self._store = store

    def execute(
        self, endpoints: List[Dict[str, Any]], filename: str = "openapi.json"
    ) -> Dict[str, Any]:
        schema = self._generator.generate(endpoints)
        self._store.write_json(filename, schema)

        try:
            import yaml

            yaml_content = yaml.dump(schema, allow_unicode=True, sort_keys=False)
            self._store.write_text(filename.replace(".json", ".yaml"), yaml_content)
        except ImportError:
            pass

        return schema
