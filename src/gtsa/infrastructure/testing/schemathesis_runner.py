#!/usr/bin/env python3
"""
step5_schemathesis_with_data.py - Executa Schemathesis injetando os dados
gerados pelo Step 3 (tests/dados/) via spec aumentada com x-example,
e cobre endpoints GET com query params via WSGI hook.

Autenticação condicional baseada em enriched_endpoints.json:
- custom_auth_headers        → headers específicos (ex: x-chave-acesso-sistema)
- Roles REQUISITANTE / PAV   → Authorization: Bearer <TOKEN_<ROLE>>
- Outras roles               → Cookie: <AUTH_COOKIE_NAME>=<TOKEN_<ROLE>>
- Sem role definida          → headers padrão do auth_loader

Migração realizada: substituição do hook map_headers por classes de autenticação
Schemathesis com @schemathesis.auth() para compatibilidade com check ignored_auth.
"""
import json
import os
import subprocess
import sys
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from ..config.settings import load_environment, add_env_arg, get_env_file_from_args
from ..auth.auth_provider import AuthProvider
from ..http.requests_client import RequestsHttpClient


def build_auth_headers() -> Dict[str, str]:
    """Monta os headers de autenticação via ``AuthProvider`` unificado."""
    return AuthProvider(RequestsHttpClient()).build_headers()


def print_auth_summary(headers: Dict[str, str]) -> None:
    AuthProvider(RequestsHttpClient()).print_summary(headers)


# ============================================================================
# CARREGAMENTO DE CONFIGURAÇÕES DO .ENV
# ============================================================================
def load_skip_endpoints(env_value: str) -> List[str]:
    if not env_value:
        return []
    return [item.strip() for item in env_value.split(',') if item.strip()]


def load_skip_methods(env_value: str) -> List[str]:
    if not env_value:
        return ["TRACE", "OPTIONS", "HEAD"]
    return [item.strip().upper() for item in env_value.split(',') if item.strip()]


def load_invalid_schemas(env_value: str) -> List[str]:
    if not env_value:
        return []
    return [item.strip() for item in env_value.split(',') if item.strip()]


def load_exclude_checks(env_value: str) -> List[str]:
    if not env_value:
        return []
    return [item.strip() for item in env_value.split(',') if item.strip()]


def load_file_to_endpoint(env_value: str) -> Dict[str, Tuple[str, str]]:
    mapping = {}
    if not env_value:
        return mapping
    for item in env_value.split(','):
        item = item.strip()
        if not item or ':' not in item:
            continue
        filename, endpoint = item.split(':', 1)
        if '|' not in endpoint:
            continue
        method, path = endpoint.split('|', 1)
        mapping[filename.strip()] = (method.strip().upper(), path.strip())
    return mapping


def load_query_fixtures(env_value: str) -> Dict[str, Dict[str, str]]:
    fixtures = {}
    if not env_value:
        return fixtures
    for item in env_value.split(';'):
        item = item.strip()
        if not item or ':' not in item:
            continue
        path, params_str = item.split(':', 1)
        params = {}
        for param in params_str.split('|'):
            param = param.strip()
            if not param or '=' not in param:
                continue
            key, value = param.split('=', 1)
            params[key.strip()] = value.strip()
        fixtures[path.strip()] = params
    return fixtures


# ============================================================================
# CONFIGURAÇÕES INICIAIS
# ============================================================================
SKIP_ENDPOINTS = []
SKIP_METHODS = ["TRACE", "OPTIONS", "HEAD"]
INVALID_SCHEMA_REFERENCES = []
FILE_TO_ENDPOINT = {}
GET_QUERY_FIXTURES = {}
SCHEMATHESIS_EXCLUDE_CHECKS = []


