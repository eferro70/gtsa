"""
schemathesis_auth_hook.py
─────────────────────────
Hook de autenticação para o Schemathesis.

Lê o enriched_endpoints.json e mapeia cada operação (método + path)
para a role correta, injetando o token JWT correspondente via header
Authorization. Os tokens são lidos de variáveis de ambiente no formato:

    TOKEN_REQUISITANTE=<jwt>
    TOKEN_GESTOR=<jwt>
    TOKEN_ADMINISTRADOR=<jwt>
    TOKEN_INTERESSADO=<jwt>

Se o endpoint não exigir autenticação (auth_required=false) ou não
houver role mapeada, o header não é injetado.

Uso (referenciado pelo step6_schemathesis.sh via --hooks):
    schemathesis run ... --hooks schemathesis_auth_hook.py
"""

import os
import json
from pathlib import Path
import schemathesis

# ── Carrega mapeamento endpoint → roles ──────────────────────────────────────

def _load_role_map(enriched_path: str) -> dict[tuple[str, str], list[str]]:
    """Retorna {(METHOD, /path/normalizado): [roles]} a partir do JSON enriquecido."""
    path = Path(enriched_path)
    if not path.exists():
        print(f"[auth_hook] AVISO: enriched_endpoints.json não encontrado em {enriched_path}")
        return {}

    with path.open() as f:
        endpoints = json.load(f)

    role_map: dict[tuple[str, str], list[str]] = {}
    for ep in endpoints:
        method = ep.get("method", "").upper()
        ep_path = ep.get("path", "")
        roles = ep.get("roles") or []
        if method and ep_path:
            role_map[(method, ep_path)] = roles
    return role_map


def _get_token(role: str) -> str | None:
    """Lê TOKEN_<ROLE> do ambiente (insensível a maiúsculas)."""
    return os.environ.get(f"TOKEN_{role.upper()}")


# Caminho padrão; pode ser sobrescrito via variável de ambiente
_ENRICHED_PATH = os.environ.get(
    "ENRICHED_ENDPOINTS_JSON",
    os.path.join(os.path.dirname(__file__), "tests", "enriched_endpoints.json"),
)

_ROLE_MAP = _load_role_map(_ENRICHED_PATH)

# ── Hook de autenticação ─────────────────────────────────────────────────────

@schemathesis.hook("before_call")
def set_auth_header(context, case, **kwargs):
    """
    Injeta o header Authorization antes de cada chamada HTTP.

    Estratégia de seleção de role (em ordem de prioridade):
      1. Role mapeada no enriched_endpoints.json para este endpoint
      2. Primeira role com token disponível no ambiente
      3. Sem autenticação (endpoint público)
    """
    method = case.method.upper()
    # formatted_path pode não existir em versões mais novas; usa path_template como fallback
    path = getattr(case, "formatted_path", None) or getattr(case, "path", "")
    path_params = getattr(case, "path_parameters", None) or {}

    # Tenta correspondência exata primeiro; depois por path template
    roles = _ROLE_MAP.get((method, path)) or _ROLE_MAP.get(
        (method, _to_template(path, path_params))
    )

    if not roles:
        # Endpoint público — não injeta token
        return

    # Seleciona o primeiro role que tenha token disponível
    for role in roles:
        token = _get_token(role)
        if token:
            case.headers = case.headers or {}
            case.headers["Authorization"] = f"Bearer {token}"
            return

    print(
        f"[auth_hook] AVISO: nenhum token encontrado para roles {roles} "
        f"em {method} {path}. Requisição será enviada sem autenticação."
    )


def _to_template(formatted_path: str, path_params: dict) -> str:
    """
    Reconstrói o path template a partir do path formatado.
    Ex: /api/grupos/id/abc123  →  /api/grupos/id/:id
        /api/fluxos/42/interessados  →  /api/fluxos/:id/interessados

    Suporta tanto o estilo Express (:param) quanto o estilo OpenAPI ({param}).
    """
    result = formatted_path
    for param, value in path_params.items():
        result = result.replace(str(value), f":{param}")
    return result
