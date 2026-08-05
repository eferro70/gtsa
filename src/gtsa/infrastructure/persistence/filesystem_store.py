"""Armazenamento de artefatos em sistema de arquivos.

Implementa ``IArtifactStore``. Todos os caminhos relativos são resolvidos a
partir de ``Settings.output_dir``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config.settings import Settings


class FilesystemArtifactStore:
    """Lê e grava artefatos JSON/texto no diretório de saída da execução."""

    def __init__(self, settings: Settings) -> None:
        self._base = settings.output_dir

    def path_for(self, relative_path: str) -> Path:
        return self._base / relative_path

    def write_json(self, relative_path: str, data: Any) -> Path:
        path = self.path_for(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        return path

    def read_json(self, relative_path: str) -> Any:
        with open(self.path_for(relative_path), encoding="utf-8") as f:
            return json.load(f)

    def write_text(self, relative_path: str, content: str) -> Path:
        path = self.path_for(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path
