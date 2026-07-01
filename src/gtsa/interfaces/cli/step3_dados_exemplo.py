"""CLI do Passo 3 — geração de dados de exemplo (payloads) via LLM."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from ...bootstrap import build_container


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Gera dados de exemplo para testes a partir de uma OpenAPI."
    )
    parser.add_argument("openapi", help="Caminho do arquivo openapi.json")
    parser.add_argument("--data-dir", default=None, help="(compat) ignorado; usa runtime/dados")
    parser.add_argument("--only-with-body", action="store_true", help="Apenas endpoints com body")
    parser.add_argument("--env-file", default=None, help="Arquivo .env")
    parser.add_argument("--llm-backend", default=None, help="Backend LLM (ollama/gatiator)")
    parser.add_argument("--llm-model", default=None, help="Modelo LLM")
    parser.add_argument("--llm-url", default=None, help="URL base do LLM")
    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.llm_backend:
        os.environ["LLM_BACKEND"] = args.llm_backend
    if args.llm_model:
        os.environ["LLM_MODEL"] = args.llm_model
    if args.llm_url:
        os.environ["LLM_BASE_URL"] = args.llm_url

    container = build_container(env_file=args.env_file)

    openapi_path = Path(args.openapi)
    if not openapi_path.exists():
        print(f"❌ OpenAPI não encontrada: {openapi_path}")
        sys.exit(1)
    with open(openapi_path, "r", encoding="utf-8") as fh:
        openapi = json.load(fh)

    count = container.generate_example_data.execute(
        openapi, only_with_body=args.only_with_body
    )
    print(f"\n✅ {count} arquivo(s) de dados gerados em: {container.settings.data_dir}")


if __name__ == "__main__":
    main()
