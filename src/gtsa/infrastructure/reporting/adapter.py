"""Adapter que implementa ``IReportBuilder``.

Envolve o gerador de relatório consolidado (``report_builder.py``, antigo
``step6``), que parseia o JUnit XML e o log do Schemathesis e escreve o
``test_api_summary.md``. As constantes globais do módulo são resolvidas a
partir de ``Settings`` antes da execução.
"""

from __future__ import annotations

from pathlib import Path

from ..config.settings import Settings
from . import report_builder as _builder


class MarkdownReportBuilderAdapter:
    """Constrói o relatório Markdown a partir dos resultados do Schemathesis."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def build(
        self,
        full: bool = False,
        hide_success: bool = False,
        hide_skip: bool = False,
    ) -> Path:
        output_dir = Path(self._settings.output_dir).resolve()

        _builder.OUTPUT_DIR = output_dir
        _builder.JUNIT_XML = output_dir / "schemathesis_results.xml"
        _builder.SCHEMATHESIS_LOG = output_dir / "schemathesis_execution.log"
        _builder.HIGH_RISK_SPEC = output_dir / "openapi_high_risk.json"
        _builder.SUMMARY_MD = output_dir / "test_api_summary.md"

        parser = _builder.SchemathesisReportParser()
        parser.run()

        return output_dir / "test_api_summary.md"
