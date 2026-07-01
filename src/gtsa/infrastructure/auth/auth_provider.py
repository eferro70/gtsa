"""Provedor de autenticação unificado.

Consolida as três implementações antigas de autenticação
(``utils/auth_loader.py``, ``interfaces/hooks/auth_hooks.py`` e o hook gerado)
em um único adapter que implementa ``IAuthProvider``.

Estratégias (em ordem de prioridade):
1. ``API_AUTH_HEADERS`` — JSON explícito no .env, usado sem alterações.
2. OAuth2 Client Credentials (``AUTH_TYPE=client_credentials``).
3. Montagem automática a partir dos tokens estáticos por perfil.
"""

from __future__ import annotations

import json
import os
from typing import Dict, Optional

from ...domain.errors import AuthenticationError
from ...domain.ports.http import IHttpClient

_PROFILE_TOKEN_VAR: Dict[str, str] = {
    "ADMINISTRADOR": "TOKEN_ADMINISTRADOR",
    "GESTOR": "TOKEN_GESTOR",
    "REQUISITANTE": "TOKEN_REQUISITANTE",
    "INTERESSADO": "TOKEN_INTERESSADO",
    "PAV": "TOKEN_PAV",
    "TESTE": "TOKEN_TESTE",
}

_FALLBACK_ORDER = [
    "ADMINISTRADOR",
    "GESTOR",
    "INTERESSADO",
    "REQUISITANTE",
    "PAV",
    "TESTE",
]

_PLACEHOLDERS = {
    "seu-token-aqui", "token-aqui", "your-token-here",
    "<token>", "Bearer", "eyJhbGciOi...", "MTJjYTVmY2YtZ...",
}


class AuthProvider:
    """Monta headers de autenticação para as requisições da pipeline."""

    def __init__(self, http: IHttpClient) -> None:
        self._http = http
        self._oauth2_cache: Optional[Dict[str, str]] = None

    # -- API pública -------------------------------------------------------

    def build_headers(self) -> Dict[str, str]:
        # 1. API_AUTH_HEADERS explícito
        raw = os.getenv("API_AUTH_HEADERS", "").strip()
        if raw and raw != "{}":
            try:
                headers = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise AuthenticationError(
                    f"API_AUTH_HEADERS não contém JSON válido: {exc}\n  Valor: {raw}"
                ) from exc
            if headers and isinstance(headers, dict):
                return headers

        # 2. OAuth2 Client Credentials
        if os.getenv("AUTH_TYPE", "").strip().lower() == "client_credentials":
            return self._get_oauth2_token()

        # 3. Montagem automática (tokens estáticos)
        return self._build_static_headers()

    def print_summary(self, headers: Dict[str, str]) -> None:
        auth_type = os.getenv("AUTH_TYPE", "").strip().lower() or "static"
        profile = os.getenv("AUTH_PROFILE", "auto").strip() or "auto"
        print(f"\n🔑 Autenticação (tipo: {auth_type}, perfil: {profile}):")
        if not headers:
            print("   ⚠️  Nenhum header configurado — modo anônimo.")
            return
        for name, value in headers.items():
            masked = f"{value[:6]}..." if len(value) > 8 else "***"
            print(f"   - {name}: ✅ ({masked})")

    def clear_cache(self) -> None:
        self._oauth2_cache = None

    # -- Internos ----------------------------------------------------------

    def _get_oauth2_token(self) -> Dict[str, str]:
        if self._oauth2_cache is not None:
            return self._oauth2_cache

        client_id = os.getenv("CLIENT_ID", "").strip()
        client_secret = os.getenv("CLIENT_SECRET", "").strip()
        token_url = os.getenv("TOKEN_URL", "").strip()

        if not client_id or not client_secret:
            raise AuthenticationError(
                "Client Credentials requer CLIENT_ID e CLIENT_SECRET no .env."
            )
        if not token_url:
            raise AuthenticationError("Client Credentials requer TOKEN_URL no .env.")

        payload = {"grant_type": "client_credentials"}
        form_headers = {"Content-Type": "application/x-www-form-urlencoded"}

        # Tentativa 1: HTTP Basic Auth (RFC 6749 §2.3.1)
        response = self._http.post(
            token_url, data=payload, auth=(client_id, client_secret),
            headers=form_headers, timeout=30,
        )
        if response.status_code == 401:
            # Tentativa 2: credenciais no body
            payload = {**payload, "client_id": client_id, "client_secret": client_secret}
            response = self._http.post(token_url, data=payload, headers=form_headers, timeout=30)

        try:
            response.raise_for_status()
        except Exception as exc:  # noqa: BLE001 - re-empacota como erro de domínio
            raise AuthenticationError(
                f"Falha ao obter token OAuth2 ({token_url}): {exc}"
            ) from exc

        try:
            token_data = response.json()
        except ValueError as exc:
            raise AuthenticationError(
                f"Token endpoint retornou resposta não-JSON: {response.text[:200]}"
            ) from exc

        access_token = (
            token_data.get("access_token")
            or token_data.get("token")
            or token_data.get("accessToken")
        )
        if not access_token:
            raise AuthenticationError(
                f"Resposta do token endpoint sem access_token. Campos: {list(token_data)}"
            )

        self._oauth2_cache = {"Authorization": f"Bearer {access_token}"}
        return self._oauth2_cache

    def _build_static_headers(self) -> Dict[str, str]:
        profile = os.getenv("AUTH_PROFILE", "").strip().upper()

        if not profile:
            for candidate in _FALLBACK_ORDER:
                if os.getenv(_PROFILE_TOKEN_VAR[candidate], "").strip():
                    profile = candidate
                    break
        if not profile:
            return {}

        token_var = _PROFILE_TOKEN_VAR.get(profile)
        if not token_var:
            raise AuthenticationError(
                f"AUTH_PROFILE='{profile}' não reconhecido. "
                f"Aceitos: {', '.join(_PROFILE_TOKEN_VAR)}"
            )

        token = os.getenv(token_var, "").strip()
        if not token:
            raise AuthenticationError(
                f"Perfil '{profile}' requer {token_var}, mas está vazio no .env."
            )
        if token in _PLACEHOLDERS:
            raise AuthenticationError(
                f"{token_var} contém placeholder ('{token}'). Use o token real."
            )

        if profile == "REQUISITANTE":
            return {"Authorization": f"Bearer {token}"}

        cookie_name = os.getenv("AUTH_COOKIE_NAME", "").strip()
        if not cookie_name:
            raise AuthenticationError(
                "AUTH_COOKIE_NAME não definido — necessário para auth via cookie."
            )
        return {"Cookie": f"{cookie_name}={token}"}