def load_all_configs_from_env():
    global SKIP_ENDPOINTS, SKIP_METHODS, INVALID_SCHEMA_REFERENCES
    global FILE_TO_ENDPOINT, GET_QUERY_FIXTURES, SCHEMATHESIS_EXCLUDE_CHECKS
    SKIP_ENDPOINTS = load_skip_endpoints(os.getenv("SKIP_ENDPOINTS", ""))
    SKIP_METHODS = load_skip_methods(os.getenv("SKIP_METHODS", ""))
    INVALID_SCHEMA_REFERENCES = load_invalid_schemas(os.getenv("INVALID_SCHEMA_REFERENCES", ""))
    FILE_TO_ENDPOINT = load_file_to_endpoint(os.getenv("FILE_TO_ENDPOINT", ""))
    GET_QUERY_FIXTURES = load_query_fixtures(os.getenv("GET_QUERY_FIXTURES", ""))
    SCHEMATHESIS_EXCLUDE_CHECKS = load_exclude_checks(os.getenv("SCHEMATHESIS_EXCLUDE_CHECKS", ""))


# ============================================================================
# CARREGAMENTO DE AUTH INFO POR ENDPOINT (via enriched_endpoints.json)
# ============================================================================
def load_endpoint_auth_info(output_dir: Path) -> Dict[str, Dict]:
    """
    Lê enriched_endpoints.json e retorna:
    { "METHOD /path": {"roles": [...], "custom_headers": {"header": "ENV_VAR"}} }
    """
    enriched_file = output_dir / "enriched_endpoints.json"
    if not enriched_file.exists():
        runtime_dir = Path(__file__).resolve().parents[4] / "runtime"
        enriched_file = runtime_dir / "enriched_endpoints.json"

    if not enriched_file.exists():
        print(f"⚠️  enriched_endpoints.json não encontrado — sem auth condicional")
        return {}

    try:
        with open(enriched_file, 'r', encoding='utf-8') as f:
            enriched_data = json.load(f)

        auth_map = {}
        for endpoint in enriched_data:
            method = endpoint.get('method', '').upper()
            path = endpoint.get('path', '')
            roles = endpoint.get('roles', [])
            custom_headers = endpoint.get('custom_auth_headers', {})
            if method and path:
                key = f"{method} {path}"
                auth_map[key] = {
                    "roles": roles,
                    "custom_headers": custom_headers
                }

        custom_count = sum(1 for v in auth_map.values() if v.get('custom_headers'))
        roles_count = sum(1 for v in auth_map.values() if v.get('roles'))
        print(f"✅ Auth info carregada: {len(auth_map)} endpoints ({roles_count} com roles, {custom_count} com custom headers)")
        return auth_map
    except Exception as e:
        print(f"❌ Erro ao carregar enriched_endpoints.json: {e}")
        return {}

# ============================================================================
# HELPERS
# ============================================================================
def should_skip_endpoint(method: str, path: str, operation: dict) -> bool:
    method_upper = method.upper()
    endpoint_key = f"{method_upper} {path}"
    if method_upper in SKIP_METHODS:
        print(f"   ⏭️  Pulando {method} {path} (método não suportado)")
        return True
    if endpoint_key in SKIP_ENDPOINTS:
        print(f"   ⏭️  Pulando {endpoint_key} (endpoint problemático conhecido)")
        return True
    if "requestBody" in operation:
        content = operation["requestBody"].get("content", {})
        for content_def in content.values():
            schema = content_def.get("schema", {})
            if "$ref" in schema:
                for invalid_ref in INVALID_SCHEMA_REFERENCES:
                    if invalid_ref in schema["$ref"]:
                        print(f"   ⏭️  Pulando {endpoint_key} (referência inválida: {invalid_ref})")
                        return True
    return False


def load_dados_exemplo(output_dir: Path) -> dict:
    dados = {}
    pipeline_dados_dir = Path(__file__).resolve().parents[4] / "runtime" / "dados"
    output_dados_dir = output_dir / "tests" / "dados"
    if pipeline_dados_dir.exists():
        tests_data_dir = pipeline_dados_dir
    elif output_dados_dir.exists():
        tests_data_dir = output_dados_dir
        print(f"⚠️  Usando fallback de dados: {tests_data_dir}")
    else:
        print(f"⚠️  Diretório de dados não encontrado")
        return dados

    arquivos = list(tests_data_dir.glob("*.json"))
    print(f"\n📂 Dados encontrados em {tests_data_dir}: {len(arquivos)} arquivo(s)")
    for arquivo in sorted(arquivos):
        stem = arquivo.stem
        if stem not in FILE_TO_ENDPOINT:
            print(f"   ⚠️  Sem mapeamento para: {arquivo.name} — ignorado")
            continue
        method, openapi_path = FILE_TO_ENDPOINT[stem]
        try:
            with open(arquivo, 'r', encoding='utf-8') as f:
                body = json.load(f)
            key = f"{method.upper()} {openapi_path}"
            dados[key] = body
            print(f"   ✅ Carregado: {arquivo.name} → {key}")
        except Exception as e:
            print(f"   ❌ Erro ao ler {arquivo.name}: {e}")
    return dados


