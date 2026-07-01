"""Caso de uso: geração do relatório final em Markdown."""

from __future__ import annotations

from pathlib import Path

from ...domain.ports.reporting import IReportBuilder


class BuildReportUseCase:
    """Constrói o relatório final a partir dos resultados dos testes."""

    def __init__(self, builder: IReportBuilder) -> None:
        self._builder = builder

    def execute(
        self,
        full: bool = False,
        hide_success: bool = False,
        hide_skip: bool = False,
    ) -> Path:
        return self._builder.build(full=full, hide_success=hide_success, hide_skip=hide_skip)
