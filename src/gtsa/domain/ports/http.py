"""Port para cliente HTTP (abstrai ``requests``)."""

from __future__ import annotations

from typing import Any, Dict, Optional, Protocol, Tuple


class IHttpClient(Protocol):
    """Cliente HTTP mínimo usado pelos adapters (auth, llm)."""

    def post(
        self,
        url: str,
        *,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[Tuple[str, str]] = None,
        timeout: int = 30,
    ) -> "HttpResponse": ...


class HttpResponse(Protocol):
    """Resposta HTTP mínima."""

    status_code: int
    text: str

    def json(self) -> Any: ...

    def raise_for_status(self) -> None: ...
