"""CLI do Passo 1 — varredura do projeto e extração de endpoints."""

from __future__ import annotations

import argparse
import sys

from ...bootstrap import build_container


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analisa um projeto e extrai endpoints de API (multi-linguagem)."
    )
    parser.add_argument("-i", "--input", required=True, help="Caminho da raiz do projeto")
    parser.add_argument("--language", default=None, help="Linguagem (typescript, java, ...)")
    parser.add_argument("--output-dir", "-d", default=None, help="Diretório de relatórios")
    parser.add_argument("--env-file", default=None, help="Arquivo .env")
    parser.add_argument("--debug", action="store_true", help="Ativa logs detalhados")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    container = build_container(
        env_file=args.env_file,
        output_dir=args.output_dir,
        debug=args.debug,
    )
    try:
        result = container.scan_source.execute(
            project_path=args.input,
            language=args.language,
            debug=args.debug,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"❌ Erro durante a análise: {exc}")
        sys.exit(1)

    print(f"\n📁 Scan salvo em: {result.scan_dir}")
    print(f"🔗 Endpoints encontrados: {len(result.endpoints)}")


if __name__ == "__main__":
    main()
