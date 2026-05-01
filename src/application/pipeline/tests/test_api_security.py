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
            f.write(f"[{status}] {message}\n")
    except Exception:
        pass

SPEC_FILE = r"/home/s231991563/projetos/neosigner/controlador-api/src/swagger/specs/openapi.json"

def load_openapi_spec():
    with open(SPEC_FILE, 'r') as f:
        if SPEC_FILE.endswith('.yaml') or SPEC_FILE.endswith('.yml'):
            return yaml.safe_load(f)
        return json.load(f)

def normalize_endpoint_path(endpoint):
    if not endpoint:
        return endpoint
    normalized = endpoint.strip()
    normalized = re.sub(r':([^/]+)', r'{\1}', normalized)
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

    paths = spec.get('paths', {})
    method_lower = method.lower()

    for candidate in build_openapi_path_candidates(endpoint):
        op = paths.get(candidate, {})
        if method_lower in op:
            return candidate, op.get(method_lower)

    return None, None

def make_request(method, endpoint, headers, data=None, base_url="http://localhost", timeout=10, verify_ssl=False):
    url = f"{base_url.rstrip('/')}{endpoint}"
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
        props = schema.get("properties", {})
        required = schema.get("required", [])
        result = {}
        for k, v in props.items():
            if avoid_pii and any(p in k.lower() for p in pii_patterns):
                continue
            if k in required or random.random() > 0.3:
                result[k] = generate_data_from_schema(v, depth+1, avoid_pii)
        return result
    if schema_type == "array":
        items = schema.get("items", {})
        return [generate_data_from_schema(items, depth+1, avoid_pii)]
    if schema_type == "string":
        format_pattern = schema.get("format")
        if format_pattern == "email":
            return f"test{random.randint(1,999)}@example.com"
        if format_pattern == "uuid":
            return f"550e8400-e29b-41d4-a716-{random.randint(100000000000, 999999999999)}"
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
    pii_patterns = {
        'cpf': r'\d{3}\.\d{3}\.\d{3}-\d{2}|\d{11}',
        'cnpj': r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{14}',
        'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        'telefone': r'\(?\d{2}\)?\s?\d{4,5}-?\d{4}',
        'rg': r'\d{2}\.\d{3}\.\d{3}-\d{1}|\d{9}'
    }
    for pii_type in endpoint_pii:
        if pii_type in pii_patterns and re.search(pii_patterns[pii_type], response_text):
            return False
    return True

