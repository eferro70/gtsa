"""Port para construção de relatórios."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class IReportBuilder(Protocol):
    """Constrói o relatório final a partir dos resultados dos testes."""

    def build(self, full: bool = False, hide_success: bool = False, hide_skip: bool = False) -> Path:
        """Gera o relatório e retorna o caminho do arquivo produzido."""
        ...
