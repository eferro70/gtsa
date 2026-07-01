"""Caso de uso: execução dos testes property-based (Schemathesis)."""

from __future__ import annotations

from ...domain.ports.testing import ITestRunner


class RunSchemathesisUseCase:
    """Executa a suíte Schemathesis contra a API alvo."""

    def __init__(self, runner: ITestRunner) -> None:
        self._runner = runner

    def execute(self, only_high_risk: bool = False, verbose: bool = False) -> int:
        return self._runner.run(only_high_risk=only_high_risk, verbose=verbose)
