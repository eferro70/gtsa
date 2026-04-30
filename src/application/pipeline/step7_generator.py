#!/usr/bin/env python3
"""
step7_generator.py
------------------
Gera automaticamente arquivos de teste para APIs REST a partir de uma especificação OpenAPI e endpoints enriquecidos.

Principais funções:
- Cria arquivos de teste Python (Schemathesis/Hypothesis) para validação automática dos endpoints.
- Gera um runner Bash para execução paralela dos testes.
- Gera hooks de autenticação e configuração para integração com o pipeline.
- Os hooks são gravados em src/infrastructure/interfaces/hooks.
- Os arquivos de teste e runner são gravados em output/tests.

Uso típico: python3 step7_generator.py <openapi.json>
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
        # enriched_endpoints.json agora em src/application/pipeline/tests/
        self.enriched_file = Path("src/application/pipeline/tests/enriched_endpoints.json").resolve()
        self.openapi_file = Path(openapi_file).resolve()
        self.output_dir = Path("src/application/pipeline/tests").resolve()
        self.api_base = os.getenv("API_BASE_URL", "http://localhost")
        self.load_data()
    
    def load_data(self):
        """Carrega os dados com verificação e logging explícito"""
        print(f"🔍 Verificando arquivos de entrada...")
        
        # Verifica enriched_endpoints.json
        if not self.enriched_file.exists():
            raise FileNotFoundError(
                f"❌ Arquivo não encontrado: {self.enriched_file}\n"
                f"💡 Execute primeiro: python3 step5_analyzer.py para gerar enriched_endpoints.json"
            )
        print(f"✅ enriched_endpoints.json encontrado: {self.enriched_file}")
        
        # Verifica openapi.json
        if not self.openapi_file.exists():
            raise FileNotFoundError(f"❌ Arquivo não encontrado: {self.openapi_file}")
        print(f"✅ OpenAPI spec encontrado: {self.openapi_file}")
        
        # Carrega enriched_endpoints.json
        try:
            with open(self.enriched_file, 'r', encoding='utf-8') as f:
                self.endpoints = json.load(f)
            print(f"✅ {len(self.endpoints)} endpoints carregados de enriched_endpoints.json")
        except json.JSONDecodeError as e:
            raise ValueError(f"❌ Erro ao parsear enriched_endpoints.json: {e}")
        except Exception as e:
            raise RuntimeError(f"❌ Erro ao ler enriched_endpoints.json: {e}")
        
        # Carrega openapi.json
        try:
            with open(self.openapi_file, 'r', encoding='utf-8') as f:
                self.openapi_schema = json.load(f)
            print(f"✅ OpenAPI schema carregado: {self.openapi_schema.get('info', {}).get('title', 'Sem título')}")
        except json.JSONDecodeError as e:
            raise ValueError(f"❌ Erro ao parsear OpenAPI: {e}")
        except Exception as e:
            raise RuntimeError(f"❌ Erro ao ler OpenAPI: {e}")
        
        print(f"✅ Dados carregados. Gerando artefatos para: {self.output_dir}")

    def generate_auth_hooks(self) -> str:
        api_base = os.getenv("API_BASE_URL", "http://localhost:8080")
        return textwrap.dedent("""
            import os
            import json
            from dotenv import load_dotenv
            from pathlib import Path

            # Busca auth_config.json subindo diretórios a partir do cwd e também em config/
            def find_config(filename):
                path = Path.cwd()
                for _ in range(6):  # Sobe até 6 níveis
                    # Procura no diretório atual
                    candidate = path / filename
                    if candidate.exists():
                        return candidate
                    # Procura em config/ no diretório atual
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

            # Busca .env subindo diretórios a partir do cwd
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
                    print(f"[!] Variável de ambiente '{{var}}' não encontrada no .env")
                return val

            def apply_auth(case):
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

                # Token de role (opcional)
                role_tokens = AUTH_CONFIG.get("role_tokens", {})
                default_role = AUTH_CONFIG.get("default_role")
                if default_role and default_role in role_tokens:
                    token_env = role_tokens[default_role].get("env_var")
                    token_value = role_tokens[default_role].get("value")
                    token = get_env_value(token_env) if token_env else token_value
                    if token:
                        auth_header = AUTH_CONFIG.get("auth_header", "Authorization")
                        prefix = AUTH_CONFIG.get("auth_prefix", "Bearer ")
                        case.headers[auth_header] = f"{prefix}{token.strip()}"
        """).strip()

    def generate_llm_hooks(self) -> str:
        return textwrap.dedent("""
            import schemathesis
            from .auth_hooks import apply_auth

            @schemathesis.hook
            def before_call(context, case, **kwargs):
                if case.headers is None:
                    case.headers = {}
                
                # Força o Content-Type para evitar erros 422/415
                case.headers["Content-Type"] = "application/json"
                case.headers["Accept"] = "application/json"
                
                # Aplica autenticação e chave de sistema
                apply_auth(case)
        """).strip()

    def generate_smart_test_file(self) -> str:
        swagger_path = str(self.openapi_file)
        template = textwrap.dedent("""
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
                    f.write(f"[{status}] {message}\\n")
            except Exception:
                pass

        SPEC_FILE = r"__SWAGGER_PATH__"

        def load_openapi_spec():
            with open(SPEC_FILE, 'r') as f:
                if SPEC_FILE.endswith('.yaml') or SPEC_FILE.endswith('.yml'):
                    return yaml.safe_load(f)
                return json.load(f)

        def make_request(method, endpoint, headers, data=None, base_url="{api_base}", timeout=10):
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
            \"\"\"Executa uma função de teste, loga resultado e retorna True/False.\"\"\"
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
        """).strip()

        return template.replace("__SWAGGER_PATH__", swagger_path).replace("{api_base}", self.api_base)
    
    def generate_runner(self) -> str:
        return textwrap.dedent("""
