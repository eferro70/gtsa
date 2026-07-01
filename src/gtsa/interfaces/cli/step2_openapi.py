"""CLI do Passo 2 — geração da especificação OpenAPI."""

from __future__ import annotations

import argparse
import os
import sys

from ...bootstrap import build_container
from .common import load_latest_scan_endpoints


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Gera uma especificação OpenAPI 3.0 a partir dos endpoints do scan."
    )
    parser.add_argument("--env-file", default=None, help="Arquivo .env")
    parser.add_argument("--output-dir", "-d", default=None, help="Diretório de saída")
    parser.add_argument("--title", default=None, help="Título da API")
    parser.add_argument("--version", default=None, help="Versão da API")
    parser.add_argument("--prefix", default=None, help="Prefixo externo dos endpoints")
    parser.add_argument("--base-url", default=None, help="URL base da API")
    return parser


def main() -> None:
    args = build_parser().parse_args()

    # Prioridade: args > .env. Injeta no ambiente antes de montar Settings.
    for env_name, value in (
        ("API_TITLE", args.title),
        ("API_VERSION", args.version),
        ("ENDPOINT_PREFIX", args.prefix),
        ("API_BASE_URL", args.base_url),
    ):
        if value:
            os.environ[env_name] = value

    container = build_container(env_file=args.env_file, output_dir=args.output_dir)

    try:
        endpoints = load_latest_scan_endpoints(container.settings)
    except FileNotFoundError as exc:
        print(f"❌ {exc}")
        sys.exit(1)

    schema = container.generate_openapi.execute(endpoints)
    print("\n✅ OpenAPI gerado com sucesso!")
    print(f"   - Total de paths: {len(schema.get('paths', {}))}")


if __name__ == "__main__":
    main()