def inject_examples_into_spec(spec_path: Path, dados: dict, output_dir: Path) -> Path:
    with open(spec_path, 'r') as f:
        spec = json.load(f)
    injetados = 0
    for path, methods in spec.get("paths", {}).items():
        for method, operation in methods.items():
            key = f"{method.upper()} {path}"
            if key in dados and "requestBody" in operation:
                example_body = dados[key]
                content = operation["requestBody"].get("content", {})
                for media_type, content_def in content.items():
                    if "schema" in content_def:
                        content_def["schema"]["example"] = example_body
                        content_def["examples"] = {
                            "step3_example": {"summary": "Dado gerado pelo Step 3", "value": example_body}
                        }
                        injetados += 1
                        print(f"   💉 Injetado exemplo em: {key} ({media_type})")
                        break
    enriched_spec = output_dir / "openapi_enriched.json"
    with open(enriched_spec, 'w') as f:
        json.dump(spec, f, indent=2)
    print(f"\n📁 Spec enriquecida salva em: {enriched_spec}")
    print(f"   💉 Total de exemplos injetados: {injetados}")
    return enriched_spec


def generate_hook_file(query_fixtures: dict, auth_headers: dict,
                       output_dir: Path, endpoint_auth_info: Dict[str, Dict]) -> Path:
    """
    Gera schemathesis_hooks.py com classe de autenticação unificada.
    """
    fixtures_repr = json.dumps(query_fixtures, ensure_ascii=False, indent=4)
    auth_info_repr = json.dumps(endpoint_auth_info, ensure_ascii=False, indent=4)

    lines = [
        "# Hook gerado automaticamente pelo Step 5 — não editar manualmente",
        "# Classe de autenticação unificada com @schemathesis.auth()",
        "import sys",
        "import os",
        "from pathlib import Path",
        "import schemathesis",
        "",
        "# Garante que o pacote 'gtsa' seja importável",
        "for _p in Path(__file__).resolve().parents:",
        "    if (_p / 'pyproject.toml').exists():",
        "        _src = _p / 'src'",
        "        if _src.exists() and str(_src) not in sys.path:",
        "            sys.path.insert(0, str(_src))",
        "        break",
        "",
        "try:",
        "    from dotenv import load_dotenv",
        "    _env_file = os.environ.get('ENV_FILE', '.env')",
        "    load_dotenv(_env_file, override=False)",
        "except ImportError:",
        "    pass",
        "",
        "try:",
        "    from gtsa.infrastructure.auth.auth_provider import AuthProvider",
        "    from gtsa.infrastructure.http.requests_client import RequestsHttpClient",
        "    _AUTH_HEADERS = AuthProvider(RequestsHttpClient()).build_headers()",
        "except Exception as _auth_err:",
        "    import warnings",
        "    warnings.warn(f'auth_loader falhou, rodando sem autenticação: {_auth_err}')",
        "    _AUTH_HEADERS = {}",
        "",
        f"_QUERY_FIXTURES = {fixtures_repr}",
        f"ENDPOINT_AUTH_INFO = {auth_info_repr}",
        "",
        "import re as _re",
        "",
        "def _canonical_path(path):",
        '    """Normaliza um path para comparação."""',
        "    p = _re.sub(r'/v\\d+(?=/|$)', '', path)",
        "    p = _re.sub(r'\\{[^}/]+\\}', '{X}', p)",
        "    p = _re.sub(r':[^/]+', '{X}', p)",
        "    return p.rstrip('/')",
        "",
        "_CANONICAL_AUTH_INFO = {}",
        "for _ep_key, _info in ENDPOINT_AUTH_INFO.items():",
        "    _parts = _ep_key.split(' ', 1)",
        "    if len(_parts) == 2:",
        "        _cmethod, _cpath = _parts[0].upper(), _canonical_path(_parts[1])",
        "        _CANONICAL_AUTH_INFO[(_cmethod, _cpath)] = _info",
        "",
        "def _lookup_auth(method, path):",
        '    """Busca info de auth comparando formas canônicas dos paths."""',
        "    key = (method.upper(), _canonical_path(path))",
        "    return _CANONICAL_AUTH_INFO.get(key)",
        "",
        "# Endpoints que exigem Cookie mesmo sem role definida",
        "FORCE_COOKIE_PATHS = {",
        "    ('PUT', '/api/token'),",
        "    ('PUT', '/api/v1/token'),",
        "}",
        "",
        "def _token_from_authorization(value):",
        "    if not value:",
        "        return None",
        "    raw = str(value).strip()",
        "    if not raw:",
        "        return None",
        "    if raw.lower().startswith('bearer '):",
        "        raw = raw[7:]",
        "    raw = raw.strip()",
        "    return raw or None",
        "",
        "def _get_token_from_env(role):",
        "    \"\"\"Busca token especifico da role. Sem fallback cross-role.\"\"\"",
        "    if not role:",
        "        return None",
        "    return os.getenv(f'TOKEN_{role}')",
        "",
        "def _bearer_fallback():",
        "    \"\"\"Fallback Bearer: usa apenas Authorization de _AUTH_HEADERS (mesmo formato).\"\"\"",
        "    if 'Authorization' in _AUTH_HEADERS:",
        "        return _token_from_authorization(_AUTH_HEADERS.get('Authorization'))",
        "    return None",
        "",
        "def _cookie_fallback():",
        "    \"\"\"Fallback Cookie: usa apenas Cookie de _AUTH_HEADERS (mesmo formato).\"\"\"",
        "    if 'Cookie' in _AUTH_HEADERS:",
        "        ch = _AUTH_HEADERS.get('Cookie', '')",
        "        if '=' in ch:",
        "            token = ch.split('=', 1)[1].split(';', 1)[0].strip()",
        "            if token:",
        "                return token",
        "    return None",
        "",
        "# ===================================================================",
        "# CLASSE DE AUTENTICAÇÃO ÚNICA",
        "# ===================================================================",
        "@schemathesis.auth()",
        "class ConditionalAuth:",
        "    def get(self, case: schemathesis.Case, ctx: schemathesis.AuthContext):",
        '        """Retorna os headers de autenticação apropriados para o endpoint."""',
        "        path = case.operation.path",
        "        method = case.operation.method",
        "        canon_key = (method.upper(), _canonical_path(path))",
        "        ",
        "        # 1. FORCE_COOKIE_PATHS",
        "        if canon_key in FORCE_COOKIE_PATHS:",
        "            cookie_name = os.getenv('AUTH_COOKIE_NAME', 'auth_token')",
        "            token = _cookie_fallback()",
        "            if token:",
        "                origin = os.getenv('API_BASE_URL', 'http://localhost')",
        "                return {",
        "                    'Cookie': f'{cookie_name}={token}',",
        "                    'Origin': origin,",
        "                    'Referer': f'{origin}/'",
        "                }",
        "            return {}",
        "        ",
        "        # 2. Busca info do endpoint",
        "        info = _lookup_auth(method, path)",
        "        ",
        "        if not info:",
        "            # Sem info → fallback para auth_loader",
        "            return dict(_AUTH_HEADERS)",
        "        ",
        "        # 3. Headers Customizados (prioridade máxima)",
        "        custom = info.get('custom_headers', {})",
        "        if custom:",
        "            headers = {}",
        "            for hdr_name, env_var in custom.items():",
        "                val = os.getenv(env_var)",
        "                if val:",
        "                    headers[hdr_name] = val",
        "            # Retorna IMEDIATAMENTE, sem tentar outros métodos",
        "            if headers:",
        "                return headers",
        "            return {}",
        "        ",
        "        # 4. Roles",
        "        roles = info.get('roles', [])",
        "        origin = os.getenv('API_BASE_URL', 'http://localhost')",
        "        cookie_name = os.getenv('AUTH_COOKIE_NAME', 'auth_token')",
        "        _BEARER_ONLY_ROLES = ('REQUISITANTE', 'PAV')",
        "        _bearer_role = next((r for r in roles if r in _BEARER_ONLY_ROLES), None)",
        "        ",
        "        if _bearer_role:",
        "            # Token especifico da role, com fallback só pra Authorization (mesmo formato)",
        "            token = _get_token_from_env(_bearer_role) or _bearer_fallback()",
        "            if token:",
        "                return {'Authorization': f'Bearer {token}'}",
        "            return {}",
        "        elif roles:",
        "            # APENAS Cookie para outras roles",
        "            role = roles[0]",
        "            # Token especifico da role, com fallback só pra Cookie (mesmo formato)",
        "            cookie_token = _get_token_from_env(role) or _cookie_fallback()",
        "            if cookie_token:",
        "                return {",
        "                    'Cookie': f'{cookie_name}={cookie_token}',",
        "                    'Origin': origin,",
        "                    'Referer': f'{origin}/'",
        "                }",
        "            return {}",
        "        ",
        "        # 5. Fallback",
        "        return dict(_AUTH_HEADERS)",
        "    ",
        "    def set(self, case: schemathesis.Case, data, ctx: schemathesis.AuthContext) -> None:",
        '        """Injeta os headers no caso de teste."""',
        "        if not data:",
        "            return",
        "        ",
        "        case.headers = case.headers or {}",
        "        ",
        "        # Remove TODOS os headers de autenticação (case-insensitive)",
        "        auth_headers = ['authorization', 'cookie', 'x-chave-acesso-sistema']",
        "        for key in list(case.headers.keys()):",
        "            if key.lower() in auth_headers:",
        "                del case.headers[key]",
        "        ",
        "        # Injeta os novos headers",
        "        for k, v in data.items():",
        "            if v is not None:",
        "                case.headers[k] = str(v)",
        "        ",
        "        # SEMPRE adicionar Origin/Referer se Cookie estiver presente",
        "        if 'Cookie' in case.headers:",
        "            origin = os.getenv('API_BASE_URL', 'http://localhost')",
        "            case.headers.setdefault('Origin', origin)",
        "            case.headers.setdefault('Referer', f'{origin}/')",
        "",
        "# ===================================================================",
        "# HOOK map_query",
        "# ===================================================================",
        "@schemathesis.hook",
        "def map_query(context, query):",
        '    """Injeta query params fixos para endpoints GET críticos."""',
        "    path = context.operation.path",
        "    if path in _QUERY_FIXTURES:",
        "        base = dict(_QUERY_FIXTURES[path])",
        "        if query:",
        "            try:",
        "                base.update(dict(query))",
        "            except (TypeError, ValueError):",
        "                pass",
        "        return base",
        "    return query",
    ]

    hook_code = "\n".join(lines) + "\n"

    # Appenda hooks específicos da API, se configurados
    hooks_extra_path = os.getenv("SCHEMATHESIS_HOOKS_EXTRA", "")
    if hooks_extra_path:
        extra_file = Path(hooks_extra_path)
        if not extra_file.is_absolute():
            extra_file = Path(__file__).resolve().parents[4] / hooks_extra_path
        if extra_file.exists():
            hook_code += "\n# === Hooks específicos da API (SCHEMATHESIS_HOOKS_EXTRA) ===\n"
            hook_code += extra_file.read_text(encoding="utf-8")
            print(f"      → Hooks extras carregados: {extra_file}")
        else:
            print(f"   ⚠️  SCHEMATHESIS_HOOKS_EXTRA definido mas arquivo não encontrado: {extra_file}")

    output_dir.mkdir(parents=True, exist_ok=True)
    hook_path = output_dir / "schemathesis_hooks.py"
    with open(hook_path, "w", encoding="utf-8") as f:
        f.write(hook_code)
    print(f"   🔧 Hook gerado em: {hook_path}")
    print(f"      → Auth condicional: {len(endpoint_auth_info)} endpoints mapeados")
    return hook_path

