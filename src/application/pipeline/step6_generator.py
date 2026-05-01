#!/usr/bin/env python3
"""
step7_generator.py (OTIMIZADO E CORRIGIDO)
------------------
Gera automaticamente arquivos de teste para APIs REST a partir de uma especificação OpenAPI e endpoints enriquecidos.
AGORA com suporte a:
- Filtragem por nível de risco
- Testes específicos por vulnerabilidade
- Verificações de PII
- Priorização de endpoints críticos
"""

import json
import os
import sys
import textwrap
from pathlib import Path

# Carrega variáveis do .env automaticamente
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv não instalado. Variáveis do .env não serão carregadas automaticamente.")


class SmartSchemathesisGenerator:
    def __init__(self, openapi_file: str):
        self.enriched_file = Path("src/application/pipeline/tests/enriched_endpoints.json").resolve()
        self.openapi_file = Path(openapi_file).resolve()
        self.output_dir = Path("src/application/pipeline/tests").resolve()
        self.api_base = os.getenv("API_BASE_URL", "http://localhost")
        self.load_data()
    
    def load_data(self):
        """Carrega os dados com verificação e logging explícito"""
        print(f"🔍 Verificando arquivos de entrada...")
        
        if not self.enriched_file.exists():
            raise FileNotFoundError(
                f"❌ Arquivo não encontrado: {self.enriched_file}\n"
                f"💡 Execute primeiro: python3 step5_analyzer_unified.py"
            )
        print(f"✅ enriched_endpoints.json encontrado: {self.enriched_file}")
        
        if not self.openapi_file.exists():
            raise FileNotFoundError(f"❌ Arquivo não encontrado: {self.openapi_file}")
        print(f"✅ OpenAPI spec encontrado: {self.openapi_file}")
        
        try:
            with open(self.enriched_file, 'r', encoding='utf-8') as f:
                self.endpoints = json.load(f)
            print(f"✅ {len(self.endpoints)} endpoints carregados de enriched_endpoints.json")
        except Exception as e:
            raise RuntimeError(f"❌ Erro ao ler enriched_endpoints.json: {e}")
        
        try:
            with open(self.openapi_file, 'r', encoding='utf-8') as f:
                self.openapi_schema = json.load(f)
            print(f"✅ OpenAPI schema carregado")
        except Exception as e:
            raise ValueError(f"❌ Erro ao parsear OpenAPI: {e}")
        
        # Estatísticas de segurança
        high_risk = sum(1 for e in self.endpoints if e.get('risk_level') == 'alto')
        critical_vulns = sum(1 for e in self.endpoints if any(v.get('severity') == 'critical' for v in e.get('vulnerabilities_detailed', [])))
        print(f"📊 Estatísticas de segurança: {high_risk} endpoints de alto risco, {critical_vulns} com vulnerabilidades críticas")

    def generate_auth_hooks(self) -> str:
        """Gera hooks de autenticação aprimorados"""
        return textwrap.dedent("""
            import os
            import json
            from dotenv import load_dotenv
            from pathlib import Path

            # Busca auth_config.json subindo diretórios
            def find_config(filename):
                path = Path.cwd()
                for _ in range(6):
                    candidate = path / filename
                    if candidate.exists():
                        return candidate
                    candidate_config = path / 'config' / filename
                    if candidate_config.exists():
                        return candidate_config
                    if path.parent == path:
                        break
                    path = path.parent
                raise FileNotFoundError(f"Arquivo de configuração de autenticação não encontrado: {filename}")

            config_path = find_config('auth_config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                AUTH_CONFIG = json.load(f)

            # Busca .env
            def find_env(filename):
                path = Path.cwd()
                for _ in range(6):
                    candidate = path / filename
                    if candidate.exists():
                        return candidate
                    if path.parent == path:
                        break
                    path = path.parent
                return None

            env_path = find_env('.env')
            if env_path:
                load_dotenv(dotenv_path=env_path)

            def get_env_value(var):
                val = os.getenv(var)
                if val is None:
                    print(f"[!] Variável de ambiente '{var}' não encontrada no .env")
                return val

            def apply_auth(case, role=None):
                if case.headers is None:
                    case.headers = {}

                # Headers fixos
                for header in AUTH_CONFIG.get("fixed_headers", []):
                    header_name = header["name"]
                    env_var = header.get("env_var")
                    value = header.get("value")
                    if env_var:
                        env_val = get_env_value(env_var)
                        if env_val:
                            case.headers[header_name] = env_val
                    elif value:
                        case.headers[header_name] = value

                # Token baseado na role
                role_tokens = AUTH_CONFIG.get("role_tokens", {})
                target_role = role or AUTH_CONFIG.get("default_role")
                
                if target_role and target_role in role_tokens:
                    token_env = role_tokens[target_role].get("env_var")
                    token_value = role_tokens[target_role].get("value")
                    token = get_env_value(token_env) if token_env else token_value
                    if token:
                        auth_header = AUTH_CONFIG.get("auth_header", "Authorization")
                        prefix = AUTH_CONFIG.get("auth_prefix", "Bearer ")
                        case.headers[auth_header] = f"{prefix}{token.strip()}"
                
                return case.headers.get(auth_header) is not None
        """).strip()

    def generate_llm_hooks(self) -> str:
        """Gera hooks com verificações de segurança adicionais"""
        return textwrap.dedent("""
            import schemathesis
            from .auth_hooks import apply_auth

            @schemathesis.hook
            def before_call(context, case, **kwargs):
                if case.headers is None:
                    case.headers = {}
                
                # Força headers padrão
                case.headers["Content-Type"] = "application/json"
                case.headers["Accept"] = "application/json"
                
                # Extrai role do caso (se disponível)
                role = getattr(case, 'role', None)
                apply_auth(case, role=role)
                
                # Log de segurança (opcional)
                if hasattr(case, 'security_context'):
                    vulns = case.security_context.get('vulnerabilities', [])
                    if vulns:
                        print(f"[SECURITY] Testando endpoint com vulnerabilidades conhecidas: {', '.join(vulns)}")
        """).strip()

    def generate_smart_test_file(self) -> str:
        """Gera arquivo de teste com verificações de segurança avançadas"""
        swagger_path = str(self.openapi_file)
        api_base = self.api_base
        
        # Template dividido em partes para evitar problemas com dedent
        template_header = f'''
import jsonschema
import os
import sys
import json
import argparse
import yaml
import random
import string
import re
from pathlib import Path
from src.infrastructure.interfaces.hooks.llm_hooks import before_call
from hypothesis import given, settings, HealthCheck, strategies as st

try:
    import requests
except ImportError:
    requests = None

LOG_FILE = os.environ.get('TEST_LOG_FILE', 'test_api_llm.log')
SUMMARY_FILE = os.environ.get('TEST_SUMMARY_FILE', 'test_api_llm_summary.md')

def log_test(message, status="INFO"):
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"[{{status}}] {{message}}\\n")
    except Exception:
        pass

SPEC_FILE = r"{swagger_path}"

def load_openapi_spec():
    with open(SPEC_FILE, 'r') as f:
        if SPEC_FILE.endswith('.yaml') or SPEC_FILE.endswith('.yml'):
            return yaml.safe_load(f)
        return json.load(f)

def normalize_endpoint_path(endpoint):
    if not endpoint:
        return endpoint
    normalized = endpoint.strip()
    normalized = re.sub(r':([^/]+)', r'{{\\1}}', normalized)
    normalized = re.sub(r'/+', '/', normalized)
    return normalized

def build_openapi_path_candidates(endpoint):
    candidates = []

    def _add(path):
        if path and path not in candidates:
            candidates.append(path)

    normalized = normalize_endpoint_path(endpoint)
    _add(normalized)

    if normalized.startswith('/api/v1/'):
        _add(normalized.replace('/api/v1/', '/api/', 1))
    elif normalized.startswith('/api/'):
        _add(normalized.replace('/api/', '/api/v1/', 1))

    return candidates

def find_operation(spec, endpoint, method):
    if not endpoint or not method:
        return None, None

    paths = spec.get('paths', {{}})
    method_lower = method.lower()

    for candidate in build_openapi_path_candidates(endpoint):
        op = paths.get(candidate, {{}})
        if method_lower in op:
            return candidate, op.get(method_lower)

    return None, None

def make_request(method, endpoint, headers, data=None, base_url="{api_base}", timeout=10, verify_ssl=False):
    url = f"{{base_url.rstrip('/')}}{{endpoint}}"
    if requests is None:
        raise RuntimeError("requests não instalado")
    if not verify_ssl:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    if method.upper() in ["GET", "DELETE"]:
        return requests.request(method, url, headers=headers, timeout=timeout, verify=verify_ssl)
    else:
        return requests.request(method, url, headers=headers, json=data, timeout=timeout, verify=verify_ssl)

def generate_data_from_schema(schema, depth=0, avoid_pii=False):
    if depth > 10:
        return None
    schema_type = schema.get("type")
    if "$ref" in schema:
        return "ref-value"
    
    pii_patterns = ['cpf', 'cnpj', 'email', 'telefone', 'celular', 'rg', 'documento', 'senha', 'password']
    
    if schema_type == "object":
        props = schema.get("properties", {{}})
        required = schema.get("required", [])
        result = {{}}
        for k, v in props.items():
            if avoid_pii and any(p in k.lower() for p in pii_patterns):
                continue
            if k in required or random.random() > 0.3:
                result[k] = generate_data_from_schema(v, depth+1, avoid_pii)
        return result
    if schema_type == "array":
        items = schema.get("items", {{}})
        return [generate_data_from_schema(items, depth+1, avoid_pii)]
    if schema_type == "string":
        format_pattern = schema.get("format")
        if format_pattern == "email":
            return f"test{{random.randint(1,999)}}@example.com"
        if format_pattern == "uuid":
            return f"550e8400-e29b-41d4-a716-{{random.randint(100000000000, 999999999999)}}"
        if "password" in schema.get("description", "").lower():
            return "Test@123456"
        return ''.join(random.choices(string.ascii_letters, k=8))
    if schema_type == "integer":
        return random.randint(0, 1000)
    if schema_type == "number":
        return random.random() * 1000
    if schema_type == "boolean":
        return random.choice([True, False])
    return None

def check_pii_leakage(response_text, endpoint_pii):
    if not endpoint_pii:
        return True
    pii_patterns = {{
        'cpf': r'\\d{{3}}\\.\\d{{3}}\\.\\d{{3}}-\\d{{2}}|\\d{{11}}',
        'cnpj': r'\\d{{2}}\\.\\d{{3}}\\.\\d{{3}}/\\d{{4}}-\\d{{2}}|\\d{{14}}',
        'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{{2,}}',
        'telefone': r'\\(?\\d{{2}}\\)?\\s?\\d{{4,5}}-?\\d{{4}}',
        'rg': r'\\d{{2}}\\.\\d{{3}}\\.\\d{{3}}-\\d{{1}}|\\d{{9}}'
    }}
    for pii_type in endpoint_pii:
        if pii_type in pii_patterns and re.search(pii_patterns[pii_type], response_text):
            return False
    return True

def run_test(name, fn, critical=False):
    try:
        fn()
        if critical:
            log_test(f"✅ {{name}} (CRÍTICO) passou", "SUCCESS")
        else:
            log_test(f"✅ {{name}} passou", "SUCCESS")
        return True
    except AssertionError as e:
        severity = "CRITICAL" if critical else "ERROR"
        log_test(f"❌ {{name}} falhou: {{e}}", severity)
        return False
    except Exception as e:
        severity = "CRITICAL" if critical else "ERROR"
        log_test(f"❌ {{name}} erro inesperado: {{e}}", severity)
        return False

def main():
    parser = argparse.ArgumentParser(description='Testes avançados de API com segurança')
    parser.add_argument('--method', help='Método HTTP')
    parser.add_argument('--endpoint', help='Endpoint')
    parser.add_argument('--test-data', help='Arquivo JSON com dados de teste')
    parser.add_argument('--max-examples', type=int, default=5)
    parser.add_argument('--no-generated', action='store_true')
    parser.add_argument('--token', help='Token JWT explícito')
    parser.add_argument('--base-url', default='http://localhost:8080')
    parser.add_argument('--skip-pii-check', action='store_true', help='Pular verificação de PII')
    parser.add_argument('--security-context', help='JSON com contexto de segurança')
    args, _ = parser.parse_known_args()

    security_context = {{}}
    if args.security_context:
        try:
            security_context = json.loads(args.security_context)
        except:
            pass

    risk_level = security_context.get('risk_level', 'unknown')
    vulnerabilities = security_context.get('vulnerabilities', [])
    pii_fields = security_context.get('pii_fields', [])
    is_critical = risk_level == 'alto' or 'critical' in str(vulnerabilities).lower()

    log_test(f"▶️ Iniciando testes para {{args.method}} {{args.endpoint}}")
    log_test(f"   🔒 Contexto: Risco={{risk_level}}, Vulns={{vulnerabilities}}, PII={{pii_fields}}")

    spec = load_openapi_spec()
    matched_path, operation = find_operation(spec, args.endpoint, args.method)
    
    request_schema = None
    if operation:
        req_body = operation.get("requestBody", {{}})
        content = req_body.get("content", {{}})
        for ctype, cinfo in content.items():
            if "schema" in cinfo:
                request_schema = cinfo["schema"]
                break

    def extract_response_schemas(op):
        responses = op.get("responses", {{}})
        schemas = {{}}
        for status_code, resp in responses.items():
            content = resp.get("content", {{}})
            for ctype, cinfo in content.items():
                if "schema" in cinfo:
                    schemas[status_code] = cinfo["schema"]
        return schemas

    HEADERS = {{"Content-Type": "application/json"}}
    if args.token:
        HEADERS["Authorization"] = f"Bearer {{args.token}}"

    failed = 0
    passed = 0

    # Teste específico para vulnerabilidades
    if vulnerabilities and operation:
        for vuln in vulnerabilities:
            if vuln in ['bola', 'bfla']:
                def _test_authorization():
                    log_test(f"🧪 test_authorization_{{vuln}}: Verificando controle de acesso")
                    data = generate_data_from_schema(request_schema) if request_schema else None
                    response = make_request(args.method, args.endpoint, HEADERS, data=data, base_url=args.base_url)
                    if response.status_code == 200:
                        log_test(f"⚠️ Possível falha de autorização ({{vuln}}): acesso concedido", "WARNING")
                run_test(f"test_authorization_{{vuln}}", _test_authorization, critical=True)

    # Teste com dados específicos
    if args.test_data and os.path.exists(args.test_data):
        with open(args.test_data, 'r') as f:
            specific_data = json.load(f)
        specific_data.pop('_path_params', None)
        def _test_specific_data():
            log_test(f"🧪 test_specific_data")
            response = make_request(args.method, args.endpoint, HEADERS, data=specific_data, base_url=args.base_url)
            assert response.status_code < 500, f"Status {{response.status_code}}"
        if run_test("test_specific_data", _test_specific_data, is_critical):
            passed += 1
        else:
            failed += 1

    # Teste de vazamento de PII
    if pii_fields and not args.skip_pii_check:
        def _test_pii_leakage():
            log_test(f"🧪 test_pii_leakage: Verificando vazamento de {{', '.join(pii_fields)}}")
            response = make_request(args.method, args.endpoint, HEADERS, base_url=args.base_url)
            if response.status_code < 500 and response.content:
                response_text = response.text
                if not check_pii_leakage(response_text, pii_fields):
                    raise AssertionError(f"Possível vazamento de PII detectado! Campos sensíveis: {{pii_fields}}")
        if run_test("test_pii_leakage", _test_pii_leakage, is_critical):
            passed += 1
        else:
            failed += 1

    # Teste básico
    if not args.no_generated:
        def _test_basic():
            log_test(f"🧪 test_basic")
            data = generate_data_from_schema(request_schema, avoid_pii=True) if request_schema else None
            response = make_request(args.method, args.endpoint, HEADERS, data=data, base_url=args.base_url)
            assert response.status_code < 500, f"Status {{response.status_code}}"
        if run_test("test_basic", _test_basic, is_critical):
            passed += 1
        else:
            failed += 1

    # Teste sem body (GET/DELETE)
    if args.method and args.method.upper() in ["GET", "DELETE"]:
        def _test_endpoint_without_body():
            log_test(f"🧪 test_endpoint_without_body")
            response = make_request(args.method, args.endpoint, HEADERS, base_url=args.base_url)
            assert response.status_code < 500, f"Status {{response.status_code}}"
        if run_test("test_endpoint_without_body", _test_endpoint_without_body, is_critical):
            passed += 1
        else:
            failed += 1

    # Teste sem dados gerados explicitamente
    if args.no_generated:
        def _test_no_generated():
            log_test(f"🧪 test_no_generated")
            response = make_request(args.method, args.endpoint, HEADERS, base_url=args.base_url)
            assert response.status_code < 500, f"Status {{response.status_code}}"
        if run_test("test_no_generated", _test_no_generated, is_critical):
            passed += 1
        else:
            failed += 1

    # Teste com múltiplos exemplos
    if request_schema and not args.no_generated and args.max_examples > 1:
        def _test_multiple_examples():
            log_test(f"🧪 test_multiple_examples: {{args.max_examples}} exemplos para {{args.method}} {{args.endpoint}}")
            for _ in range(args.max_examples):
                data = generate_data_from_schema(request_schema, avoid_pii=True)
                response = make_request(args.method, args.endpoint, HEADERS, data=data, base_url=args.base_url)
                assert response.status_code < 500, f"Status {{response.status_code}}"
        if run_test("test_multiple_examples", _test_multiple_examples, is_critical):
            passed += 1
        else:
            failed += 1

    # Teste property-based (Hypothesis)
    if request_schema and not args.no_generated and args.max_examples > 0:
        try:
            @settings(max_examples=args.max_examples, suppress_health_check=[HealthCheck.too_slow])
            @given(data=st.builds(lambda: generate_data_from_schema(request_schema, avoid_pii=True)))
            def _hyp_test(data):
                response = make_request(args.method, args.endpoint, HEADERS, data=data, base_url=args.base_url)
                assert response.status_code < 500, f"Status {{response.status_code}}"
            _hyp_test()
            passed += 1
            log_test(f"✅ test_property_based concluído com {{args.max_examples}} exemplos")
        except Exception as e:
            log_test(f"❌ test_property_based falhou: {{e}}", "ERROR")
            failed += 1

    # Teste de schema de resposta
    if operation:
        response_schemas = extract_response_schemas(operation)
        if response_schemas:
            def _test_response_schema():
                log_test(f"🧪 test_response_schema")
                data = generate_data_from_schema(request_schema) if request_schema else None
                response = make_request(args.method, args.endpoint, HEADERS, data=data, base_url=args.base_url)
                if not response.content or not response.content.strip():
                    log_test(f"✅ test_response_schema ignorado (body vazio)")
                    return
                try:
                    body = response.json()
                except Exception:
                    log_test(f"✅ test_response_schema ignorado (body não é JSON)")
                    return
                status_str = str(response.status_code)
                schema = response_schemas.get(status_str) or response_schemas.get('200')
                if schema:
                    full_spec = load_openapi_spec()
                    def expand_nullable(s):
                        if isinstance(s, dict):
                            if s.get("nullable") and "type" in s:
                                t = s["type"]
                                s = dict(s)
                                s["type"] = [t, "null"] if isinstance(t, str) else t + ["null"]
                            return {{k: expand_nullable(v) for k, v in s.items()}}
                        if isinstance(s, list):
                            return [expand_nullable(i) for i in s]
                        return s
                    schema = expand_nullable(schema)
                    import warnings
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", DeprecationWarning)
                        resolver = jsonschema.RefResolver.from_schema(full_spec)
                        jsonschema.validate(body, schema, resolver=resolver)
            if run_test("test_response_schema", _test_response_schema, is_critical):
                passed += 1
            else:
                failed += 1

    log_test(f"📊 Resultados para {{args.method}} {{args.endpoint}}: {{passed}} passaram, {{failed}} falharam")
    sys.exit(1 if failed > 0 else 0)

if __name__ == "__main__":
    main()
'''
        return template_header.strip()
    
    def generate_runner(self) -> str:
        """Gera runner Bash com filtros de segurança avançados"""
        api_base = self.api_base
        
        runner_template = f'''#!/bin/bash

# ============================================================
# step7_run_llm_tests.sh (OTIMIZADO)
# ============================================================
# Configurações de segurança
ONLY_HIGH_RISK="${{ONLY_HIGH_RISK:-false}}"           # Testar apenas endpoints de alto risco
SKIP_NO_AUTH="${{SKIP_NO_AUTH:-false}}"               # Pular endpoints sem autenticação
MAX_RISK_SCORE="${{MAX_RISK_SCORE:-1.0}}"             # Score máximo (0.0-1.0)
TEST_BY_VULN="${{TEST_BY_VULN:-false}}"               # Testar especificamente por vulnerabilidade
VERBOSE="${{VERBOSE:-false}}"                         # Log detalhado
PARALLEL_JOBS="${{PARALLEL_JOBS:-4}}"                 # Jobs paralelos

# Configurações padrão
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENRICHED_ENDPOINTS_JSON="$SCRIPT_DIR/tests/enriched_endpoints.json"
TEST_SCRIPT="$SCRIPT_DIR/tests/test_api_security.py"
LOGFILE="$(cd "$SCRIPT_DIR/../../.." && pwd)/test_api_llm.log"
SUMMARY_FILE="output/test_api_llm_summary.md"
BASE_URL="${{API_BASE_URL:-{api_base}}}"
MAX_PARALLEL="$PARALLEL_JOBS"

export PYTHONPATH="$(cd "$SCRIPT_DIR/../../.." && pwd)"
export USE_LLM_DATA=true
export TEST_LOG_FILE="$LOGFILE"
export TEST_SUMMARY_FILE="$SUMMARY_FILE"

# Cores para output
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'
NC='\\033[0m'

echo "============================================================"
echo "🔒 TESTES DE SEGURANÇA DE API - MODO OTIMIZADO"
echo "============================================================"
echo "📋 Configurações:"
echo "   - Apenas alto risco: $ONLY_HIGH_RISK"
echo "   - Pular sem autenticação: $SKIP_NO_AUTH"
echo "   - Score máximo: $MAX_RISK_SCORE"
echo "   - Testar por vulnerabilidade: $TEST_BY_VULN"
echo "   - Jobs paralelos: $MAX_PARALLEL"
echo "   - Base URL: $BASE_URL"
echo "============================================================"

# Remove arquivos anteriores
if [ -f "$LOGFILE" ]; then rm "$LOGFILE"; fi
if [ -f "$SUMMARY_FILE" ]; then rm "$SUMMARY_FILE"; fi

# Cabeçalho do log e summary
echo "Execução iniciada em: $(date '+%Y-%m-%d %H:%M:%S')" > "$LOGFILE"
echo "# Relatório de Testes de Segurança da API" > "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"
echo "**Data da execução:** $(date '+%Y-%m-%d %H:%M:%S')" >> "$SUMMARY_FILE"
echo "**Modo:** $([ "$ONLY_HIGH_RISK" = "true" ] && echo "Apenas alto risco" || echo "Completo")" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"
echo "## Resultados por Endpoint" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"
echo "| Endpoint | Método | Risco | Vulnerabilidades | Status |" >> "$SUMMARY_FILE"
echo "|----------|--------|-------|------------------|--------|" >> "$SUMMARY_FILE"

if [ ! -f "$ENRICHED_ENDPOINTS_JSON" ]; then
    echo -e "$RED❌ Arquivo enriched_endpoints.json não encontrado em $ENRICHED_ENDPOINTS_JSON$NC"
    exit 1
fi

# Constrói filtro JSON
FILTER="."
if [ "$ONLY_HIGH_RISK" = "true" ]; then
    FILTER='select(.risk_level == "alto")'
elif [ "$MAX_RISK_SCORE" != "1.0" ]; then
    FILTER="select(.risk_score <= $MAX_RISK_SCORE)"
fi

ENDPOINT_COUNT=$(jq -c ".[] | $FILTER" "$ENRICHED_ENDPOINTS_JSON" | wc -l)
echo -e "$BLUE📊 $ENDPOINT_COUNT endpoints serão testados$NC"

# Função para obter token via variável de ambiente
get_token() {{
    local role="$1"
    local env_var="TOKEN_${{role^^}}"
    local token="${{!env_var}}"
    echo "$token"
}}

normalize_endpoint_for_filename() {{
    local endpoint="$1"
    echo "$endpoint" | sed -E 's|:[^/]+|X|g; s|\{{[^}}]+\}}|X|g; s|^/||; s|/|_|g'
}}

resolve_test_data_file() {{
    local method="$1"
    local endpoint="$2"
    local candidate_file=""

    local base_name
    base_name="$(normalize_endpoint_for_filename "$endpoint")"
    candidate_file="$SCRIPT_DIR/tests/dados/${{method}}_${{base_name}}.json"
    if [ -f "$candidate_file" ]; then
        echo "$candidate_file"
        return
    fi

    if [[ "$endpoint" =~ ^/api/ ]] && [[ ! "$endpoint" =~ ^/api/v1/ ]]; then
        local endpoint_v1
        endpoint_v1="${{endpoint/#\/api\//\/api\/v1\/}}"
        base_name="$(normalize_endpoint_for_filename "$endpoint_v1")"
        candidate_file="$SCRIPT_DIR/tests/dados/${{method}}_${{base_name}}.json"
        if [ -f "$candidate_file" ]; then
            echo "$candidate_file"
            return
        fi
    fi

    echo ""
}}

# Função para executar teste de um endpoint/role
run_test() {{
    local method="$1"
    local endpoint="$2"
    local role="$3"
    local risk_level="$4"
    local vulnerabilities="$5"
    local pii_fields="$6"
    local test_data_file="$7"
    
    local security_context=$(jq -n \
        --arg risk "$risk_level" \
        --argjson vulns "$(echo "$vulnerabilities" | jq -R 'split(",")')" \
        --argjson pii "$(echo "$pii_fields" | jq -R 'split(",")')" \
        '{{risk_level: $risk, vulnerabilities: $vulns, pii_fields: $pii}}')
    
    echo "[INFO] Iniciando teste: $method $endpoint (role: $role, risco: $risk_level)" >> "$LOGFILE"
    
    local token="$(get_token "$role")"
    local args=(--method "$method" --endpoint "$endpoint" --base-url "$BASE_URL")
    [ -n "$token" ] && args+=(--token "$token")
    [ -n "$test_data_file" ] && [ -f "$test_data_file" ] && args+=(--test-data "$test_data_file")
    args+=(--security-context "$security_context")
    
    local TIMEOUT=120
    timeout $TIMEOUT python3 "$TEST_SCRIPT" "${{args[@]}}" >> "$LOGFILE" 2>&1
    local exit_code=$?
    
    local vuln_display=$(echo "$vulnerabilities" | sed 's/,/, /g')
    if [ -z "$vuln_display" ] || [ "$vuln_display" = "null" ]; then
        vuln_display="-"
    fi
    
    if [ $exit_code -eq 0 ]; then
        echo -e "$GREEN✅ $method $endpoint (role: $role)$NC"
        echo "| $endpoint | $method | $risk_level | $vuln_display | ✅ Sucesso |" >> "$SUMMARY_FILE"
    elif [ $exit_code -eq 124 ]; then
        echo -e "$RED❌ $method $endpoint (role: $role) [TIMEOUT]${{NC}}"
        echo "| $endpoint | $method | $risk_level | $vuln_display | ⏱️ Timeout |" >> "$SUMMARY_FILE"
    else
        echo -e "$RED❌ $method $endpoint (role: $role) [exit $exit_code]${{NC}}"
        echo "| $endpoint | $method | $risk_level | $vuln_display | ❌ Falha (exit $exit_code) |" >> "$SUMMARY_FILE"
    fi
    return $exit_code
}}

# Processa endpoints
COUNT=0
FAIL=0
SUCCESS=0
PIDS=()

while IFS= read -r row; do
    method=$(echo "$row" | jq -r '.method')
    endpoint=$(echo "$row" | jq -r '.path')
    auth_required=$(echo "$row" | jq -r '.auth_required // true')
    risk_level=$(echo "$row" | jq -r '.risk_level // "baixo"')
    risk_score=$(echo "$row" | jq -r '.risk_score // 0.1')
    vulnerabilities=$(echo "$row" | jq -r '.vulnerabilities | join(",")')
    pii_fields=$(echo "$row" | jq -r '.pii_fields | join(",")')
    roles=$(echo "$row" | jq -r '.roles // empty | @sh')
    
    # Pula endpoints sem autenticação se configurado
    if [ "$SKIP_NO_AUTH" = "true" ] && [ "$auth_required" = "false" ]; then
        echo -e "$YELLOW⏭️ Pulando $method $endpoint (sem autenticação)$NC"
        continue
    fi
    
    # Filtro adicional por score de risco
    if [ "$MAX_RISK_SCORE" != "1.0" ]; then
        if (( $(echo "$risk_score > $MAX_RISK_SCORE" | bc -l) )); then
            echo -e "$YELLOW⏭️ Pulando $method $endpoint (risco $risk_score > $MAX_RISK_SCORE)$NC"
            continue
        fi
    fi
    
    test_data_file="$(resolve_test_data_file "$method" "$endpoint")"
    
    # Log de segurança
    echo -e "$BLUE🔒 $method $endpoint - Risco: $risk_level ($risk_score) | Vulns: ${{vulnerabilities:-nenhuma}} | PII: ${{pii_fields:-nenhuma}}$NC"
    
    if [ -n "$roles" ]; then
        roles_eval=$(eval echo "$roles")
        for role in $roles_eval; do
            run_test "$method" "$endpoint" "$role" "$risk_level" "$vulnerabilities" "$pii_fields" "$test_data_file" &
            PIDS+=($!)
            ((COUNT++))
            while [ "$(jobs -rp | wc -l)" -ge "$MAX_PARALLEL" ]; do sleep 0.2; done
        done
    else
        run_test "$method" "$endpoint" "" "$risk_level" "$vulnerabilities" "$pii_fields" "$test_data_file" &
        PIDS+=($!)
        ((COUNT++))
        while [ "$(jobs -rp | wc -l)" -ge "$MAX_PARALLEL" ]; do sleep 0.2; done
    fi
done < <(jq -c ".[] | $FILTER" "$ENRICHED_ENDPOINTS_JSON")

# Aguarda todos os processos
for pid in "${{PIDS[@]}}"; do
    if wait "$pid"; then
        ((SUCCESS++))
    else
        ((FAIL++))
    fi
done

# Resumo final
echo "" >> "$SUMMARY_FILE"
echo "## Resumo de Segurança" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"
echo "- **Total de testes:** $COUNT" >> "$SUMMARY_FILE"
echo "- **✅ Sucessos:** $SUCCESS" >> "$SUMMARY_FILE"
echo "- **❌ Falhas:** $FAIL" >> "$SUMMARY_FILE"
echo "- **Modo de risco:** $([ "$ONLY_HIGH_RISK" = "true" ] && echo "Apenas alto risco" || echo "Completo")" >> "$SUMMARY_FILE"

echo ""
echo "============================================================"
echo -e "$BLUE📊 RESUMO FINAL$NC"
echo "============================================================"
echo -e "Total de testes executados: $COUNT"
echo -e "$GREEN✅ Sucessos: $SUCCESS$NC"
echo -e "$RED❌ Falhas: $FAIL$NC"
echo "============================================================"
echo -e "📋 Log completo: $LOGFILE"
echo -e "📊 Relatório: $SUMMARY_FILE"
echo "============================================================"

# Exit code
if [ $FAIL -gt 0 ]; then
    exit 1
fi
exit 0
'''
        return runner_template.strip()

    def _write_file_safely(self, file_path: Path, content: str, description: str) -> bool:
        """Escreve arquivo com verificação pós-escrita"""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding='utf-8')
            if file_path.exists() and file_path.stat().st_size > 0:
                print(f"✅ {description}: {file_path}")
                return True
            else:
                print(f"❌ Falha ao escrever {description}")
                return False
        except Exception as e:
            print(f"❌ Erro ao escrever {description}: {e}")
            return False

    def generate(self):
        """Gera a estrutura de arquivos otimizada"""
        print(f"\n🔧 Iniciando geração de artefatos otimizados...")
        
        tests_dir = Path("src/application/pipeline/tests")
        hooks_dir = Path("src/infrastructure/interfaces/hooks")
        pipeline_dir = Path("src/application/pipeline")
        
        for d in [tests_dir, hooks_dir, pipeline_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        success_count = 0
        total_files = 5
        
        # 1. __init__.py dos hooks
        init_content = "from .llm_hooks import before_call\nfrom .auth_hooks import apply_auth\n"
        if self._write_file_safely(hooks_dir / "__init__.py", init_content, "Hooks __init__.py"):
            success_count += 1
        
        # 2. auth_hooks.py
        auth_content = self.generate_auth_hooks()
        if self._write_file_safely(hooks_dir / "auth_hooks.py", auth_content, "auth_hooks.py"):
            success_count += 1
        
        # 3. llm_hooks.py
        llm_content = self.generate_llm_hooks()
        if self._write_file_safely(hooks_dir / "llm_hooks.py", llm_content, "llm_hooks.py"):
            success_count += 1
        
        # 4. test_api_security.py
        test_content = self.generate_smart_test_file()
        if self._write_file_safely(tests_dir / "test_api_security.py", test_content, "test_api_security.py"):
            success_count += 1
        
        # 5. step7_run_llm_tests.sh
        runner_content = self.generate_runner()
        runner_path = pipeline_dir / "step7_run_llm_tests.sh"
        if self._write_file_safely(runner_path, runner_content, "step7_run_llm_tests.sh"):
            success_count += 1
            # Torna executável
            runner_path.chmod(0o755)
        
        print(f"\n✅ Geração concluída: {success_count}/{total_files} arquivos criados.")
        print("\n📌 Para executar os testes:")
        print("   # Testar apenas endpoints de alto risco")
        print("   ONLY_HIGH_RISK=true ./src/application/pipeline/step7_run_llm_tests.sh")
        print("")
        print("   # Testar com score máximo 0.7")
        print("   MAX_RISK_SCORE=0.7 ./src/application/pipeline/step7_run_llm_tests.sh")
        print("")
        print("   # Teste completo")
        print("   ./src/application/pipeline/step7_run_llm_tests.sh")
        
        return success_count == total_files


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 step6_generator.py <openapi.json>")
        print("\nVariáveis de ambiente opcionais:")
        print("  API_BASE_URL     - URL base da API (padrão: http://localhost)")
        print("  ONLY_HIGH_RISK   - Testar apenas endpoints de alto risco")
        print("  MAX_RISK_SCORE   - Score máximo de risco (0.0-1.0)")
        sys.exit(1)

    openapi_file = sys.argv[1]
    generator = SmartSchemathesisGenerator(openapi_file)
    success = generator.generate()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()