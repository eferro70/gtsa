# Hook gerado automaticamente pelo Step 5 — não editar manualmente
# Compatível com Schemathesis >= 4.0
import sys
import os
from pathlib import Path
import schemathesis

# Adiciona o diretório raiz do projeto ao path para importar utils
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Carrega o .env antes de importar o auth_loader
try:
    from dotenv import load_dotenv
    _env_file = os.environ.get('ENV_FILE', '.env')
    load_dotenv(_env_file, override=False)
except ImportError:
    pass  # python-dotenv não instalado; confia nas variáveis já exportadas

# Autenticação resolvida em runtime — suporta OAuth2, cookie e Bearer estático
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


@schemathesis.hook
def map_headers(context, headers):
    """Injeta headers de autenticação sem sobrescrever os gerados pelo fuzzing."""
    if headers is None:
        headers = {}
    for key, value in _AUTH_HEADERS.items():
        headers.setdefault(key, value)
    return headers


@schemathesis.hook
def map_query(context, query):
    """Injeta query params fixos para endpoints GET críticos."""
    path = context.operation.path
    if path in _QUERY_FIXTURES:
        base = dict(_QUERY_FIXTURES[path])
        if query:
            base.update(query)
        return base
    return query
