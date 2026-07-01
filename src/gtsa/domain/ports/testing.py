"""Port para execução de testes (Schemathesis)."""

from __future__ import annotations

from typing import Protocol


class ITestRunner(Protocol):
    """Executa a suíte de testes property-based sobre a API alvo."""

    def run(self, only_high_risk: bool = False, verbose: bool = False) -> int:
        """Executa os testes e retorna o código de saída do processo."""
        ...