def _strip_redundant_auth_header_params(spec: dict) -> int:
    """Remove parâmetros soltos 'in: header, name: Authorization/Cookie'
    quando a operação já tem 'security' definido.

    Esses dois mecanismos são redundantes no OpenAPI (o 'security' já
    diz que o endpoint exige auth), mas quando ambos aparecem juntos o
    Schemathesis passa a fuzzar 'Authorization'/'Cookie' como parâmetro
    normal de dado -- inclusive em casos de Coverage/Fuzzing que não são
    testes de segurança propositais. Isso faz o header (às vezes lixo,
    às vezes ausente) chegar pronto no hook `map_headers`, que então
    respeita esse valor "explícito" e nunca injeta a credencial real.
    Removendo o parâmetro duplicado, o `security` scheme continua
    documentando a exigência de auth, mas só os checks de segurança
    dedicados do Schemathesis (missing_required_header, etc.) mexem
    nesse header -- a geração normal para de fuzzá-lo à toa.
    """
    removed = 0
    global_security = spec.get("security")
    for path, methods in spec.get("paths", {}).items():
        for method, op in methods.items():
            if not (op.get("security") or global_security):
                continue
            params = op.get("parameters", [])
            kept = []
            for p in params:
                if p.get("in") == "header" and p.get("name", "").lower() in ("authorization", "cookie"):
                    removed += 1
                    continue
                kept.append(p)
            if len(kept) != len(params):
                op["parameters"] = kept
    return removed


