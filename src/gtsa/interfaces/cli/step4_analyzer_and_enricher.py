"""CLI do Passo 4 — análise de risco e enriquecimento de segurança."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ...bootstrap import build_container
from .common import load_latest_scan_endpoints


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analisa risco dos endpoints e enriquece a especificação OpenAPI."
    )
    parser.add_argument("endpoints", nargs="?", default=None, help="Arquivo all_endpoints.json")
    parser.add_argument("--output-dir", "-d", default=None, help="Diretório de saída")
    parser.add_argument("--openapi", default=None, help="Caminho da OpenAPI de origem")
    parser.add_argument("--env-file", default=None, help="Arquivo .env")
    parser.add_argument("--no-llm", action="store_true", help="Desativa análise via LLM")
    return parser


def main() -> None:
    args = build_parser().parse_args()

    container = build_container(
        env_file=args.env_file,
        output_dir=args.output_dir,
        use_llm=not args.no_llm,
    )

    if args.endpoints:
        endpoints_path = Path(args.endpoints)
        if not endpoints_path.exists():
            print(f"❌ Arquivo de endpoints não encontrado: {endpoints_path}")
            sys.exit(1)
        with open(endpoints_path, "r", encoding="utf-8") as fh:
            endpoints = json.load(fh)
    else:
        try:
            endpoints = load_latest_scan_endpoints(container.settings)
        except FileNotFoundError as exc:
            print(f"❌ {exc}")
            sys.exit(1)

    enriched = container.analyze_and_enrich.execute(endpoints, openapi=args.openapi)
    print(f"\n✅ Análise concluída: {len(enriched)} endpoints enriquecidos.")


if __name__ == "__main__":
    main()
