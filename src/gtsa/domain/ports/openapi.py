"""Port para geração de especificação OpenAPI."""

from __future__ import annotations

from typing import Any, Dict, List, Protocol


class IOpenApiGenerator(Protocol):
    """Converte uma lista de endpoints em uma especificação OpenAPI 3.0."""

    def generate(self, endpoints: List[Dict[str, Any]]) -> Dict[str, Any]: ...