#!/bin/bash

# Configurações
SCRIPT_DIR="$(cd \"$(dirname \"$0\")\" && pwd)"
ENRICHED_ENDPOINTS_JSON="$SCRIPT_DIR/tests/enriched_endpoints.json"
TEST_SCRIPT="$SCRIPT_DIR/test_api_security.py"
DATA_DIR="$SCRIPT_DIR/dados"
LOGFILE="$SCRIPT_DIR/test_api_llm.log"
SUMMARY_FILE="output/test_api_llm_summary.md"
BASE_URL="{api_base}"
MAX_PARALLEL=4

export USE_LLM_DATA=true
export TEST_LOG_FILE="$LOGFILE"
export TEST_SUMMARY_FILE="$SUMMARY_FILE"
mkdir -p "$DATA_DIR"
# Remove o arquivo de log anterior, se existir
if [ -f "$LOGFILE" ]; then
    rm "$LOGFILE"
fi
# Remove o arquivo de summary anterior, se existir
if [ -f "$SUMMARY_FILE" ]; then
    rm "$SUMMARY_FILE"
fi
# Adiciona data e hora da execução no início do log
echo "Execução iniciada em: $(date '+%Y-%m-%d %H:%M:%S')" > "$LOGFILE"
echo "# Relatório de Testes da API" > "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"
echo "**Data da execução:** $(date '+%Y-%m-%d %H:%M:%S')" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"
echo "## Resultados" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"
echo "| Endpoint | Método | Role | Status |" >> "$SUMMARY_FILE"
echo "|----------|--------|------|--------|" >> "$SUMMARY_FILE"

if [ ! -f "$ENRICHED_ENDPOINTS_JSON" ]; then
    echo "Arquivo enriched_endpoints.json não encontrado em $ENRICHED_ENDPOINTS_JSON"
    exit 1
fi

echo "🚀 Iniciando testes LLM Schemathesis"
echo "====================================="
echo "Arquivo de endpoints: $ENRICHED_ENDPOINTS_JSON"
echo "Script de teste: $TEST_SCRIPT"
echo "Base URL: $BASE_URL"
echo "Log: $LOGFILE"
echo "Summary: $SUMMARY_FILE"
echo "====================================="

# Função para obter token do .env
get_token() {
    local role="$1"
    local env_var="TOKEN_${role^^}"
    local token="${!env_var}"
    if [ -z "$token" ]; then
        echo ""
    else
        echo "$token"
    fi
}

