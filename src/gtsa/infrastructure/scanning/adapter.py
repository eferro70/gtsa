"""Adapter que implementa ``ISourceScanner``.

Envolve o varredor consolidado (``scanner.py``, antigo ``step1``), mantendo a
lógica comprovada de detecção de linguagem e extração de endpoints por parser,
mas resolvendo os diretórios de saída a partir de ``Settings``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config.settings import Settings
from . import scanner as _scanner


@dataclass
class ScanResult:
    scan_dir: str
    endpoints: List[Dict[str, Any]] = field(default_factory=list)


class SourceScannerAdapter:
    """Executa a varredura e devolve o diretório do scan e os endpoints."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def scan(
        self,
        project_path: str,
        language: Optional[str] = None,
        output_dir: Optional[str] = None,
        debug: bool = False,
    ) -> ScanResult:
        target_output = output_dir or str(self._settings.output_dir)
        _scanner.analyze_project(
            project_path=project_path,
            language=language,
            output_dir=target_output,
            debug=debug,
        )

        scans_root = Path(self._settings.scans_dir)
        scan_dirs = sorted(
            scans_root.glob("scan_*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not scan_dirs:
            raise FileNotFoundError(
                f"Nenhum diretório de scan encontrado em {scans_root}"
            )

        latest = scan_dirs[0]
        endpoints_file = latest / "all_endpoints.json"
        endpoints: List[Dict[str, Any]] = []
        if endpoints_file.exists():
            with open(endpoints_file, "r", encoding="utf-8") as fh:
                endpoints = json.load(fh)

        return ScanResult(scan_dir=str(latest), endpoints=endpoints)
