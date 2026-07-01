"""Factory de parsers: detecta a linguagem do projeto e cria o parser adequado.

Implementa ``ISourceParserFactory`` do domínio. Encapsula a detecção de
linguagem que antes vivia dentro do ``step1_scan.py``.
"""

from __future__ import annotations

import os
from typing import Dict, Optional, Type

from ...domain.errors import UnsupportedLanguageError
from ...domain.ports.parsing import ISourceParser
from .base import BaseParser

_LANGUAGE_INDICATORS: Dict[str, list] = {
    "typescript": ["tsconfig.json", "package.json", ".ts", ".tsx"],
    "python": ["requirements.txt", "setup.py", "pyproject.toml", ".py"],
    "java": ["pom.xml", "build.gradle", ".java"],
    "go": ["go.mod", "go.sum", ".go"],
    "ruby": ["Gemfile", "Rakefile", ".rb"],
}


def _load_parser_registry() -> Dict[str, Type[BaseParser]]:
    """Carrega os parsers disponíveis, tolerando dependências ausentes."""
    registry: Dict[str, Type[BaseParser]] = {}
    try:
        from .typescript import TypeScriptParser

        registry.update(
            {
                "typescript": TypeScriptParser,
                "javascript": TypeScriptParser,
                "ts": TypeScriptParser,
                "js": TypeScriptParser,
            }
        )
    except ImportError as exc:  # pragma: no cover - depende de tree-sitter
        print(f"⚠️  Parser TypeScript indisponível: {exc}")

    try:
        from .java import JavaSpringParser

        registry["java"] = JavaSpringParser
    except ImportError as exc:  # pragma: no cover
        print(f"⚠️  Parser Java indisponível: {exc}")

    return registry


class SourceParserFactory:
    """Detecta linguagem e instancia o parser correspondente."""

    def __init__(self) -> None:
        self._registry = _load_parser_registry()

    def detect_language(self, project_path: str) -> Optional[str]:
        scores = {lang: 0 for lang in _LANGUAGE_INDICATORS}

        for root, _dirs, files in os.walk(project_path):
            if root.count(os.sep) - project_path.count(os.sep) > 2:
                continue
            for file in files:
                for lang, patterns in _LANGUAGE_INDICATORS.items():
                    if file in patterns[:3]:
                        scores[lang] += 10
                    if any(file.endswith(ext) for ext in patterns[2:]):
                        scores[lang] += 1
            if max(scores.values()) > 20:
                break

        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        return None

    def create(self, language: str, debug: bool = False) -> ISourceParser:
        parser_class = self._registry.get(language)
        if parser_class is None:
            raise UnsupportedLanguageError(
                f"Parser não disponível para '{language}'. "
                f"Disponíveis: {sorted(self._registry)}"
            )
        try:
            return parser_class(debug=debug)  # type: ignore[call-arg]
        except TypeError:
            return parser_class()
