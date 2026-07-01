"""Port para cliente de LLM (Ollama, Gatiator, ...)."""

from __future__ import annotations

from typing import Protocol


class ILlmClient(Protocol):
    """Gera texto a partir de um prompt usando um backend de LLM."""

    def generate(self, prompt: str, model: str) -> str: ...
