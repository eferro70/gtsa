# Hook gerado automaticamente pelo Step 5 — não editar manualmente
# Compatível com Schemathesis >= 4.0
import sys
import os
from pathlib import Path
import schemathesis

_PIPELINE_DIR = next(
    p for p in Path(__file__).resolve().parents
    if (p / 'utils' / 'auth_loader.py').exists()
)
if str(_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(_PIPELINE_DIR))

try:
    from dotenv import load_dotenv
    _env_file = os.environ.get('ENV_FILE', '.env')
    load_dotenv(_env_file, override=False)
except ImportError:
    pass

try:
    from utils.auth_loader import build_auth_headers
    _AUTH_HEADERS = build_auth_headers()
except Exception as _auth_err:
    import warnings
    warnings.warn(f'auth_loader falhou, rodando sem autenticação: {_auth_err}')
    _AUTH_HEADERS = {}

_QUERY_FIXTURES = {
    "/api/v1/fluxos-interessado": {
        "nome": "",
        "status": "",
        "pendente": "true",
        "sortField": "nome",
        "sortDirection": "ASC",
        "offset": "0",
        "limit": "10"
    },
    "/api/v1/clientes": {
        "nome": "",
        "sigla": "",
        "sortField": "nome",
        "sortDirection": "ASC",
        "limit": "10",
        "offset": "0"
    }
}
ENDPOINT_AUTH_INFO = {
    "GET /metrics": {
        "roles": [],
        "custom_headers": {}
    },
    "GET /api/controlador/hello": {
        "roles": [],
        "custom_headers": {}
    },
    "GET /api/controlador/meu-ip": {
        "roles": [],
        "custom_headers": {}
    },
    "POST /api/contas/perfil/:perfil": {
        "roles": [
            "GESTOR",
            "ADMINISTRADOR"
        ],
        "custom_headers": {}
    },
    "PUT /api/contas/perfil/:perfil/:id": {
        "roles": [
            "GESTOR",
            "ADMINISTRADOR"
        ],
        "custom_headers": {}
    },
    "GET /api/contas/perfil/:perfil": {
        "roles": [
            "ADMINISTRADOR",
            "GESTOR",
            "REQUISITANTE"
        ],
        "custom_headers": {}
    },
    "GET /api/contas/id/:id": {
        "roles": [
            "ADMINISTRADOR",
            "GESTOR",
            "REQUISITANTE"
        ],
        "custom_headers": {}
    },
    "GET /api/contas": {
        "roles": [
            "ADMINISTRADOR",
            "GESTOR",
            "REQUISITANTE"
        ],
        "custom_headers": {}
    },
    "GET /api/contas/sumario": {
        "roles": [
            "ADMINISTRADOR",
            "GESTOR",
            "REQUISITANTE"
        ],
        "custom_headers": {}
    },
    "GET /api/contas/codigo/:codigo": {
        "roles": [
            "ADMINISTRADOR",
            "GESTOR",
            "REQUISITANTE"
        ],
        "custom_headers": {}
    },
    "PATCH /api/contas/reenviar-credenciais-sistema": {
        "roles": [
            "GESTOR",
            "ADMINISTRADOR"
        ],
        "custom_headers": {}
    },
    "PATCH /api/reenviar-links": {
        "roles": [
            "REQUISITANTE"
        ],
        "custom_headers": {}
    },
    "POST /api/documentos": {
        "roles": [
            "REQUISITANTE"
        ],
        "custom_headers": {}
    },
    "DELETE /api/documentos/:id": {
        "roles": [
            "REQUISITANTE"
        ],
        "custom_headers": {}
    },
    "GET /api/webhook/validar/:idRequisitante": {
        "roles": [
            "GESTOR",
            "ADMINISTRADOR"
        ],
        "custom_headers": {}
    },
    "POST /api/fluxos": {
        "roles": [
            "REQUISITANTE"
        ],
        "custom_headers": {}
    },
    "POST /api/fluxos/adicionar": {
        "roles": [
            "REQUISITANTE"
        ],
        "custom_headers": {}
    },
    "PUT /api/fluxos/:id": {
        "roles": [
            "REQUISITANTE"
        ],
        "custom_headers": {}
    },
    "DELETE /api/fluxo/:id": {
        "roles": [
            "REQUISITANTE"
        ],
        "custom_headers": {}
    },
    "PATCH /api/fluxos/:id/iniciar": {
        "roles": [
            "REQUISITANTE"
        ],
        "custom_headers": {}
    },
    "PATCH /api/fluxos/:id/finalizar": {
        "roles": [
            "REQUISITANTE"
        ],
        "custom_headers": {}
    },
    "PATCH /api/fluxos/:id/cancelar": {
        "roles": [
            "REQUISITANTE"
        ],
        "custom_headers": {}
    },
    "PATCH /api/fluxos/:id/arquivar": {
        "roles": [
            "REQUISITANTE"
        ],
        "custom_headers": {}
    },
    "GET /api/fluxos": {
        "roles": [
            "REQUISITANTE"
        ],
        "custom_headers": {}
    },
    "GET /api/fluxo/:id": {
        "roles": [
            "REQUISITANTE"
        ],
        "custom_headers": {}
    },
    "GET /api/fluxos/:id/hashes-documentos/:algoritmo": {
        "roles": [
            "INTERESSADO"
        ],
        "custom_headers": {}
    },
    "GET /api/fluxos/arquivados": {
        "roles": [
            "REQUISITANTE"
        ],
        "custom_headers": {}
    },
    "GET /api/fluxos/:id/interessados": {
        "roles": [
            "REQUISITANTE",
            "INTERESSADO"
        ],
        "custom_headers": {}
    },
    "GET /api/resposta/:id": {
        "roles": [
            "INTERESSADO"
        ],
        "custom_headers": {}
    },
    "GET /api/respostas-gerencial": {
        "roles": [
            "GESTOR",
            "REQUISITANTE"
        ],
        "custom_headers": {}
    },
    "GET /api/fluxos-interessado": {
        "roles": [
            "INTERESSADO"
        ],
        "custom_headers": {}
    },
    "GET /api/fluxos/:id/sumario": {
        "roles": [
            "REQUISITANTE"
        ],
        "custom_headers": {}
    },
    "GET /api/monitoracao/dlqs": {
        "roles": [
            "ADMINISTRADOR"
        ],
        "custom_headers": {}
    },
    "PATCH /api/fluxos/:id/rejeitar": {
        "roles": [
            "INTERESSADO"
        ],
        "custom_headers": {}
    },
    "PATCH /api/fluxos/:id/assinar": {
        "roles": [
            "INTERESSADO"
        ],
        "custom_headers": {}
    },
    "PATCH /api/fluxos/:id/revisar": {
        "roles": [
            "INTERESSADO"
        ],
        "custom_headers": {}
    },
    "PATCH /api/fluxos/:id/revisao": {
        "roles": [
            "INTERESSADO"
        ],
        "custom_headers": {}
    },
    "PATCH /api/fluxos/:id/assinar-serpro-id": {
        "roles": [
            "INTERESSADO"
        ],
        "custom_headers": {}
    },
    "PATCH /api/fluxos/:id/assinar-bird-id": {
        "roles": [
            "INTERESSADO"
        ],
        "custom_headers": {}
    },
    "PATCH /api/fluxos/:id/assinar-safe-id": {
        "roles": [
            "INTERESSADO"
        ],
        "custom_headers": {}
    },
    "PATCH /api/fluxos/:id/assinar-vidaas": {
        "roles": [
            "INTERESSADO"
        ],
        "custom_headers": {}
    },
    "PATCH /api/fluxos/:id/assinar-ds-cloud": {
        "roles": [
            "INTERESSADO"
        ],
        "custom_headers": {}
    },
    "PATCH /api/fluxos/:id/assinar-syn-id": {
        "roles": [
            "INTERESSADO"
        ],
        "custom_headers": {}
    },
    "PATCH /api/fluxos/:id/assinar-certisign": {
        "roles": [
            "INTERESSADO"
        ],
        "custom_headers": {}
    },
    "PATCH /api/fluxos/:id/assinar-desktop/:algoritmo": {
        "roles": [
            "INTERESSADO"
        ],
        "custom_headers": {}
    },
    "GET /api/getlink": {
        "roles": [],
        "custom_headers": {}
    },
    "GET /api/clientes": {
        "roles": [
            "ADMINISTRADOR"
        ],
        "custom_headers": {}
    },
    "POST /api/clientes": {
        "roles": [
            "PAV",
            "ADMINISTRADOR"
        ],
        "custom_headers": {}
    },
    "PUT /api/clientes/:id": {
        "roles": [
            "ADMINISTRADOR"
        ],
        "custom_headers": {}
    },
    "GET /api/clientes/:id": {
        "roles": [
            "ADMINISTRADOR"
        ],
        "custom_headers": {}
    },
    "GET /api/authentication-options": {
        "roles": [],
        "custom_headers": {}
    },
    "POST /api/verify-registration": {
        "roles": [],
        "custom_headers": {}
    },
    "POST /api/verify-authentication": {
        "roles": [],
        "custom_headers": {}
    },
    "PUT /api/login-sistema": {
        "roles": [],
        "custom_headers": {
            "x-chave-acesso-sistema": "X_CHAVE_ACESSO_SISTEMA"
        }
    },
    "GET /api/listar-contas/:email": {
        "roles": [],
        "custom_headers": {}
    },
    "GET /api/confirmacao-conta/:idConta": {
        "roles": [],
        "custom_headers": {}
    },
    "PATCH /api/enviar-otp": {
        "roles": [],
        "custom_headers": {}
    },
    "PATCH /api/verificar-otp": {
        "roles": [],
        "custom_headers": {}
    },
    "PUT /api/token": {
        "roles": [],
        "custom_headers": {}
    },
    "PATCH /api/link": {
        "roles": [],
        "custom_headers": {}
    },
    "GET /api/autenticar-certificado": {
        "roles": [],
        "custom_headers": {
            "x-ssl-client-cert": "X_SSL_CLIENT_CERT"
        }
    },
    "PATCH /api/verificar-certificado": {
        "roles": [],
        "custom_headers": {}
    },
    "PATCH /api/verificar-certificado-nuvem": {
        "roles": [],
        "custom_headers": {}
    },
    "PUT /api/logout": {
        "roles": [],
        "custom_headers": {}
    },
    "POST /api/grupos": {
        "roles": [
            "ADMINISTRADOR",
            "GESTOR"
        ],
        "custom_headers": {}
    },
    "PUT /api/grupos/:id": {
        "roles": [
            "ADMINISTRADOR",
            "GESTOR"
        ],
        "custom_headers": {}
    },
    "GET /api/grupos/id/:id": {
        "roles": [
            "ADMINISTRADOR",
            "GESTOR",
            "REQUISITANTE"
        ],
        "custom_headers": {}
    },
    "GET /api/grupos": {
        "roles": [
            "ADMINISTRADOR",
            "GESTOR",
            "REQUISITANTE"
        ],
        "custom_headers": {}
    },
    "GET /api/grupos-requisitante": {
        "roles": [
            "REQUISITANTE"
        ],
        "custom_headers": {}
    },
    "GET /api/grupos-gestor-mais-requisitante": {
        "roles": [
            "ADMINISTRADOR",
            "GESTOR"
        ],
        "custom_headers": {}
    },
    "PATCH /api/notificar": {
        "roles": [],
        "custom_headers": {}
    },
    "PATCH /api/fluxos/finalizar": {
        "roles": [],
        "custom_headers": {}
    },
    "PATCH /api/fluxos/arquivar": {
        "roles": [],
        "custom_headers": {}
    }
}

