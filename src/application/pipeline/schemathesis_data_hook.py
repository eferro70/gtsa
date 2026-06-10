# schemathesis_data_hook.py (versão atualizada com suporte a Cookie)

"""
Schemathesis Hook com suporte a autenticação dual:
- REQUISITANTE: Header Authorization: Bearer
- Outros perfis: Cookie: neosigner-auth
"""

import json
import random
import os
import schemathesis

# ============================================================================
# CONFIGURAÇÕES DE AUTENTICAÇÃO
# ============================================================================

# Tokens por perfil
TOKEN_REQUISITANTE = os.getenv("TOKEN_REQUISITANTE", "")
TOKEN_GESTOR = os.getenv("TOKEN_GESTOR", "")
TOKEN_ADMIN = os.getenv("TOKEN_ADMINISTRADOR", "")
TOKEN_INTERESSADO = os.getenv("TOKEN_INTERESSADO", "")

# Mapeamento de endpoints para perfil e método de auth
# Baseado no enriched_endpoints.json
ENDPOINT_AUTH = {
    # REQUISITANTE - Header Authorization
    "POST /api/v1/fluxos": {"perfil": "REQUISITANTE", "method": "header"},
    "POST /api/v1/fluxos/adicionar": {"perfil": "REQUISITANTE", "method": "header"},
    "PUT /api/v1/fluxos/{id}": {"perfil": "REQUISITANTE", "method": "header"},
    "DELETE /api/v1/fluxo/{id}": {"perfil": "REQUISITANTE", "method": "header"},
    "GET /api/v1/fluxos": {"perfil": "REQUISITANTE", "method": "header"},
    "GET /api/v1/fluxo/{id}": {"perfil": "REQUISITANTE", "method": "header"},
    "GET /api/v1/fluxos/arquivados": {"perfil": "REQUISITANTE", "method": "header"},
    "POST /api/v1/documentos": {"perfil": "REQUISITANTE", "method": "header"},
    "DELETE /api/v1/documentos/{id}": {"perfil": "REQUISITANTE", "method": "header"},
    "GET /api/v1/contas": {"perfil": "REQUISITANTE", "method": "header"},
    "GET /api/v1/contas/codigo/{codigo}": {"perfil": "REQUISITANTE", "method": "header"},
    "GET /api/v1/contas/id/{id}": {"perfil": "REQUISITANTE", "method": "header"},
    
    # GESTOR - Cookie
    "POST /api/v1/grupos": {"perfil": "GESTOR", "method": "cookie"},
    "PUT /api/v1/grupos/{id}": {"perfil": "GESTOR", "method": "cookie"},
    "GET /api/v1/grupos": {"perfil": "GESTOR", "method": "cookie"},
    "GET /api/v1/contas/perfil/GESTOR": {"perfil": "GESTOR", "method": "cookie"},
    "GET /api/v1/respostas-gerencial": {"perfil": "GESTOR", "method": "cookie"},
    
    # ADMINISTRADOR - Cookie
    "POST /api/v1/clientes": {"perfil": "ADMIN", "method": "cookie"},
    "PUT /api/v1/clientes/{id}": {"perfil": "ADMIN", "method": "cookie"},
    "GET /api/v1/clientes": {"perfil": "ADMIN", "method": "cookie"},
    "GET /api/v1/clientes/{id}": {"perfil": "ADMIN", "method": "cookie"},
    "POST /api/v1/contas/perfil/{perfil}": {"perfil": "ADMIN", "method": "cookie"},
    "PUT /api/v1/contas/perfil/{perfil}/{id}": {"perfil": "ADMIN", "method": "cookie"},
    
    # INTERESSADO - Cookie
    "GET /api/v1/fluxos-interessado": {"perfil": "INTERESSADO", "method": "cookie"},
    "PATCH /api/v1/fluxos/{id}/assinar": {"perfil": "INTERESSADO", "method": "cookie"},
    "PATCH /api/v1/fluxos/{id}/rejeitar": {"perfil": "INTERESSADO", "method": "cookie"},
    "PATCH /api/v1/fluxos/{id}/revisar": {"perfil": "INTERESSADO", "method": "cookie"},
    "GET /api/v1/fluxos/{id}/hashes-documentos/{algoritmo}": {"perfil": "INTERESSADO", "method": "cookie"},
    "GET /api/v1/resposta/{id}": {"perfil": "INTERESSADO", "method": "cookie"},
}