def run_test(name, fn, critical=False):
    try:
        fn()
        if critical:
            log_test(f"✅ {name} (CRÍTICO) passou", "SUCCESS")
        else:
            log_test(f"✅ {name} passou", "SUCCESS")
        return True
    except AssertionError as e:
        severity = "CRITICAL" if critical else "ERROR"
        log_test(f"❌ {name} falhou: {e}", severity)
        return False
    except Exception as e:
        severity = "CRITICAL" if critical else "ERROR"
        log_test(f"❌ {name} erro inesperado: {e}", severity)
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

    security_context = {}
    if args.security_context:
        try:
            security_context = json.loads(args.security_context)
        except:
            pass

    risk_level = security_context.get('risk_level', 'unknown')
    vulnerabilities = security_context.get('vulnerabilities', [])
    pii_fields = security_context.get('pii_fields', [])
    is_critical = risk_level == 'alto' or 'critical' in str(vulnerabilities).lower()

    log_test(f"▶️ Iniciando testes para {args.method} {args.endpoint}")
    log_test(f"   🔒 Contexto: Risco={risk_level}, Vulns={vulnerabilities}, PII={pii_fields}")

    spec = load_openapi_spec()
    matched_path, operation = find_operation(spec, args.endpoint, args.method)
    
    request_schema = None
    if operation:
        req_body = operation.get("requestBody", {})
        content = req_body.get("content", {})
        for ctype, cinfo in content.items():
            if "schema" in cinfo:
                request_schema = cinfo["schema"]
                break

    def extract_response_schemas(op):
        responses = op.get("responses", {})
        schemas = {}
        for status_code, resp in responses.items():
            content = resp.get("content", {})
            for ctype, cinfo in content.items():
                if "schema" in cinfo:
                    schemas[status_code] = cinfo["schema"]
        return schemas

    HEADERS = {"Content-Type": "application/json"}
    if args.token:
        HEADERS["Authorization"] = f"Bearer {args.token}"

    failed = 0
    passed = 0

    # Teste específico para vulnerabilidades
    if vulnerabilities and operation:
        for vuln in vulnerabilities:
            if vuln in ['bola', 'bfla']:
                def _test_authorization():
                    log_test(f"🧪 test_authorization_{vuln}: Verificando controle de acesso")
                    data = generate_data_from_schema(request_schema) if request_schema else None
                    response = make_request(args.method, args.endpoint, HEADERS, data=data, base_url=args.base_url)
                    if response.status_code == 200:
                        log_test(f"⚠️ Possível falha de autorização ({vuln}): acesso concedido", "WARNING")
                run_test(f"test_authorization_{vuln}", _test_authorization, critical=True)

    # Teste com dados específicos
    if args.test_data and os.path.exists(args.test_data):
        with open(args.test_data, 'r') as f:
            specific_data = json.load(f)
        specific_data.pop('_path_params', None)
        def _test_specific_data():
            log_test(f"🧪 test_specific_data")
            response = make_request(args.method, args.endpoint, HEADERS, data=specific_data, base_url=args.base_url)
            assert response.status_code < 500, f"Status {response.status_code}"
        if run_test("test_specific_data", _test_specific_data, is_critical):
            passed += 1
        else:
            failed += 1

    # Teste de vazamento de PII
    if pii_fields and not args.skip_pii_check:
        def _test_pii_leakage():
            log_test(f"🧪 test_pii_leakage: Verificando vazamento de {', '.join(pii_fields)}")
            response = make_request(args.method, args.endpoint, HEADERS, base_url=args.base_url)
            if response.status_code < 500 and response.content:
                response_text = response.text
                if not check_pii_leakage(response_text, pii_fields):
                    raise AssertionError(f"Possível vazamento de PII detectado! Campos sensíveis: {pii_fields}")
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
            assert response.status_code < 500, f"Status {response.status_code}"
        if run_test("test_basic", _test_basic, is_critical):
            passed += 1
        else:
            failed += 1

    # Teste sem body (GET/DELETE)
    if args.method and args.method.upper() in ["GET", "DELETE"]:
        def _test_endpoint_without_body():
            log_test(f"🧪 test_endpoint_without_body")
            response = make_request(args.method, args.endpoint, HEADERS, base_url=args.base_url)
            assert response.status_code < 500, f"Status {response.status_code}"
        if run_test("test_endpoint_without_body", _test_endpoint_without_body, is_critical):
            passed += 1
        else:
            failed += 1

    # Teste sem dados gerados explicitamente
    if args.no_generated:
        def _test_no_generated():
            log_test(f"🧪 test_no_generated")
            response = make_request(args.method, args.endpoint, HEADERS, base_url=args.base_url)
            assert response.status_code < 500, f"Status {response.status_code}"
        if run_test("test_no_generated", _test_no_generated, is_critical):
            passed += 1
        else:
            failed += 1

    # Teste com múltiplos exemplos
    if request_schema and not args.no_generated and args.max_examples > 1:
        def _test_multiple_examples():
            log_test(f"🧪 test_multiple_examples: {args.max_examples} exemplos para {args.method} {args.endpoint}")
            for _ in range(args.max_examples):
                data = generate_data_from_schema(request_schema, avoid_pii=True)
                response = make_request(args.method, args.endpoint, HEADERS, data=data, base_url=args.base_url)
                assert response.status_code < 500, f"Status {response.status_code}"
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
                assert response.status_code < 500, f"Status {response.status_code}"
            _hyp_test()
            passed += 1
            log_test(f"✅ test_property_based concluído com {args.max_examples} exemplos")
        except Exception as e:
            log_test(f"❌ test_property_based falhou: {e}", "ERROR")
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
                            return {k: expand_nullable(v) for k, v in s.items()}
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

    log_test(f"📊 Resultados para {args.method} {args.endpoint}: {passed} passaram, {failed} falharam")
    sys.exit(1 if failed > 0 else 0)

if __name__ == "__main__":
    main()