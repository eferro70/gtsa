"""Caso de uso: geração de dados de exemplo (payloads) via LLM."""

from __future__ import annotations

from typing import Any, Dict

from ...domain.ports.examples import IExampleDataGenerator


class GenerateExampleDataUseCase:
    """Gera dados de exemplo a partir de uma especificação OpenAPI."""

    def __init__(self, generator: IExampleDataGenerator) -> None:
        self._generator = generator

    def execute(self, openapi: Dict[str, Any], only_with_body: bool = True) -> int:
        return self._generator.generate(openapi, only_with_body=only_with_body)
