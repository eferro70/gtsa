"""Caso de uso: análise de risco e enriquecimento de segurança."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ...domain.ports.analysis import IVulnerabilityAnalyzer


class AnalyzeAndEnrichUseCase:
    """Classifica risco dos endpoints e enriquece a especificação OpenAPI."""

    def __init__(self, analyzer: IVulnerabilityAnalyzer) -> None:
        self._analyzer = analyzer

    def execute(
        self,
        endpoints: List[Dict[str, Any]],
        openapi: Dict[str, Any] | str | None = None,
    ) -> List[Dict[str, Any]]:
        return self._analyzer.analyze(endpoints, openapi)
