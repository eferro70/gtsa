"""Ports para análise de vulnerabilidades e detecção de PII."""

from __future__ import annotations

from typing import Any, Dict, List, Protocol


class IPiiDetector(Protocol):
    """Detecta campos com dados pessoais sensíveis (PII)."""

    def detect(self, text: str) -> List[str]: ...


class IVulnerabilityAnalyzer(Protocol):
    """Analisa endpoints e produz enriquecimento de segurança (OWASP/SANS)."""

    def analyze(
        self,
        endpoints: List[Dict[str, Any]],
        openapi: Dict[str, Any] | None = None,
    ) -> List[Dict[str, Any]]: ...
