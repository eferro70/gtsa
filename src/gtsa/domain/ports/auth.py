"""Port para provedor de autenticação."""

from __future__ import annotations

from typing import Dict, Protocol


class IAuthProvider(Protocol):
    """Monta os headers de autenticação para as requisições da pipeline."""

    def build_headers(self) -> Dict[str, str]: ...
