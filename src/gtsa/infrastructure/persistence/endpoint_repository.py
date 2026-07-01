"""Repositório de endpoints (scans brutos e enriquecidos).

Implementa ``IEndpointRepository`` persistindo em JSON dentro de
``Settings.runtime_dir``. Substitui os caminhos hardcoded
``src/application/pipeline/tests/...`` usados pelos steps antigos.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...domain.errors import GtsaError
from ..config.settings import Settings


class FilesystemEndpointRepository:
    """Persiste coleções de endpoints em ``runtime/scans`` e ``runtime``."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._scans_dir = settings.scans_dir
        self._enriched_path = settings.runtime_dir / "enriched_endpoints.json"
        self._scans_dir.mkdir(parents=True, exist_ok=True)

    # -- Scans -------------------------------------------------------------

    def save_scan(self, endpoints: List[Dict[str, Any]], language: str = "unknown") -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = self._scans_dir / f"scan_{timestamp}_{language}"
        session_dir.mkdir(parents=True, exist_ok=True)
        path = session_dir / "all_endpoints.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(endpoints, f, indent=2, ensure_ascii=False, default=str)
        return path

    def latest_scan_path(self) -> Optional[Path]:
        if not self._scans_dir.exists():
            return None
        scan_dirs = sorted(
            (d for d in self._scans_dir.glob("scan_*") if d.is_dir()), reverse=True
        )
        for d in scan_dirs:
            candidate = d / "all_endpoints.json"
            if candidate.exists():
                return candidate
        return None

    def load_latest_scan(self) -> List[Dict[str, Any]]:
        path = self.latest_scan_path()
        if path is None:
            raise GtsaError(
                f"Nenhum scan encontrado em {self._scans_dir}. Execute o step1 primeiro."
            )
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    # -- Enriquecidos ------------------------------------------------------

    def save_enriched(self, endpoints: List[Dict[str, Any]]) -> Path:
        self._enriched_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._enriched_path, "w", encoding="utf-8") as f:
            json.dump(endpoints, f, indent=2, ensure_ascii=False, default=str)
        return self._enriched_path

    def load_enriched(self) -> List[Dict[str, Any]]:
        if not self._enriched_path.exists():
            raise GtsaError(f"enriched_endpoints.json não encontrado em {self._enriched_path}.")
        with open(self._enriched_path, encoding="utf-8") as f:
            return json.load(f)
