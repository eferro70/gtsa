#!/usr/bin/env python3
"""
utils/auth_loader.py
--------------------
Centraliza a lógica de montagem dos headers de autenticação para os scripts
da pipeline GTSA.

Regras suportadas (em ordem de prioridade):

1. API_AUTH_HEADERS  — JSON explícito no .env; usado diretamente se presente.
   Exemplo: API_AUTH_HEADERS='{"Cookie": "neosigner-auth=<token>"}'

2. Autenticação Client Credentials (OAuth2) — gera token via client_id/client_secret
   Ativado quando AUTH_TYPE=client_credentials
   Variáveis necessárias:
     CLIENT_ID, CLIENT_SECRET, TOKEN_URL (opcional)

3. Montagem automática a partir das variáveis de token do .env:
   - Perfil REQUISITANTE → Authorization: Bearer <TOKEN_REQUISITANTE>
   - Demais perfis        → Cookie: <AUTH_COOKIE_NAME>=<token>
     Prioridade dos tokens: ADMINISTRADOR > GESTOR > INTERESSADO > PAV > TESTE

   Variáveis de controle no .env:
     AUTH_COOKIE_NAME   — nome do cookie (ex: neosigner-auth)
     AUTH_PROFILE       — perfil ativo: ADMINISTRADOR | GESTOR | REQUISITANTE |
                          INTERESSADO | PAV | TESTE  (padrão: ADMINISTRADOR)

Interface pública
-----------------
    from utils.auth_loader import build_auth_headers, print_auth_summary

    auth_headers = build_auth_headers()   # → dict[str, str]
    print_auth_summary(auth_headers)
"""

from __future__ import annotations

import json
import os
from typing import Dict, Optional
import requests
from urllib.parse import urljoin


# ---------------------------------------------------------------------------
# Mapeamento perfil → variável de ambiente do token
# ---------------------------------------------------------------------------
_PROFILE_TOKEN_VAR: Dict[str, str] = {
    "ADMINISTRADOR": "TOKEN_ADMINISTRADOR",
    "GESTOR":        "TOKEN_GESTOR",
    "REQUISITANTE":  "TOKEN_REQUISITANTE",
    "INTERESSADO":   "TOKEN_INTERESSADO",
    "PAV":           "TOKEN_PAV",
    "TESTE":         "TOKEN_TESTE",
}

# Ordem de fallback quando AUTH_PROFILE não está definido
_FALLBACK_ORDER = [
    "ADMINISTRADOR",
    "GESTOR",
    "INTERESSADO",
    "REQUISITANTE",
    "PAV",
    "TESTE",
]

# Cache do token OAuth2 para evitar múltiplas requisições
_OAUTH2_TOKEN_CACHE: Optional[Dict[str, str]] = None


# Valores conhecidos de placeholder — rejeitados para evitar testes com token falso
_PLACEHOLDERS = {
    "seu-token-aqui", "token-aqui", "your-token-here",
    "<token>", "Bearer", "eyJhbGciOi...", "MTJjYTVmY2YtZ...",
}