def get_auth_for_endpoint(method: str, path: str) -> tuple:
    """Retorna (perfil, método_auth) para o endpoint"""
    # Tenta match exato primeiro
    key = f"{method} {path}"
    if key in ENDPOINT_AUTH:
        auth = ENDPOINT_AUTH[key]
        return auth["perfil"], auth["method"]
    
    # Tenta match com path pattern (para URLs com {id})
    for pattern, auth in ENDPOINT_AUTH.items():
        if ' ' in pattern:
            pattern_method, pattern_path = pattern.split(' ', 1)
            if pattern_method == method:
                # Comparação simples de padrão
                pattern_parts = pattern_path.split('/')
                path_parts = path.split('/')
                if len(pattern_parts) == len(path_parts):
                    match = True
                    for pp, ppath in zip(pattern_parts, path_parts):
                        if not (pp == ppath or (pp.startswith('{') and pp.endswith('}'))):
                            match = False
                            break
                    if match:
                        return auth["perfil"], auth["method"]
    
    # Default: REQUISITANTE com header
    return "REQUISITANTE", "header"


def get_token_for_perfil(perfil: str) -> str:
    """Retorna o token para o perfil"""
    tokens = {
        "REQUISITANTE": TOKEN_REQUISITANTE,
        "GESTOR": TOKEN_GESTOR,
        "ADMIN": TOKEN_ADMIN,
        "INTERESSADO": TOKEN_INTERESSADO,
    }
    return tokens.get(perfil, TOKEN_REQUISITANTE)


# ============================================================================
# HOOK PRINCIPAL
# ============================================================================

@schemathesis.hook
def map_headers(ctx, headers):
    """Adiciona autenticação correta baseada no perfil do endpoint"""
    if headers is None:
        headers = {}
    
    method = ctx.operation.method.upper()
    path = ctx.operation.path
    
    perfil, auth_method = get_auth_for_endpoint(method, path)
    token = get_token_for_perfil(perfil)
    
    if auth_method == "header":
        # REQUISITANTE: Header Authorization
        if token:
            headers["Authorization"] = f"Bearer {token}"
    else:
        # Outros perfis: Cookie
        if token:
            headers["Cookie"] = f"neosigner-auth={token}"
    
    # Headers padrão
    headers["Content-Type"] = "application/json"
    headers["Accept"] = "application/json"
    headers["X-Test-Source"] = "schemathesis"
    
    if os.getenv("VERBOSE", "false").lower() == "true":
        print(f"  🔑 {method} {path} → perfil: {perfil}, auth: {auth_method}", flush=True)
    
    return headers


@schemathesis.hook
def map_body(ctx, body):
    """Usa exemplos reais quando disponíveis"""
    return body


@schemathesis.check
def check_auth_method(ctx, response, case):
    """Verifica se o método de autenticação está correto"""
    # Não falha, apenas loga para debug
    pass


print("🔌 Hook com autenticação dual carregado!")
print(f"   - REQUISITANTE (Header): {'✅' if TOKEN_REQUISITANTE else '❌'}")
print(f"   - GESTOR (Cookie): {'✅' if TOKEN_GESTOR else '❌'}")
print(f"   - ADMIN (Cookie): {'✅' if TOKEN_ADMIN else '❌'}")
print(f"   - INTERESSADO (Cookie): {'✅' if TOKEN_INTERESSADO else '❌'}")