# Função para executar teste de endpoint
run_test() {
    local method="$1"
    local endpoint="$2"
    local role="$3"
    local test_data_file="$4"
    echo "[INFO] Iniciando teste: $method $endpoint (role: $role)" >> "$LOGFILE"
    local token="$(get_token "$role")"
    local args=(--method "$method" --endpoint "$endpoint" --base-url "$BASE_URL")
    if [ -n "$token" ]; then
        args+=(--token "$token")
    fi
    if [ -n "$test_data_file" ] && [ -f "$test_data_file" ]; then
        args+=(--test-data "$test_data_file")
    fi
    local TIMEOUT=120
    timeout $TIMEOUT python3 "$TEST_SCRIPT" "${args[@]}" >> "$LOGFILE" 2>&1
    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        echo "✅ $method $endpoint (role: $role)" >> "$LOGFILE"
        echo "| $endpoint | $method | $role | ✅ Sucesso |" >> "$SUMMARY_FILE"
    elif [ $exit_code -eq 124 ]; then
        echo "❌ $method $endpoint (role: $role) [timeout após ${TIMEOUT}s]" >> "$LOGFILE"
        echo "| $endpoint | $method | $role | ⏱️ Timeout |" >> "$SUMMARY_FILE"
    else
        echo "❌ $method $endpoint (role: $role) [exit $exit_code]" >> "$LOGFILE"
        echo "| $endpoint | $method | $role | ❌ Falha (exit $exit_code) |" >> "$SUMMARY_FILE"
    fi
    return $exit_code
}

# Lê endpoints do enriched_endpoints.json
# Para cada endpoint, testa para todas as roles possíveis (campo 'roles' lista), ou 'role' (string), ou sem token
COUNT=0
FAIL=0
SUCCESS=0
PIDS=()

while IFS= read -r row; do
    method=$(echo "$row" | jq -r '.method')
    endpoint=$(echo "$row" | jq -r '.path')
    # Extrai lista de roles, se houver
    roles=$(echo "$row" | jq -r '.roles // empty | @sh')
    # Se não houver 'roles', tenta 'role' (string), senão string vazia
    if [ -n "$roles" ]; then
        roles=$(eval echo $roles)
        for role in $roles; do
            base_name=$(echo "$endpoint" | sed 's|^/||; s|/|_|g; s/{[^}]*}/X/g')
            test_data_file="$DATA_DIR/${method}_${base_name}.json"
            run_test "$method" "$endpoint" "$role" "$test_data_file" &
            PIDS+=($!)
            ((COUNT++))
            while [ "$(jobs -rp | wc -l)" -ge "$MAX_PARALLEL" ]; do
                sleep 0.2
            done
        done
    else
        role=$(echo "$row" | jq -r '.role // empty')
        base_name=$(echo "$endpoint" | sed 's|^/||; s|/|_|g; s/{[^}]*}/X/g')
        test_data_file="$DATA_DIR/${method}_${base_name}.json"
        run_test "$method" "$endpoint" "$role" "$test_data_file" &
        PIDS+=($!)
        ((COUNT++))
        while [ "$(jobs -rp | wc -l)" -ge "$MAX_PARALLEL" ]; do
            sleep 0.2
        done
    fi
done < <(jq -c '.[]' "$ENRICHED_ENDPOINTS_JSON")

# Aguarda todos os processos e coleta resultados
for pid in "${PIDS[@]}"; do
    if wait "$pid"; then
        ((SUCCESS++))
    else
        ((FAIL++))
    fi
done

echo "" >> "$SUMMARY_FILE"
echo "## Resumo" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"
echo "- **Total de testes:** $COUNT" >> "$SUMMARY_FILE"
echo "- **✅ Sucessos:** $SUCCESS" >> "$SUMMARY_FILE"
echo "- **❌ Falhas:** $FAIL" >> "$SUMMARY_FILE"
echo ""

