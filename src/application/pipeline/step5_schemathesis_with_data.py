#!/usr/bin/env python3
"""
step6_schemathesis_with_data.py - Executa Schemathesis injetando os dados
gerados pelo Step 3 (tests/dados/) via spec aumentada com x-example,
e cobre endpoints GET com query params via WSGI hook.

Estratégia por tipo de endpoint:
  - POST/PUT/PATCH com body   → injeta x-example no requestBody da spec filtrada
  - GET/DELETE com query params → injetados via schemathesis hook (override de
                                  query string em before_call), disparados como
                                  casos fixos antes do fuzzing aleatório
  - Endpoints sem dados       → fuzzing aleatório normal do Schemathesis
"""

import json
import os
import subprocess
import sys
import re
from pathlib import Path
from datetime import datetime

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent  # gtsa/
TESTS_DATA_DIR = SCRIPT_DIR / "tests" / "dados"
OPENAPI_JSON = Path("openapi.json")
ENRICHED_ENDPOINTS_JSON = TESTS_DATA_DIR / "enriched_endpoints.json"
OUTPUT_DIR = PROJECT_ROOT / "output"
JUNIT_XML = OUTPUT_DIR / "schemathesis_results.xml"
LOGFILE = OUTPUT_DIR / "schemathesis.log"

# ============================================================================
# ENDPOINTS PROBLEMÁTICOS
# ============================================================================

SKIP_ENDPOINTS = [
    "POST /api/v1/documentos",
    "PATCH /api/v1/verificar-certificado-nuvem",
    "GET /api/v1/autenticar-certificado",
    "PATCH /api/v1/verificar-certificado",
    "PUT /api/v1/login-sistema",
    "GET /api/monitoracao/dlqs",
    "PATCH /api/v1/notificar",
    "PATCH /api/v1/fluxos/arquivar",
    "PATCH /api/v1/fluxos/finalizar",
]

SKIP_METHODS = ["TRACE", "OPTIONS", "HEAD"]

INVALID_SCHEMA_REFERENCES = [
    "AutenticacaoCertificadoNuvemInput",
]

# ============================================================================
# MAPEAMENTO: nome-de-arquivo → (method, openapi_path)
#
# O Step 3 salva arquivos com o padrão:
#   METHOD_api_v1_recurso_X_subrecurso.json
# onde X é um placeholder para path params.
# Este dicionário mapeia o stem do arquivo para o caminho OpenAPI correspondente.
# Acrescente entradas aqui se o Step 3 gerar novos arquivos.
# ============================================================================

