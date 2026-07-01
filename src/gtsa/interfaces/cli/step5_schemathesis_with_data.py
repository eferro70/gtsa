"""CLI do Passo 5 — execução dos testes Schemathesis com dados reais."""

from __future__ import annotations

import argparse
import sys

from ...bootstrap import build_container


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Executa Schemathesis com dados reais e autenticação condicional."
    )
    parser.add_argument("--output-dir", "-d", default=None, help="Diretório de saída")
    parser.add_argument("--env-file", default=None, help="Arquivo .env")
    parser.add_argument("--only-high-risk", action="store_true", help="Apenas alto risco")
    parser.add_argument("--verbose", "-v", action="store_true", help="Logs detalhados")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    container = build_container(
        env_file=args.env_file,
        output_dir=args.output_dir,
        verbose=args.verbose,
    )
    exit_code = container.run_schemathesis.execute(
        only_high_risk=args.only_high_risk,
        verbose=args.verbose,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