echo "====================================="
echo "Testes concluídos : $COUNT"
echo "✅ Sucesso        : $SUCCESS"
echo "❌ Falha          : $FAIL"
echo "Veja o log em: $LOGFILE"
echo "Veja o resumo em: $SUMMARY_FILE"
                """).strip().replace("{api_base}", self.api_base)

    def _write_file_safely(self, file_path: Path, content: str, description: str) -> bool:
        """Escreve arquivo com verificação pós-escrita e logging"""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding='utf-8')
            
            # Verificação pós-escrita
            if file_path.exists() and file_path.stat().st_size > 0:
                print(f"✅ {description}: {file_path}")
                return True
            else:
                print(f"❌ Falha ao escrever {description}: arquivo vazio ou não criado")
                return False
        except PermissionError:
            print(f"❌ Permissão negada para escrever {description}: {file_path}")
            return False
        except Exception as e:
            print(f"❌ Erro ao escrever {description}: {e}")
            return False

    def generate(self):
        """
        Gera a estrutura de arquivos para os testes do Schemathesis.
        """
        print(f"🔧 Iniciando geração de artefatos...")
        
        # Define diretórios de saída
        tests_dir = Path("src/application/pipeline/tests")
        hooks_dir = Path("src/infrastructure/interfaces/hooks")
        pipeline_dir = Path("src/application/pipeline")

        # Cria a estrutura de pastas
        for d in [tests_dir, hooks_dir, pipeline_dir]:
            d.mkdir(parents=True, exist_ok=True)
            print(f"📁 Diretório verificado: {d}")

        # Não cria o diretório dados aqui (responsabilidade de outro step)

        # Contador de sucessos
        success_count = 0
        total_files = 5

        # 1. GERAÇÃO DO __init__.py
        init_content = "from .llm_hooks import before_call\n"
        if self._write_file_safely(hooks_dir / "__init__.py", init_content, "Hooks __init__.py"):
            success_count += 1

        # 2. GERAÇÃO DO auth_hooks.py
        auth_content = self.generate_auth_hooks()
        if self._write_file_safely(hooks_dir / "auth_hooks.py", auth_content, "auth_hooks.py"):
            success_count += 1

        # 3. GERAÇÃO DO llm_hooks.py
        llm_hooks_content = self.generate_llm_hooks()
        if self._write_file_safely(hooks_dir / "llm_hooks.py", llm_hooks_content, "llm_hooks.py"):
            success_count += 1

        # 4. GERAÇÃO DO test_api_security.py
        test_file_content = self.generate_smart_test_file()
        if self._write_file_safely(tests_dir / "test_api_security.py", test_file_content, "test_api_security.py"):
            success_count += 1

        # 5. GERAÇÃO DO step8_run_llm_tests.sh em pipeline/
        sh_content = textwrap.dedent(f"""
#!/bin/bash

# Configurações
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENRICHED_ENDPOINTS_JSON="$SCRIPT_DIR/tests/enriched_endpoints.json"
TEST_SCRIPT="$SCRIPT_DIR/tests/test_api_security.py"
LOGFILE="$(cd "$SCRIPT_DIR/../../.." && pwd)/test_api_llm.log"
SUMMARY_FILE="output/test_api_llm_summary.md"
BASE_URL="{self.api_base}"
MAX_PARALLEL=4

export PYTHONPATH="$(cd \"$SCRIPT_DIR/../../..\" && pwd)"

export USE_LLM_DATA=true
export TEST_LOG_FILE="$LOGFILE"
export TEST_SUMMARY_FILE="$SUMMARY_FILE"

# Remove arquivos anteriores, se existirem
if [ -f "$LOGFILE" ]; then rm "$LOGFILE"; fi
if [ -f "$SUMMARY_FILE" ]; then rm "$SUMMARY_FILE"; fi

# Cabeçalho do log e summary
echo "Execução iniciada em: $(date '+%Y-%m-%d %H:%M:%S')" > "$LOGFILE"
echo "# Relatório de Testes da API" > "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"
echo "**Data da execução:** $(date '+%Y-%m-%d %H:%M:%S')" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"
echo "## Resultados" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"
echo "| Endpoint | Método | Role | Status |" >> "$SUMMARY_FILE"
echo "|----------|--------|------|--------|" >> "$SUMMARY_FILE"

if [ ! -f "$ENRICHED_ENDPOINTS_JSON" ]; then
    echo "Arquivo enriched_endpoints.json não encontrado em $ENRICHED_ENDPOINTS_JSON"
    exit 1
fi

echo "🚀 Iniciando testes LLM Schemathesis"
echo "====================================="
echo "Arquivo de endpoints: $ENRICHED_ENDPOINTS_JSON"
echo "Script de teste: $TEST_SCRIPT"
echo "Base URL: $BASE_URL"
echo "Log: $LOGFILE"
echo "Summary: $SUMMARY_FILE"
echo "====================================="

# Função para obter token via variável de ambiente
get_token() {{
    local role="$1"
    local env_var="TOKEN_${{role^^}}"
    local token="${{!env_var}}"
    echo "$token"
}}