def filter_openapi_spec(spec_path: Path, output_dir: Path) -> Path:
    with open(spec_path, 'r') as f:
        spec = json.load(f)
    original_count = sum(len(methods) for methods in spec.get("paths", {}).values())
    print(f"\n📊 Endpoints originais: {original_count}")
    filtered_paths = {}
    for path, methods in spec.get("paths", {}).items():
        filtered_methods = {
            method: op for method, op in methods.items()
            if not should_skip_endpoint(method, path, op)
        }
        if filtered_methods:
            filtered_paths[path] = filtered_methods
    filtered_count = sum(len(m) for m in filtered_paths.values())
    print(f"\n📈 Resumo da filtragem:")
    print(f"   ✅ Endpoints mantidos: {filtered_count}")
    print(f"   🚫 Endpoints removidos: {original_count - filtered_count}")
    spec["paths"] = filtered_paths
    removed_auth_params = _strip_redundant_auth_header_params(spec)
    if removed_auth_params:
        print(f"   🔧 Parâmetros Authorization/Cookie redundantes removidos: {removed_auth_params}")
    filtered_spec = output_dir / "openapi_filtered.json"
    with open(filtered_spec, 'w') as f:
        json.dump(spec, f, indent=2)
    print(f"   📁 Spec filtrada salva em: {filtered_spec}")
    return filtered_spec