FILE_TO_ENDPOINT: dict[str, tuple[str, str]] = {
    # autenticação
    "PATCH_api_v1_enviar-otp":                       ("PATCH", "/api/v1/enviar-otp"),
    "PATCH_api_v1_verificar-otp":                    ("PATCH", "/api/v1/verificar-otp"),
    "PATCH_api_v1_link":                             ("PATCH", "/api/v1/link"),
    # clientes
    "POST_api_v1_clientes":                          ("POST",  "/api/v1/clientes"),
    "PUT_api_v1_clientes_X":                         ("PUT",   "/api/v1/clientes/{id}"),
    # contas
    "POST_api_v1_contas_perfil_X":                   ("POST",  "/api/v1/contas/perfil/{perfil}"),
    "PUT_api_v1_contas_perfil_X_X":                  ("PUT",   "/api/v1/contas/perfil/{perfil}/{id}"),
    "PATCH_api_v1_contas_reenviar-credenciais-sistema": ("PATCH", "/api/v1/contas/reenviar-credenciais-sistema"),
    # documentos (está em SKIP_ENDPOINTS mas mantemos o mapeamento)
    "POST_api_v1_documentos":                        ("POST",  "/api/v1/documentos"),
    # fluxos
    "POST_api_v1_fluxos":                            ("POST",  "/api/v1/fluxos"),
    "POST_api_v1_fluxos_adicionar":                  ("POST",  "/api/v1/fluxos/adicionar"),
    "PATCH_api_v1_fluxos_X_rejeitar":                ("PATCH", "/api/v1/fluxos/{id}/rejeitar"),
    "PATCH_api_v1_fluxos_X_assinar":                 ("PATCH", "/api/v1/fluxos/{id}/assinar"),
    "PATCH_api_v1_fluxos_X_revisar":                 ("PATCH", "/api/v1/fluxos/{id}/revisar"),
    "PATCH_api_v1_fluxos_X_revisao":                 ("PATCH", "/api/v1/fluxos/{id}/revisao"),
    "PATCH_api_v1_fluxos_X_assinar-serpro-id":       ("PATCH", "/api/v1/fluxos/{id}/assinar-serpro-id"),
    "PATCH_api_v1_fluxos_X_assinar-bird-id":         ("PATCH", "/api/v1/fluxos/{id}/assinar-bird-id"),
    "PATCH_api_v1_fluxos_X_assinar-safe-id":         ("PATCH", "/api/v1/fluxos/{id}/assinar-safe-id"),
    "PATCH_api_v1_fluxos_X_assinar-vidaas":          ("PATCH", "/api/v1/fluxos/{id}/assinar-vidaas"),
    "PATCH_api_v1_fluxos_X_assinar-ds-cloud":        ("PATCH", "/api/v1/fluxos/{id}/assinar-ds-cloud"),
    "PATCH_api_v1_fluxos_X_assinar-syn-id":          ("PATCH", "/api/v1/fluxos/{id}/assinar-syn-id"),
    "PATCH_api_v1_fluxos_X_assinar-certisign":       ("PATCH", "/api/v1/fluxos/{id}/assinar-certisign"),
    "PATCH_api_v1_fluxos_X_assinar-desktop_X":       ("PATCH", "/api/v1/fluxos/{id}/assinar-desktop/{algoritmo}"),
    # grupos
    "POST_api_v1_grupos":                            ("POST",  "/api/v1/grupos"),
    "PUT_api_v1_grupos_X":                           ("PUT",   "/api/v1/grupos/{id}"),
}

# ============================================================================
# QUERY PARAMS FIXOS PARA ENDPOINTS GET SEM BODY
#
# Para endpoints GET que precisam de parâmetros de query específicos
# (ex.: os que apresentam injection), definimos valores iniciais seguros
# que garantem ao menos um teste bem-formado além do fuzzing.
# ============================================================================

GET_QUERY_FIXTURES: dict[str, dict] = {
    "/api/v1/fluxos-interessado": {
        "nome": "", "status": "", "pendente": "true",
        "sortField": "nome", "sortDirection": "ASC",
        "offset": "0", "limit": "10",
    },
    "/api/v1/fluxos/{id}/interessados": {
        "sortField": "nome", "sortDirection": "ASC",
        "offset": "0", "limit": "10",
    },
    "/api/v1/clientes": {
        "nome": "", "sigla": "",
        "sortField": "nome", "sortDirection": "ASC",
        "limit": "10", "offset": "0",
    },
    "/api/v1/contas": {
        "nome": "", "perfil": "",
        "limit": "10", "offset": "0",
    },
    "/api/v1/grupos": {
        "nome": "", "id": "",
        "sortDirection": "ASC",
        "limit": "10", "offset": "0",
    },
}

# ============================================================================
# CARREGAMENTO DE .ENV
# ============================================================================

def load_env_file(env_path: Path) -> dict:
    env_vars = {}
    if not env_path.exists():
        print(f"⚠️  Arquivo .env não encontrado: {env_path}")
        return env_vars
    print(f"\n📋 Carregando .env: {env_path}")
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                value = value.strip().strip('"').strip("'")
                env_vars[key.strip()] = value
                print(f"   ✅ Carregado: {key.strip()}")
    return env_vars


ENV_FILE = PROJECT_ROOT / ".env"
ENV_VARS = load_env_file(ENV_FILE)

# ============================================================================
# CONFIGURAÇÕES DE AMBIENTE
# ============================================================================

BASE_URL     = ENV_VARS.get("API_BASE_URL",   os.getenv("API_BASE_URL",   "http://localhost"))
MAX_EXAMPLES = int(ENV_VARS.get("MAX_EXAMPLES", os.getenv("MAX_EXAMPLES", "10")))
VERBOSE      = ENV_VARS.get("VERBOSE",  os.getenv("VERBOSE",  "false")).lower() == "true"
ONLY_HIGH_RISK = ENV_VARS.get("ONLY_HIGH_RISK", os.getenv("ONLY_HIGH_RISK", "false")).lower() == "true"