# Função para executar teste de um endpoint/role
run_test() {{
    local method="$1"
    local endpoint="$2"
    local role="$3"
    local test_data_file="$4"
    echo "[INFO] Iniciando teste: $method $endpoint (role: $role)" >> "$LOGFILE"
    local token
    token="$(get_token "$role")"
    local args=(--method "$method" --endpoint "$endpoint" --base-url "$BASE_URL")
    [ -n "$token" ] && args+=(--token "$token")
    [ -n "$test_data_file" ] && [ -f "$test_data_file" ] && args+=(--test-data "$test_data_file")
    local TIMEOUT=120
    timeout $TIMEOUT python3 "$TEST_SCRIPT" "${{args[@]}}" >> "$LOGFILE" 2>&1
    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        echo "✅ $method $endpoint (role: $role)" >> "$LOGFILE"
        echo "| $endpoint | $method | $role | ✅ Sucesso |" >> "$SUMMARY_FILE"
    elif [ $exit_code -eq 124 ]; then
        echo "❌ $method $endpoint (role: $role) [timeout após ${{TIMEOUT}}s]" >> "$LOGFILE"
        echo "| $endpoint | $method | $role | ⏱️ Timeout |" >> "$SUMMARY_FILE"
    else
        echo "❌ $method $endpoint (role: $role) [exit $exit_code]" >> "$LOGFILE"
        echo "| $endpoint | $method | $role | ❌ Falha (exit $exit_code) |" >> "$SUMMARY_FILE"
    fi
    return $exit_code
}}

# Processa endpoints do enriched_endpoints.json
COUNT=0
FAIL=0
SUCCESS=0
PIDS=()

while IFS= read -r row; do
    method=$(echo "$row" | jq -r '.method')
    endpoint=$(echo "$row" | jq -r '.path')
    roles=$(echo "$row" | jq -r '.roles // empty | @sh')
    base_name=$(echo "$endpoint" | sed 's|^/||; s|/|_|g; s/{{[^}}]*}}/X/g')
    test_data_file="$SCRIPT_DIR/tests/dados/${{method}}_${{base_name}}.json"

    if [ -n "$roles" ]; then
        roles_eval=$(eval echo "$roles")
        for role in $roles_eval; do
            run_test "$method" "$endpoint" "$role" "$test_data_file" &
            PIDS+=($!)
            ((COUNT++))
            while [ "$(jobs -rp | wc -l)" -ge "$MAX_PARALLEL" ]; do sleep 0.2; done
        done
    else
        role=$(echo "$row" | jq -r '.role // empty')
        run_test "$method" "$endpoint" "$role" "$test_data_file" &
        PIDS+=($!)
        ((COUNT++))
        while [ "$(jobs -rp | wc -l)" -ge "$MAX_PARALLEL" ]; do sleep 0.2; done
    fi
done < <(jq -c '.[]' "$ENRICHED_ENDPOINTS_JSON")

# Aguarda todos os processos paralelos
for pid in "${{PIDS[@]}}"; do
    if wait "$pid"; then ((SUCCESS++)); else ((FAIL++)); fi
done

# Resumo final
echo "" >> "$SUMMARY_FILE"
echo "## Resumo" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"
echo "- **Total de testes:** $COUNT" >> "$SUMMARY_FILE"
echo "- **✅ Sucessos:** $SUCCESS" >> "$SUMMARY_FILE"
echo "- **❌ Falhas:** $FAIL" >> "$SUMMARY_FILE"

echo "====================================="
echo "Testes concluídos : $COUNT"
echo "✅ Sucesso        : $SUCCESS"
echo "❌ Falha          : $FAIL"
echo "Veja o log em    : $LOGFILE"
echo "Veja o resumo em : $SUMMARY_FILE"
        """).strip()

        if self._write_file_safely(pipeline_dir / "step8_run_llm_tests.sh", sh_content, "step8_run_llm_tests.sh"):
            success_count += 1

        print(f"\n✅ Geração concluída: {success_count}/{total_files} arquivos criados com sucesso.")
        return success_count == total_files


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 step7_generator.py <openapi.json>")
        sys.exit(1)

    openapi_file = sys.argv[1]
    generator = SmartSchemathesisGenerator(openapi_file)
    success = generator.generate()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()