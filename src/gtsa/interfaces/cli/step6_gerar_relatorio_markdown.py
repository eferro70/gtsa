"""CLI do Passo 6 — geração do relatório final em Markdown."""

from __future__ import annotations

import argparse

from ...bootstrap import build_container


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Gera o relatório Markdown a partir dos resultados do Schemathesis."
    )
    parser.add_argument("--output-dir", "-d", default=None, help="Diretório de saída")
    parser.add_argument("--env-file", default=None, help="Arquivo .env")
    parser.add_argument("--full", action="store_true", help="Inclui todos os endpoints")
    parser.add_argument("--hide-success", action="store_true", help="Omite endpoints com sucesso")
    parser.add_argument("--hide-skip", action="store_true", help="Omite endpoints pulados")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    container = build_container(env_file=args.env_file, output_dir=args.output_dir)
    report_path = container.build_report.execute(
        full=args.full,
        hide_success=args.hide_success,
        hide_skip=args.hide_skip,
    )
    print(f"\n✅ Relatório gerado: {report_path}")


if __name__ == "__main__":
    main()
