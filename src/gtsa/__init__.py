"""GTSA - Gerador de Testes de Segurança de APIs.

Pacote organizado em Clean Architecture:

- ``gtsa.domain``          Entidades, value objects, erros e ports (interfaces).
- ``gtsa.application``     Casos de uso que orquestram o domínio via ports.
- ``gtsa.infrastructure``  Adapters concretos (parsers, http, llm, persistência...).
- ``gtsa.interfaces``      Pontos de entrada (CLI, hooks, testes stateful).
- ``gtsa.bootstrap``       Composition root: liga adapters aos casos de uso.
"""

__version__ = "0.1.0"
