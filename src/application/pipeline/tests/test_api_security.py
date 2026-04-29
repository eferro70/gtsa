import jsonschema
import os
import sys
import json
import argparse
import yaml
import random
import string
from pathlib import Path
from src.infrastructure.interfaces.hooks.llm_hooks import before_call
from hypothesis import given, settings, strategies as st, HealthCheck, errors as hyp_errors

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

def make_request(method, endpoint, headers, data=None, base_url="http://localhost", timeout=10):
    url = f"{base_url.rstrip('/')}{endpoint}"
    if requests is None:
        raise RuntimeError("requests não instalado")
    if method.upper() in ["GET", "DELETE"]:
        return requests.request(method, url, headers=headers, timeout=timeout)
    else:
        return requests.request(method, url, headers=headers, json=data, timeout=timeout)

def generate_data_from_schema(schema, depth=0):
    if depth > 10:
        return None
    schema_type = schema.get("type")
    if "$ref" in schema:
        return "ref-value"
    if schema_type == "object":
        props = schema.get("properties", {})
        required = schema.get("required", [])
        result = {}
        for k, v in props.items():
            if k in required or random.random() > 0.3:
                result[k] = generate_data_from_schema(v, depth+1)
        return result
    if schema_type == "array":
        items = schema.get("items", {})
        return [generate_data_from_schema(items, depth+1)]
    if schema_type == "string":
        return ''.join(random.choices(string.ascii_letters, k=8))
    if schema_type == "integer":
        return random.randint(0, 100)
    if schema_type == "number":
        return random.random() * 100
    if schema_type == "boolean":
        return random.choice([True, False])
    return None

def run_test(name, fn):
    """Executa uma função de teste, loga resultado e retorna True/False."""
    try:
        fn()
        return True
    except AssertionError as e:
        log_test(f"❌ {name} falhou: {e}", "ERROR")
        return False
    except Exception as e:
        log_test(f"❌ {name} erro inesperado: {e}", "ERROR")
        return False

