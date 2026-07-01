"""Adapter que implementa ``ITestRunner``.

Envolve o runner Schemathesis consolidado (``schemathesis_runner.py``, antigo
``step5``). O runner é um orquestrador que gera hooks e executa um subprocesso
``schemathesis``; portanto o adapter apenas fornece os parâmetros a partir de
``Settings`` e captura o código de saída.
"""

from __future__ import annotations

import sys

from ..config.settings import Settings
from . import schemathesis_runner as _runner


class SchemathesisRunnerAdapter:
    """Executa a suíte Schemathesis e retorna o código de saída."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def run(self, only_high_risk: bool = False, verbose: bool = False) -> int:
        argv = [
            "gtsa-schemathesis",
            "--output-dir",
            str(self._settings.output_dir),
        ]
        if self._settings.env_file:
            argv += ["--env-file", self._settings.env_file]
        if only_high_risk:
            argv.append("--only-high-risk")
        if verbose:
            argv.append("--verbose")

        original_argv = sys.argv
        sys.argv = argv
        try:
            _runner.main()
            return 0
        except SystemExit as exc:
            code = exc.code
            return code if isinstance(code, int) else (0 if code is None else 1)
        finally:
            sys.argv = original_argv
