"""Ports para persistência de artefatos e endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol


class IArtifactStore(Protocol):
    """Lê e grava artefatos (JSON/texto) em um local de runtime."""

    def write_json(self, relative_path: str, data: Any) -> Path: ...

    def read_json(self, relative_path: str) -> Any: ...

    def write_text(self, relative_path: str, content: str) -> Path: ...

    def path_for(self, relative_path: str) -> Path: ...


class IEndpointRepository(Protocol):
    """Persiste e recupera coleções de endpoints (brutos e enriquecidos)."""

    def save_scan(self, endpoints: List[Dict[str, Any]]) -> Path: ...

    def load_latest_scan(self) -> List[Dict[str, Any]]: ...

    def latest_scan_path(self) -> Optional[Path]: ...

    def save_enriched(self, endpoints: List[Dict[str, Any]]) -> Path: ...

    def load_enriched(self) -> List[Dict[str, Any]]: ...
