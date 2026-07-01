"""Adapter que implementa ``IVulnerabilityAnalyzer``.

Envolve o analisador consolidado (``analyzer.py``, antigo ``step4``), mantendo
seus algoritmos determinísticos e o modo híbrido LLM/heurística intactos, mas
resolvendo caminhos a partir de ``Settings`` (inversão de dependência).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config.settings import Settings
from . import analyzer as _legacy


class VulnerabilityAnalyzerAdapter:
    """Analisa endpoints e grava o enriquecimento de segurança."""

    def __init__(
        self,
        settings: Settings,
        use_llm: bool = False,
        backend: str = "none",
        model: str = "codellama:7b",
        llm_url: Optional[str] = None,
    ) -> None:
        self._settings = settings
        self._use_llm = use_llm
        self._backend = backend
        self._model = model
        self._llm_url = llm_url

    def analyze(
        self,
        endpoints: List[Dict[str, Any]],
        openapi: Dict[str, Any] | str | None = None,
    ) -> List[Dict[str, Any]]:
        openapi_file: Optional[str] = openapi if isinstance(openapi, str) else None

        result = _legacy.analyze_project_endpoints(
            endpoints=endpoints,
            openapi_file=openapi_file,
            model=self._model,
            use_llm=self._use_llm,
            backend=self._backend if self._use_llm else "gatiator",
            llm_url=self._llm_url,
            output_dir=Path(self._settings.output_dir),
            data_dir=Path(self._settings.data_dir),
            env_file=self._settings.env_file,
        )
        return result.get("endpoints", [])