def build_schemathesis_command(spec_path: Path, hook_path: Path,
                               output_dir: Path, base_url: str, max_examples: int,
                               verbose: bool, exclude_checks: Optional[List[str]] = None) -> Tuple[list, dict]:
    junit_xml = output_dir / "schemathesis_results.xml"
    cmd = [
        "schemathesis", "run", str(spec_path),
        "--url", base_url,
        "--checks", "all",
    ]
    for check_name in (exclude_checks or []):
        cmd += ["--exclude-checks", check_name]
    cmd += [
        "-n", str(max_examples),
        "--report", "junit",
        "--report-junit-path", str(junit_xml),
        "--seed", "42",
        "--output-truncate", "false",
    ]
    if verbose:
        cmd.append("-v")

    hook_module_name = hook_path.stem
    hook_dir = str(hook_path.parent)
    current_pythonpath = os.environ.get("PYTHONPATH", "")
    new_pythonpath = f"{hook_dir}:{current_pythonpath}" if current_pythonpath else hook_dir
    env_file = os.environ.get("ENV_FILE", "")
    extra_env = {
        "SCHEMATHESIS_HOOKS": hook_module_name,
        "PYTHONPATH": new_pythonpath,
        **({"ENV_FILE": env_file} if env_file else {}),
    }
    return cmd, extra_env