def _get_oauth2_token() -> Dict[str, str]:
    """
    Obtém token OAuth2 via Client Credentials (RFC 6749 §4.4).

    Estratégia de autenticação (tentadas em ordem):
      1. HTTP Basic Auth (client_id:client_secret no header Authorization)
         → padrão RFC 6749 §2.3.1, usado pelo SerproID e maioria dos IdPs.
      2. Credenciais no body (form-urlencoded)
         → fallback para servidores que não suportam Basic Auth.
    """
    global _OAUTH2_TOKEN_CACHE
    if _OAUTH2_TOKEN_CACHE is not None:
        return _OAUTH2_TOKEN_CACHE

    client_id = os.getenv("CLIENT_ID", "").strip()
    client_secret = os.getenv("CLIENT_SECRET", "").strip()
    token_url = os.getenv("TOKEN_URL", "").strip()

    if not client_id or not client_secret:
        raise ValueError(
            "Autenticação Client Credentials requer CLIENT_ID e CLIENT_SECRET "
            "definidos no .env."
        )

    if not token_url:
        raise ValueError(
            "Autenticação Client Credentials requer TOKEN_URL definido no .env."
        )

    # Payload mínimo obrigatório pela RFC 6749 §4.4.2
    payload = {"grant_type": "client_credentials"}

    # ── Tentativa 1: Basic Auth (RFC 6749 §2.3.1) ───────────────────────────
    # SerproID e a maioria dos Authorization Servers governamentais exigem
    # client_id:client_secret no header, não no body.
    try:
        response = requests.post(
            token_url,
            data=payload,
            auth=(client_id, client_secret),          # → Authorization: Basic <b64>
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )

        # Se o servidor rejeitar Basic Auth explicitamente, tenta body
        if response.status_code == 401:
            raise requests.exceptions.HTTPError(response=response)

        response.raise_for_status()

    except requests.exceptions.HTTPError:
        # ── Tentativa 2: credenciais no body (fallback) ──────────────────────
        payload["client_id"] = client_id
        payload["client_secret"] = client_secret
        try:
            response = requests.post(
                token_url,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as exc2:
            raise ValueError(
                f"Falha ao obter token OAuth2 (Basic Auth e body falharam): {exc2}\n"
                f"  TOKEN_URL: {token_url}\n"
                f"  Verifique CLIENT_ID, CLIENT_SECRET e a conectividade."
            ) from exc2

    except requests.exceptions.RequestException as exc:
        raise ValueError(
            f"Falha ao obter token OAuth2: {exc}\n"
            f"  TOKEN_URL: {token_url}\n"
            f"  Verifique CLIENT_ID, CLIENT_SECRET e a conectividade com o servidor."
        ) from exc

    try:
        token_data = response.json()
    except ValueError as exc:
        raise ValueError(
            f"Token endpoint retornou resposta não-JSON (HTTP {response.status_code}):\n"
            f"  {response.text[:200]}"
        ) from exc

    access_token = (
        token_data.get("access_token")
        or token_data.get("token")
        or token_data.get("accessToken")
    )
    if not access_token:
        raise ValueError(
            f"Resposta do token endpoint não contém access_token.\n"
            f"  Campos recebidos: {list(token_data.keys())}\n"
            f"  Resposta completa: {token_data}"
        )

    _OAUTH2_TOKEN_CACHE = {"Authorization": f"Bearer {access_token}"}
    return _OAUTH2_TOKEN_CACHE


def build_auth_headers() -> Dict[str, str]:
    """
    Retorna um dict de headers HTTP prontos para injeção nas requisições.

    Prioridade:
    1. API_AUTH_HEADERS (JSON explícito no .env) — usado sem alterações.
    2. Autenticação Client Credentials (AUTH_TYPE=client_credentials)
    3. Montagem automática (tokens estáticos do .env)
    """

    # ── 1. API_AUTH_HEADERS explícito ────────────────────────────────────────
    raw = os.getenv("API_AUTH_HEADERS", "").strip()
    if raw and raw != "{}":
        try:
            headers = json.loads(raw)
            if headers and isinstance(headers, dict):
                return headers
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"API_AUTH_HEADERS não contém JSON válido: {exc}\n"
                f"  Valor atual: {raw}\n"
                f"  Exemplo correto: "
                '\'{"Cookie": "neosigner-auth=<token>"}\''
            ) from exc

    # ── 2. Autenticação Client Credentials (OAuth2) ────────────────────────
    auth_type = os.getenv("AUTH_TYPE", "").strip().lower()
    
    if auth_type == "client_credentials":
        try:
            return _get_oauth2_token()
        except ValueError as exc:
            # Relança com contexto mais claro
            raise ValueError(
                f"Erro na autenticação Client Credentials: {exc}\n"
                f"  Configure no .env:\n"
                f"    AUTH_TYPE=client_credentials\n"
                f"    CLIENT_ID=<seu_client_id>\n"
                f"    CLIENT_SECRET=<seu_client_secret>\n"
                f"    TOKEN_URL=<opcional_url_do_token>"
            ) from exc

    # ── 3. Montagem automática (tokens estáticos) ──────────────────────────
    profile = os.getenv("AUTH_PROFILE", "").strip().upper()

    # Se AUTH_PROFILE não está definido, usa o primeiro token disponível
    if not profile:
        for candidate in _FALLBACK_ORDER:
            if os.getenv(_PROFILE_TOKEN_VAR[candidate], "").strip():
                profile = candidate
                break

    if not profile:
        return {}

    token_var = _PROFILE_TOKEN_VAR.get(profile)
    if not token_var:
        raise ValueError(
            f"AUTH_PROFILE='{profile}' não reconhecido. "
            f"Valores aceitos: {', '.join(_PROFILE_TOKEN_VAR)}"
        )

    token = os.getenv(token_var, "").strip()
    if not token:
        raise ValueError(
            f"Perfil AUTH_PROFILE='{profile}' requer {token_var}, "
            f"mas a variável está vazia ou ausente no .env."
        )
    if token in _PLACEHOLDERS:
        raise ValueError(
            f"{token_var} contém um valor placeholder ('{token}'). "
            f"Substitua pelo token real no .env."
        )

    # REQUISITANTE → Bearer; demais → Cookie
    if profile == "REQUISITANTE":
        return {"Authorization": f"Bearer {token}"}

    cookie_name = os.getenv("AUTH_COOKIE_NAME", "").strip()
    if not cookie_name:
        raise ValueError(
            "AUTH_COOKIE_NAME não definido no .env. "
            "Necessário para autenticação via cookie."
        )

    return {"Cookie": f"{cookie_name}={token}"}


def print_auth_summary(auth_headers: Dict[str, str]) -> None:
    """Imprime resumo dos headers de autenticação ativos (mascarando valores)."""
    auth_type = os.getenv("AUTH_TYPE", "").strip().lower() or "static"
    profile = os.getenv("AUTH_PROFILE", "auto").strip() or "auto"
    
    print(f"\n🔑 Autenticação (tipo: {auth_type}, perfil: {profile}):")

    if not auth_headers:
        print("   ⚠️  Nenhum header configurado — modo anônimo.")
        return

    for name, value in auth_headers.items():
        masked = f"{value[:6]}..." if len(value) > 8 else "***"
        print(f"   - {name}: ✅ ({masked})")


def clear_oauth2_cache() -> None:
    """
    Limpa o cache do token OAuth2, forçando uma nova requisição na próxima chamada.
    Útil quando o token expirou e precisa ser renovado.
    """
    global _OAUTH2_TOKEN_CACHE
    _OAUTH2_TOKEN_CACHE = None