def main():
    parser = argparse.ArgumentParser(description='Testes avançados de API')
    parser.add_argument('--method', help='Método HTTP (ex: POST, GET)')
    parser.add_argument('--endpoint', help='Endpoint (ex: /api/v1/fluxos/adicionar)')
    parser.add_argument('--test-data', help='Arquivo JSON com dados de teste específicos')
    parser.add_argument('--max-examples', type=int, default=5, help='Número máximo de exemplos gerados')
    parser.add_argument('--no-generated', action='store_true', help='Não gerar dados automaticamente')
    parser.add_argument('--token', help='Token JWT explícito')
    parser.add_argument('--base-url', default='http://localhost:8080', help='URL base da API')
    args, _ = parser.parse_known_args()

    log_test(f"▶️ Iniciando testes para {args.method} {args.endpoint}")

    spec = load_openapi_spec()
    operation = None
    if args.endpoint and args.method:
        paths = spec.get("paths", {})
        op = paths.get(args.endpoint, {})
        operation = op.get(args.method.lower())
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

    # --- test_specific_data ---
    if args.test_data and os.path.exists(args.test_data):
        with open(args.test_data, 'r') as f:
            specific_data = json.load(f)
        specific_data.pop('_path_params', None)
        def _test_specific_data():
            log_test(f"🧪 test_specific_data para {args.method} {args.endpoint}")
            response = make_request(args.method, args.endpoint, HEADERS, data=specific_data, base_url=args.base_url)
            assert response.status_code < 500, f"Status {response.status_code}"
            log_test(f"✅ test_specific_data concluído com status {response.status_code}")
        if run_test("test_specific_data", _test_specific_data): passed += 1
        else: failed += 1

    # --- test_basic ---
    if not args.no_generated:
        def _test_basic():
            log_test(f"🧪 test_basic para {args.method} {args.endpoint}")
            data = generate_data_from_schema(request_schema) if request_schema else None
            response = make_request(args.method, args.endpoint, HEADERS, data=data, base_url=args.base_url)
            assert response.status_code < 500, f"Status {response.status_code}"
            log_test(f"✅ test_basic concluído com status {response.status_code}")
        if run_test("test_basic", _test_basic): passed += 1
        else: failed += 1

    # --- test_property_based (Hypothesis) ---
    if request_schema and not args.no_generated:
        log_test(f"🧪 test_property_based para {args.method} {args.endpoint}")
        try:
            results = []
            @settings(max_examples=args.max_examples, suppress_health_check=[HealthCheck.too_slow])
            @given(data=st.builds(lambda: generate_data_from_schema(request_schema)))
            def _hyp_test(data):
                response = make_request(args.method, args.endpoint, HEADERS, data=data, base_url=args.base_url)
                assert response.status_code < 500, f"Status {response.status_code}"
            _hyp_test()
            log_test(f"✅ test_property_based concluído")
            passed += 1
        except Exception as e:
            log_test(f"❌ test_property_based falhou: {e}", "ERROR")
            failed += 1

    # --- test_endpoint_without_body ---
    if not request_schema:
        def _test_without_body():
            log_test(f"🧪 test_endpoint_without_body para {args.method} {args.endpoint}")
            response = make_request(args.method, args.endpoint, HEADERS, base_url=args.base_url)
            assert response.status_code < 500, f"Status {response.status_code}"
            log_test(f"✅ test_endpoint_without_body concluído com status {response.status_code}")
        if run_test("test_endpoint_without_body", _test_without_body): passed += 1
        else: failed += 1

    # --- test_response_schema ---
    if operation:
        response_schemas = extract_response_schemas(operation)
        if response_schemas:
            def _test_response_schema():
                log_test(f"🧪 test_response_schema para {args.method} {args.endpoint}")
                data = generate_data_from_schema(request_schema) if request_schema else None
                response = make_request(args.method, args.endpoint, HEADERS, data=data, base_url=args.base_url)
                if not response.content or not response.content.strip():
                    log_test(f"✅ test_response_schema ignorado (body vazio, status {response.status_code})")
                    return
                try:
                    body = response.json()
                except Exception:
                    log_test(f"✅ test_response_schema ignorado (body não é JSON, status {response.status_code})")
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
                log_test(f"✅ test_response_schema concluído com status {response.status_code}")
            if run_test("test_response_schema", _test_response_schema): passed += 1
            else: failed += 1

    # --- test_multiple_examples ---
    if args.max_examples > 1 and not args.no_generated:
        def _test_multiple():
            log_test(f"🧪 test_multiple_examples: {args.max_examples} exemplos para {args.method} {args.endpoint}")
            for i in range(args.max_examples):
                data = generate_data_from_schema(request_schema) if request_schema else None
                response = make_request(args.method, args.endpoint, HEADERS, data=data, base_url=args.base_url)
                assert response.status_code < 500, f"Exemplo {i+1}: status {response.status_code}"
                log_test(f"  ✅ Exemplo {i+1}/{args.max_examples} com status {response.status_code}")
        if run_test("test_multiple_examples", _test_multiple): passed += 1
        else: failed += 1

    # --- test_no_generated ---
    if args.no_generated and not args.test_data:
        def _test_no_generated():
            log_test(f"🧪 test_no_generated para {args.method} {args.endpoint}")
            data = {} if request_schema else None
            response = make_request(args.method, args.endpoint, HEADERS, data=data, base_url=args.base_url)
            assert response.status_code < 500, f"Status {response.status_code}"
            log_test(f"✅ test_no_generated concluído com status {response.status_code}")
        if run_test("test_no_generated", _test_no_generated): passed += 1
        else: failed += 1

    log_test(f"📊 Cobertura automática: Testando endpoint {args.method} {args.endpoint} — {passed} passed, {failed} failed")
    sys.exit(1 if failed > 0 else 0)

if __name__ == "__main__":
    main()