# ============================================================================
# MAIN
# ============================================================================
def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Executa Schemathesis com dados reais e autenticação condicional",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXEMPLOS:
python3 step5_schemathesis_with_data.py --output-dir output-projeto --env-file .env.prod
python3 step5_schemathesis_with_data.py --output-dir output-projeto --verbose
"""
    )
    add_env_arg(parser)
    parser.add_argument("--verbose", "-v", action="store_true", help="Exibe logs detalhados")
    parser.add_argument("--output-dir", "-d", default=None, help="Diretório para saída (padrão: output)")
    parser.add_argument("--only-high-risk", action="store_true", help="Testa apenas endpoints de alto risco")
    args = parser.parse_args()

    load_environment(env_file=args.env_file, verbose=args.verbose)
    load_all_configs_from_env()

    if args.output_dir:
        output_dir = Path(args.output_dir)
        if not output_dir.is_absolute():
            project_root = Path(__file__).resolve().parents[4]
            output_dir = project_root / args.output_dir
    else:
        env_output_dir = os.getenv("REPORTS_DIR", "output")
        output_dir = Path(env_output_dir)
        if not output_dir.is_absolute():
            project_root = Path(__file__).resolve().parents[4]
            output_dir = project_root / env_output_dir
    output_dir = output_dir.resolve()

    BASE_URL = os.getenv("API_BASE_URL", "http://localhost")
    MAX_EXAMPLES = int(os.getenv("MAX_EXAMPLES", "10"))
    VERBOSE = args.verbose or os.getenv("VERBOSE", "false").lower() == "true"
    ONLY_HIGH_RISK = args.only_high_risk or os.getenv("ONLY_HIGH_RISK", "false").lower() == "true"

    try:
        auth_headers = build_auth_headers()
    except ValueError as e:
        print(f"\n❌ Erro crítico de autenticação: {e}")
        sys.exit(1)

    print("\n" + "="*60)
    print("🚀 Schemathesis - Testes de API com auth condicional")
    print("="*60)
    print(f"\n📋 Configurações gerais:")
    print(f"   - Base URL:          {BASE_URL}")
    print(f"   - Max examples:      {MAX_EXAMPLES}")
    print(f"   - Apenas alto risco: {ONLY_HIGH_RISK}")
    print(f"   - Verbose:           {VERBOSE}")
    print(f"   - Output dir:        {output_dir}")

    # ─── CARREGA AUTH INFO POR ENDPOINT ──────────────────────────────────
    print("\n📋 Carregando informações de autenticação por endpoint...")
    endpoint_auth_info = load_endpoint_auth_info(output_dir)

    if ONLY_HIGH_RISK:
        enriched_file = output_dir / "enriched_endpoints.json"
        if not enriched_file.exists():
            runtime_dir = Path(__file__).resolve().parents[4] / "runtime"
            enriched_file = runtime_dir / "enriched_endpoints.json"
        if enriched_file.exists():
            try:
                with open(enriched_file, 'r', encoding='utf-8') as f:
                    enriched_data = json.load(f)
                high_risk_endpoints = [e for e in enriched_data if e.get('risk_level') == 'alto']
                print(f"   ✅ Encontrados {len(high_risk_endpoints)} endpoints de alto risco")
                ALLOWED_ENDPOINTS = [f"{e.get('method', '').upper()} {e.get('path', '')}" for e in high_risk_endpoints]

                def should_skip_endpoint_with_high_risk(method: str, path: str, operation: dict) -> bool:
                    method_upper = method.upper()
                    endpoint_key = f"{method_upper} {path}"
                    if ONLY_HIGH_RISK and endpoint_key not in ALLOWED_ENDPOINTS:
                        return True
                    return should_skip_endpoint(method, path, operation)

                global should_skip_endpoint
                should_skip_endpoint = should_skip_endpoint_with_high_risk
            except Exception as e:
                print(f"   ❌ Erro ao carregar enriched_endpoints.json: {e}")

    print(f"\n📋 Configurações carregadas do .env:")
    print(f"   - SKIP_ENDPOINTS:            {len(SKIP_ENDPOINTS)} endpoints")
    print(f"   - SKIP_METHODS:              {SKIP_METHODS}")
    print(f"   - FILE_TO_ENDPOINT:          {len(FILE_TO_ENDPOINT)} mapeamentos")
    print(f"   - GET_QUERY_FIXTURES:        {len(GET_QUERY_FIXTURES)} fixtures")
    print(f"   - SCHEMATHESIS_EXCLUDE_CHECKS: {SCHEMATHESIS_EXCLUDE_CHECKS or '(nenhum)'}")
    print(f"   - ENDPOINT_AUTH_INFO:        {len(endpoint_auth_info)} endpoints")
    custom_count = sum(1 for v in endpoint_auth_info.values() if v.get('custom_headers'))
    print(f"     ↳ com custom headers:      {custom_count}")
    print_auth_summary(auth_headers)

    openapi_json = Path(os.getenv("OPENAPI_JSON", "openapi.json"))
    if not openapi_json.exists():
        openapi_json = output_dir / "openapi.json"
    if not openapi_json.exists():
        print(f"\n❌ OpenAPI não encontrada: {openapi_json}")
        sys.exit(1)
    print(f"\n📄 OpenAPI de origem: {openapi_json}")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("\n📝 Filtrando OpenAPI spec...")
    filtered_spec = filter_openapi_spec(openapi_json, output_dir)

    print("\n📂 Carregando dados gerados pelo Step 3...")
    dados = load_dados_exemplo(output_dir)

    sem_dados = []
    with open(filtered_spec, 'r') as f:
        spec = json.load(f)
    for path, methods in spec.get("paths", {}).items():
        for method in methods:
            key = f"{method.upper()} {path}"
            if "requestBody" in methods[method] and key not in dados:
                sem_dados.append(key)
    if sem_dados:
        print(f"\n⚠️  {len(sem_dados)} endpoint(s) com body mas SEM dados do Step 3 (usarão fuzzing):")
        for e in sem_dados[:10]:
            print(f"   - {e}")
        if len(sem_dados) > 10:
            print(f"   ... e mais {len(sem_dados) - 10}")

    print("\n💉 Injetando exemplos do Step 3 na spec...")
    enriched_spec = inject_examples_into_spec(filtered_spec, dados, output_dir)

    # ── 4. Gera hook unificado contendo as Query Fixtures e Auth Headers ───
    print("\n🔧 Gerando hook customizado de query params e autenticação...")
    hook_path = generate_hook_file(GET_QUERY_FIXTURES, auth_headers, output_dir, endpoint_auth_info)

    print("\n" + "="*60)
    print("🚀 Executando comando do Schemathesis")
    print("="*60)
    cmd, extra_env = build_schemathesis_command(
        enriched_spec, hook_path, output_dir, BASE_URL, MAX_EXAMPLES, VERBOSE,
        exclude_checks=SCHEMATHESIS_EXCLUDE_CHECKS
    )
    run_env = {**os.environ, **extra_env}
    print(f"Comando: {' '.join(cmd)}")
    print(f"   SCHEMATHESIS_HOOKS={extra_env['SCHEMATHESIS_HOOKS']}")
    print(f"   PYTHONPATH={extra_env['PYTHONPATH']}")
    print("-"*60)
    result = subprocess.run(cmd, capture_output=True, text=True, env=run_env)

    logfile = output_dir / "schemathesis_execution.log"
    with open(logfile, "w", encoding="utf-8") as f:
        f.write(f"Comando: {' '.join(cmd)}\n")
        f.write(f"SCHEMATHESIS_HOOKS: {extra_env['SCHEMATHESIS_HOOKS']}\n")
        f.write(f"Data: {datetime.now().isoformat()}\n")
        f.write(f"Headers injetados (chaves): {list(auth_headers.keys())}\n")
        f.write(f"Dados Step 3 carregados: {len(dados)}\n")
        f.write(f"Query fixtures: {list(GET_QUERY_FIXTURES.keys())}\n")
        f.write(f"SKIP_ENDPOINTS: {SKIP_ENDPOINTS}\n")
        f.write(f"SKIP_METHODS: {SKIP_METHODS}\n")
        f.write(f"SCHEMATHESIS_EXCLUDE_CHECKS: {SCHEMATHESIS_EXCLUDE_CHECKS}\n")
        f.write(f"ENDPOINT_AUTH_INFO: {len(endpoint_auth_info)} endpoints\n")
        f.write(f"OUTPUT_DIR: {output_dir}\n")
        f.write(f"ONLY_HIGH_RISK: {ONLY_HIGH_RISK}\n")
        f.write("---\n")
        f.write(result.stdout)
        if result.stderr:
            f.write("\n--- STDERR ---\n")
            f.write(result.stderr)

    print(f"\n📄 Registro detalhado salvo em: {logfile}")
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    junit_xml = output_dir / "schemathesis_results.xml"
    if junit_xml.exists():
        print(f"\n📊 Relatório JUnit salvo em: {junit_xml}")

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()