import re as _re

def _canonical_path(path):
    """Normaliza um path para comparação: remove prefixo de versão
    (ex: /v1, /v2), converte tanto {param} quanto :param em um
    marcador genérico, e remove barras finais."""
    p = _re.sub(r'/v\d+(?=/|$)', '', path)
    p = _re.sub(r'\{[^}/]+\}', '{X}', p)
    p = _re.sub(r':[^/]+', '{X}', p)
    return p.rstrip('/')

_CANONICAL_AUTH_INFO = {}
for _ep_key, _info in ENDPOINT_AUTH_INFO.items():
    _parts = _ep_key.split(' ', 1)
    if len(_parts) == 2:
        _cmethod, _cpath = _parts[0].upper(), _canonical_path(_parts[1])
        _CANONICAL_AUTH_INFO[(_cmethod, _cpath)] = _info

def _lookup_auth(method, path):
    """Busca info de auth comparando formas canônicas dos paths,
    pois ENDPOINT_AUTH_INFO (vindo do scan do código-fonte) e o path
    enviado pelo Schemathesis (vindo da spec OpenAPI) podem usar
    prefixos de versão e sintaxes de placeholder diferentes
    (ex: /api/fluxos/:id vs /api/v1/fluxos/{id})."""
    key = (method.upper(), _canonical_path(path))
    return _CANONICAL_AUTH_INFO.get(key)