TOKEN_REQUISITANTE  = ENV_VARS.get("TOKEN_REQUISITANTE",  os.getenv("TOKEN_REQUISITANTE",  ""))
TOKEN_GESTOR        = ENV_VARS.get("TOKEN_GESTOR",        os.getenv("TOKEN_GESTOR",        ""))
TOKEN_ADMINISTRADOR = ENV_VARS.get("TOKEN_ADMINISTRADOR", os.getenv("TOKEN_ADMINISTRADOR", ""))
TOKEN_INTERESSADO   = ENV_VARS.get("TOKEN_INTERESSADO",   os.getenv("TOKEN_INTERESSADO",   ""))

DEFAULT_TOKEN = TOKEN_REQUISITANTE or TOKEN_ADMINISTRADOR or TOKEN_GESTOR or TOKEN_INTERESSADO

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


def load_dados_exemplo() -> dict[str, dict]:
    """
    Lê todos os JSONs em TESTS_DATA_DIR e retorna um dict
    { openapi_path: body_dict } para endpoints com requestBody,
    usando FILE_TO_ENDPOINT como mapeamento.
    """
    dados: dict[str, dict] = {}
    if not TESTS_DATA_DIR.exists():
        print(f"⚠️  Diretório de dados não encontrado: {TESTS_DATA_DIR}")
        return dados

    arquivos = list(TESTS_DATA_DIR.glob("*.json"))
    print(f"\n📂 Dados encontrados em {TESTS_DATA_DIR}: {len(arquivos)} arquivo(s)")

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


def inject_examples_into_spec(spec_path: Path, dados: dict[str, dict]) -> Path:
    """
    Copia a spec filtrada e injeta x-example nos requestBody
    dos endpoints que têm dados gerados pelo Step 3.
    Retorna o caminho do novo arquivo.
    """
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
                        # Injeta tanto em schema.example quanto em examples
                        content_def["schema"]["example"] = example_body
                        content_def["examples"] = {
                            "step3_example": {
                                "summary": "Dado gerado pelo Step 3",
                                "value": example_body,
                            }
                        }
                        injetados += 1
                        print(f"   💉 Injetado exemplo em: {key} ({media_type})")
                        break  # basta injetar no primeiro media type

    enriched_spec = OUTPUT_DIR / "openapi_enriched.json"
    with open(enriched_spec, 'w') as f:
        json.dump(spec, f, indent=2)

    print(f"\n   📁 Spec enriquecida salva em: {enriched_spec}")
    print(f"   💉 Total de exemplos injetados: {injetados}")
    return enriched_spec


def generate_hook_file(query_fixtures: dict[str, dict], token: str) -> Path:
    """
    Gera schemathesis_hooks.py compatível com Schemathesis 4.x.
    Carregado via variável de ambiente SCHEMATHESIS_HOOKS.

    Hooks usados:
      map_headers — injeta Authorization em todas as chamadas
      map_query   — injeta query params fixos nos GETs críticos,
                    mesclando com valores fuzzados pelo Schemathesis
    """
    fixtures_repr = json.dumps(query_fixtures, ensure_ascii=False, indent=4)
    token_repr = repr(token)

    # ATENÇÃO: NÃO usar textwrap.dedent nem indentação relativa aqui.
    # O arquivo gerado deve começar na coluna 0, senão Python levanta IndentationError.
    lines = [
        "# Hook gerado automaticamente pelo Step 6 — não editar manualmente",
        "# Compatível com Schemathesis >= 4.0  (map_query / map_headers)",
        "import schemathesis",
        "",
        f"_QUERY_FIXTURES = {fixtures_repr}",
        f"_TOKEN = {token_repr}",
        "",
        "",
        "@schemathesis.hook",
        "def map_headers(context, headers):",
        '    """Garanta Authorization em todas as chamadas."""',
        "    if _TOKEN:",
        "        if headers is None:",
        "            headers = {}",
        '        headers.setdefault("Authorization", f"Bearer {_TOKEN}")',
        "    return headers",
        "",
        "",
        "@schemathesis.hook",
        "def map_query(context, query):",
        '    """Injeta query params fixos para endpoints GET críticos."""',
        "    path = context.operation.path",
        "    if path in _QUERY_FIXTURES:",
        "        base = dict(_QUERY_FIXTURES[path])",
        "        if query:",
        "            base.update(query)  # preserva valores fuzzados pelo Schemathesis",
        "        return base",
        "    return query",
    ]
    hook_code = "\n".join(lines) + "\n"

    hook_path = OUTPUT_DIR / "schemathesis_hooks.py"
    with open(hook_path, "w", encoding="utf-8") as f:
        f.write(hook_code)

    print(f"   🔧 Hook gerado em: {hook_path}")
    return hook_path


