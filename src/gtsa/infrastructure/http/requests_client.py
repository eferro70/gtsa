"""Adapter de cliente HTTP baseado em ``requests``."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


class RequestsHttpClient:
    """Implementa ``IHttpClient`` delegando para a biblioteca ``requests``."""

    def post(
        self,
        url: str,
        *,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[Tuple[str, str]] = None,
        timeout: int = 30,
    ):
        import requests

        return requests.post(
            url,
            data=data,
            json=json,
            headers=headers,
            auth=auth,
            timeout=timeout,
        )
