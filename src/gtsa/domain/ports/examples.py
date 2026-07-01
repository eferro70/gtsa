"""Port para geração de dados de exemplo."""

from __future__ import annotations

from typing import Any, Dict, Protocol


class IExampleDataGenerator(Protocol):
    """Gera dados de exemplo (payloads) a partir de uma especificação OpenAPI."""

    def generate(self, openapi: Dict[str, Any], only_with_body: bool = True) -> int:
        """Gera exemplos e os persiste; retorna a quantidade gerada."""
        ...
