"""Regras puras de detecção de PII.

Os padrões de PII são injetados (carregados de ``config/pii_patterns.json`` pela
infraestrutura), mantendo esta regra livre de I/O.
"""

from __future__ import annotations

from typing import List, Sequence


class PiiRules:
    """Detecta ocorrências de PII em textos com base em uma lista de padrões."""

    def __init__(self, patterns: Sequence[str]) -> None:
        self._patterns = [p.lower() for p in patterns]

    def detect(self, text: str) -> List[str]:
        if not text:
            return []
        haystack = text.lower()
        return [p for p in self._patterns if p in haystack]

    def has_pii(self, text: str) -> bool:
        return bool(self.detect(text))
