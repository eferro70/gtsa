"""Utilitários compartilhados pelos comandos de CLI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from ...infrastructure.config.settings import Settings


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--env-file", default=None, help="Arquivo .env (ex: .env.serproid)"
    )
    parser.add_argument(
        "--output-dir", "-d", default=None, help="Diretório de saída (relatórios)"
    )


def load_latest_scan_endpoints(settings: Settings) -> List[Dict[str, Any]]:
    """Carrega ``all_endpoints.json`` do scan mais recente em ``runtime/scans``."""
    scans_dir = Path(settings.scans_dir)
    scan_dirs = sorted(
        scans_dir.glob("scan_*"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not scan_dirs:
        raise FileNotFoundError(
            f"Nenhum scan encontrado em {scans_dir}. Execute o passo de scan primeiro."
        )
    endpoints_file = scan_dirs[0] / "all_endpoints.json"
    if not endpoints_file.exists():
        raise FileNotFoundError(f"all_endpoints.json não encontrado em {scan_dirs[0]}")
    with open(endpoints_file, "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_openapi(settings: Settings) -> Dict[str, Any]:
    """Carrega a especificação OpenAPI do diretório de saída (ou raiz)."""
    candidates = [
        Path(settings.output_dir) / "openapi.json",
        Path(settings.project_root) / "openapi.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            with open(candidate, "r", encoding="utf-8") as fh:
                return json.load(fh)
    raise FileNotFoundError(
        f"openapi.json não encontrado em: {', '.join(str(c) for c in candidates)}"
    )