# Endpoints que exigem o cookie de sessão mesmo sem checagem de role
# (ex: endpoints de refresh/renovação que apenas decodificam o token
# atual para emitir um novo, sem exigir uma role específica). O KrakenD
# reporta roles=[] para esses casos, então o fallback genérico (Modo 4)
# nunca tentaria montar o Cookie — por isso a regra explícita abaixo.
FORCE_COOKIE_PATHS = {
    ('PUT', '/api/token'),
}

@schemathesis.hook
def map_headers(context, headers):
    """Injeta autenticação condicional baseada em enriched_endpoints.json."""
    # Na fase Stateful, o Schemathesis pode passar um objeto interno
    # (ex: GeneratedValue) que não suporta atribuição de item direta
    # como um dict normal. Convertendo explicitamente para dict aqui
    # evita 'TypeError: ... object does not support item assignment'.
    if headers is None:
        headers = {}
    elif not isinstance(headers, dict):
        try:
            headers = dict(headers)
        except (TypeError, ValueError):
            headers = {}
    path = context.operation.path
    method = context.operation.method

    canon_key = (method.upper(), _canonical_path(path))
    if canon_key in FORCE_COOKIE_PATHS:
        cookie_name = os.getenv('AUTH_COOKIE_NAME', 'auth_token')
        token = None
        if 'Cookie' in _AUTH_HEADERS:
            ch = _AUTH_HEADERS.get('Cookie', '')
            if '=' in ch:
                token = ch.split('=', 1)[1]
        if not token:
            token = os.getenv('TOKEN_REQUISITANTE') or os.getenv('TOKEN_GESTOR')
        if token:
            headers['Cookie'] = f'{cookie_name}={token}'
            headers.pop('Authorization', None)
            headers['Origin'] = os.getenv('API_BASE_URL', 'http://localhost')
        return headers

    info = _lookup_auth(method, path)

    if info:
        custom = info.get('custom_headers', {})
        if custom:
            # Modo 1: Headers customizados (ex: x-chave-acesso-sistema)
            for hdr_name, env_var in custom.items():
                val = os.getenv(env_var)
                if val:
                    headers[hdr_name] = val
            headers.pop('Authorization', None)
            headers.pop('Cookie', None)
            return headers

        roles = info.get('roles', [])
        if 'REQUISITANTE' in roles:
            # Modo 2: REQUISITANTE → Bearer
            token = os.getenv('TOKEN_REQUISITANTE')
            if not token and 'Authorization' in _AUTH_HEADERS:
                token = _AUTH_HEADERS['Authorization'].replace('Bearer ', '')
            if token:
                headers['Authorization'] = f'Bearer {token}'
                headers.pop('Cookie', None)
            return headers
        elif roles:
            # Modo 3: Outras roles → Cookie
            cookie_name = os.getenv('AUTH_COOKIE_NAME', 'auth_token')
            role = roles[0]
            token = os.getenv(f'TOKEN_{role}')
            if not token and 'Cookie' in _AUTH_HEADERS:
                ch = _AUTH_HEADERS.get('Cookie', '')
                if '=' in ch:
                    token = ch.split('=', 1)[1]
            if token:
                headers['Cookie'] = f'{cookie_name}={token}'
                headers.pop('Authorization', None)
                # CsrfProtectionMiddleware exige Origin/Referer válido
                # para métodos state-changing autenticados via Cookie.
                _origin = os.getenv('API_BASE_URL', 'http://localhost')
                headers['Origin'] = _origin
            return headers

    # Modo 4: Fallback → auth_loader padrão
    for k, v in _AUTH_HEADERS.items():
        headers.setdefault(k, v)
    if 'Cookie' in headers and method.upper() in ('POST', 'PUT', 'PATCH', 'DELETE'):
        headers.setdefault('Origin', os.getenv('API_BASE_URL', 'http://localhost'))
    return headers


@schemathesis.hook
def map_query(context, query):
    """Injeta query params fixos para endpoints GET críticos."""
    path = context.operation.path
    if path in _QUERY_FIXTURES:
        base = dict(_QUERY_FIXTURES[path])
        # Na fase Stateful, 'query' pode vir como um objeto interno
        # (ex: GeneratedValue) que não é iterável como um dict normal.
        # Convertendo explicitamente evita
        # 'TypeError: ... object is not iterable'.
        if query:
            try:
                base.update(dict(query))
            except (TypeError, ValueError):
                pass
        return base
    return query
