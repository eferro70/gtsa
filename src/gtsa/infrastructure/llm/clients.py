"""Clientes de LLM que implementam ``ILlmClient``.

Suporta os backends usados pela pipeline: ``ollama`` (nativo) e ``gatiator``
(compatível com a API de chat da OpenAI).
"""

from __future__ import annotations

from ...domain.errors import GtsaError
from ...domain.ports.http import IHttpClient

BACKEND_URLS = {
    "gatiator": "http://localhost:1313/v1/chat/completions",
    "ollama": "http://localhost:11434/api/generate",
}


class OllamaClient:
    """Cliente para o backend Ollama."""

    def __init__(self, http: IHttpClient, base_url: str | None = None) -> None:
        self._http = http
        self._url = base_url or BACKEND_URLS["ollama"]

    def generate(self, prompt: str, model: str) -> str:
        url = self._url
        if not url.rstrip("/").endswith("api/generate"):
            url = url.rstrip("/") + "/api/generate"
        payload = {"model": model, "prompt": prompt, "stream": False, "format": "json"}
        response = self._http.post(
            url, json=payload, headers={"Content-Type": "application/json"}, timeout=60
        )
        if response.status_code != 200:
            raise GtsaError(f"Ollama {response.status_code}: {response.text[:300]}")
        return response.json().get("response", "")


class GatiatorClient:
    """Cliente para o backend Gatiator (OpenAI-like)."""

    def __init__(self, http: IHttpClient, base_url: str | None = None) -> None:
        self._http = http
        self._url = base_url or BACKEND_URLS["gatiator"]

    def generate(self, prompt: str, model: str) -> str:
        payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}
        headers = {"Content-Type": "application/json", "Authorization": "Bearer qualquer"}
        response = self._http.post(self._url, json=payload, headers=headers, timeout=60)
        if response.status_code != 200:
            raise GtsaError(f"Gatiator {response.status_code}: {response.text[:300]}")
        data = response.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")


def create_llm_client(backend: str, http: IHttpClient, base_url: str | None = None):
    """Factory de cliente LLM conforme o backend configurado."""
    backend = (backend or "ollama").lower()
    if backend == "gatiator":
        return GatiatorClient(http, base_url)
    return OllamaClient(http, base_url)
