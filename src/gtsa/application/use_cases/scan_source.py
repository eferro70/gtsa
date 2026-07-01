"""Caso de uso: varredura de código-fonte para extração de endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ...domain.ports.parsing import ISourceScanner


@dataclass
class ScanSourceResult:
    scan_dir: str
    endpoints: List[Dict[str, Any]]


class ScanSourceUseCase:
    """Varre o projeto alvo e devolve o diretório do scan e os endpoints."""

    def __init__(self, scanner: ISourceScanner) -> None:
        self._scanner = scanner

    def execute(
        self,
        project_path: str,
        language: Optional[str] = None,
        output_dir: Optional[str] = None,
        debug: bool = False,
    ) -> ScanSourceResult:
        outcome = self._scanner.scan(
            project_path=project_path,
            language=language,
            output_dir=output_dir,
            debug=debug,
        )
        return ScanSourceResult(scan_dir=outcome.scan_dir, endpoints=outcome.endpoints)