def filter_openapi_spec(spec_path: Path) -> Path:
    with open(spec_path, 'r') as f:
        spec = json.load(f)

    original_count = sum(len(methods) for methods in spec.get("paths", {}).values())
    print(f"\n📊 Endpoints originais: {original_count}")

    filtered_paths = {}
    for path, methods in spec.get("paths", {}).items():
        filtered_methods = {
            method: op
            for method, op in methods.items()
            if not should_skip_endpoint(method, path, op)
        }
        if filtered_methods:
            filtered_paths[path] = filtered_methods

    filtered_count = sum(len(m) for m in filtered_paths.values())
    print(f"\n📈 Resumo da filtragem:")
    print(f"   ✅ Endpoints mantidos: {filtered_count}")
    print(f"   🚫 Endpoints removidos: {original_count - filtered_count}")

    spec["paths"] = filtered_paths
    filtered_spec = OUTPUT_DIR / "openapi_filtered.json"
    with open(filtered_spec, 'w') as f:
        json.dump(spec, f, indent=2)
    print(f"   📁 Spec filtrada salva em: {filtered_spec}")
    return filtered_spec


def build_schemathesis_command(spec_path: Path, token: str, hook_path: Path) -> tuple[list, dict]:
    """Retorna (cmd, extra_env) — o hook é carregado via SCHEMATHESIS_HOOKS.

    SCHEMATHESIS_HOOKS espera um nome de módulo Python importável (sem .py),
    não um caminho de arquivo. Por isso é necessário também adicionar o
    diretório do hook ao PYTHONPATH para que o import funcione.
    """
    cmd = [
        "schemathesis", "run", str(spec_path),
        "--url", BASE_URL,
        "--checks", "all",
        "-n", str(MAX_EXAMPLES),
        "--report", "junit",
        "--report-junit-path", str(JUNIT_XML),
        "--seed", "42",
        "--output-truncate", "false",
    ]
    if token:
        cmd.extend(["--header", f"Authorization: Bearer {token}"])
    if VERBOSE:
        cmd.append("-v")

    # SCHEMATHESIS_HOOKS aceita nome de módulo Python (sem extensão .py).
    # O diretório que contém o hook precisa estar no PYTHONPATH.
    hook_module_name = hook_path.stem          # ex: "schemathesis_hooks"
    hook_dir = str(hook_path.parent)           # ex: "/home/.../output"
    current_pythonpath = os.environ.get("PYTHONPATH", "")
    new_pythonpath = f"{hook_dir}:{current_pythonpath}" if current_pythonpath else hook_dir

    extra_env = {
        "SCHEMATHESIS_HOOKS": hook_module_name,
        "PYTHONPATH": new_pythonpath,
    }
    return cmd, extra_env


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("\n" + "="*60)
    print("🚀 Schemathesis - Testes de API com dados reais")
    print("="*60)

    print(f"\n📋 Configurações:")
    print(f"   - Base URL:         {BASE_URL}")
    print(f"   - Max examples:     {MAX_EXAMPLES}")
    print(f"   - Apenas alto risco:{ONLY_HIGH_RISK}")
    print(f"   - Verbose:          {VERBOSE}")
    print(f"   - PROJECT_ROOT:     {PROJECT_ROOT}")
    print(f"   - Dados Step 3:     {TESTS_DATA_DIR}")

    print(f"\n🔑 Tokens carregados do .env:")
    for label, tok in [
        ("REQUISITANTE",  TOKEN_REQUISITANTE),
        ("GESTOR",        TOKEN_GESTOR),
        ("ADMINISTRADOR", TOKEN_ADMINISTRADOR),
        ("INTERESSADO",   TOKEN_INTERESSADO),
    ]:
        status = f"✅ ({len(tok)} chars)" if tok else "❌"
        print(f"   - {label}: {status}")

    print(f"\n🔑 Token padrão: {'✅' if DEFAULT_TOKEN else '❌'}")
    if DEFAULT_TOKEN:
        print(f"   - Token: {DEFAULT_TOKEN[:50]}...")

    if not OPENAPI_JSON.exists():
        print(f"\n❌ OpenAPI não encontrada: {OPENAPI_JSON}")
        sys.exit(1)

    if not DEFAULT_TOKEN:
        print("\n❌ Nenhum token configurado! Abortando.")
        print(f"   Configure TOKEN_REQUISITANTE em: {ENV_FILE}")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── 1. Filtra spec ──────────────────────────────────────────────────────
    print("\n📝 Filtrando OpenAPI spec...")
    filtered_spec = filter_openapi_spec(OPENAPI_JSON)

    # ── 2. Carrega dados do Step 3 ──────────────────────────────────────────
    print("\n📂 Carregando dados gerados pelo Step 3...")
    dados = load_dados_exemplo()

    sem_dados = []
    with open(filtered_spec, 'r') as f:
        spec = json.load(f)
    for path, methods in spec.get("paths", {}).items():
        for method in methods:
            key = f"{method.upper()} {path}"
            has_body = "requestBody" in methods[method]
            has_dados = key in dados
            if has_body and not has_dados:
                sem_dados.append(key)

    if sem_dados:
        print(f"\n⚠️  {len(sem_dados)} endpoint(s) com body mas SEM dados do Step 3 (usarão fuzzing):")
        for e in sem_dados:
            print(f"   - {e}")

    # ── 3. Injeta exemplos na spec ──────────────────────────────────────────
    print("\n💉 Injetando exemplos do Step 3 na spec...")
    enriched_spec = inject_examples_into_spec(filtered_spec, dados)

    # ── 4. Gera hook com query fixtures ────────────────────────────────────
    print("\n🔧 Gerando hook de query params...")
    hook_path = generate_hook_file(GET_QUERY_FIXTURES, DEFAULT_TOKEN)

    # ── 5. Monta e executa o comando ────────────────────────────────────────
    print("\n" + "="*60)
    print("🚀 Executando Schemathesis")
    print("="*60)

    cmd, extra_env = build_schemathesis_command(enriched_spec, DEFAULT_TOKEN, hook_path)
    run_env = {**os.environ, **extra_env}
    print(f"Comando: {' '.join(cmd)}")
    print(f"   SCHEMATHESIS_HOOKS={extra_env['SCHEMATHESIS_HOOKS']}")
    print(f"   PYTHONPATH={extra_env['PYTHONPATH']}")
    print("-"*60)

    result = subprocess.run(cmd, capture_output=True, text=True, env=run_env)

    # ── 6. Salva log ────────────────────────────────────────────────────────
    logfile = OUTPUT_DIR / "schemathesis_requisitante.log"
    with open(logfile, "w", encoding="utf-8") as f:
        f.write(f"Comando: {' '.join(cmd)}\n")
        f.write(f"SCHEMATHESIS_HOOKS: {extra_env['SCHEMATHESIS_HOOKS']}\n")
        f.write(f"Data: {datetime.now().isoformat()}\n")
        f.write(f"Token usado: {DEFAULT_TOKEN[:50]}...\n")
        f.write(f"Dados Step 3 carregados: {len(dados)}\n")
        f.write(f"Query fixtures: {list(GET_QUERY_FIXTURES.keys())}\n")
        f.write("---\n")
        f.write(result.stdout)
        if result.stderr:
            f.write("\n--- STDERR ---\n")
            f.write(result.stderr)

    print(f"\n📄 Log salvo em: {logfile}")

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    if JUNIT_XML.exists():
        print(f"\n📊 Relatório JUnit salvo em: {JUNIT_XML}")

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()