#!/usr/bin/env bash
# ============================================================================
# step6_schemathesis.sh (CORRIGIDO)
# ============================================================================
set -euo pipefail

# ── Caminhos ─────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPENAPI_JSON="${OPENAPI_JSON:-$SCRIPT_DIR/../../../openapi.json}"
ENRICHED_ENDPOINTS_JSON="${ENRICHED_ENDPOINTS_JSON:-$SCRIPT_DIR/tests/enriched_endpoints.json}"
AUTH_HOOK="${AUTH_HOOK:-$(cd "$SCRIPT_DIR/../../.." && pwd)/src/infrastructure/interfaces/hooks/schemathesis_auth_hook.py}"
OUTPUT_DIR="$SCRIPT_DIR/../../../output"
JUNIT_XML="$OUTPUT_DIR/schemathesis_results.xml"
LOGFILE="$OUTPUT_DIR/schemathesis.log"

# ── Configurações ─────────────────────────────────────────────────────────────
ONLY_HIGH_RISK="${ONLY_HIGH_RISK:-false}"
MAX_EXAMPLES="${MAX_EXAMPLES:-10}"
VERBOSE="${VERBOSE:-false}"
BASE_URL="${API_BASE_URL:-http://localhost}"

# Exporta o caminho do JSON enriquecido para o hook Python
export ENRICHED_ENDPOINTS_JSON

# ── Cores ─────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; NC='\033[0m'

# ── Validações iniciais ───────────────────────────────────────────────────────
if ! command -v schemathesis &>/dev/null; then
    echo -e "${RED}❌ Schemathesis não encontrado. Execute: pip install schemathesis${NC}"
    exit 1
fi

if [ ! -f "$OPENAPI_JSON" ]; then
    echo -e "${RED}❌ OpenAPI spec não encontrada: $OPENAPI_JSON${NC}"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

echo "============================================================"
echo "🔒 SCHEMATHESIS - TESTES DE SEGURANÇA DE API"
echo "============================================================"
echo "📋 Configurações:"
echo "   - Base URL:        $BASE_URL"
echo "   - OpenAPI spec:    $OPENAPI_JSON"
echo "   - Apenas alto risco: $ONLY_HIGH_RISK"
echo "   - Max examples:    $MAX_EXAMPLES"
echo "   - JUnit XML:       $JUNIT_XML"
echo "   - Log:             $LOGFILE"
echo "============================================================"

# ── Gera OpenAPI filtrado se ONLY_HIGH_RISK=true ──────────────────────────────
SPEC_TO_USE="$OPENAPI_JSON"

if [ "$ONLY_HIGH_RISK" = "true" ]; then
    if [ ! -f "$ENRICHED_ENDPOINTS_JSON" ]; then
        echo -e "${RED}❌ enriched_endpoints.json não encontrado: $ENRICHED_ENDPOINTS_JSON${NC}"
        exit 1
    fi

    FILTERED_SPEC="$OUTPUT_DIR/openapi_high_risk.json"
    echo -e "${BLUE}🔍 Filtrando apenas endpoints de alto risco...${NC}"

    python3 - <<'PYEOF'
import json, sys, os

enriched_path = os.environ["ENRICHED_ENDPOINTS_JSON"]
openapi_path  = os.environ.get("OPENAPI_JSON")
output_path   = os.path.join(os.environ.get("OUTPUT_DIR", "output"), "openapi_high_risk.json")

with open(enriched_path) as f:
    enriched = json.load(f)

high_risk = {
    (ep["method"].lower(), ep["path"])
    for ep in enriched
    if ep.get("risk_level") == "alto"
}

if not high_risk:
    print("⚠️  Nenhum endpoint de alto risco encontrado. Usando spec completa.")
    import shutil
    shutil.copy(openapi_path, output_path)
    sys.exit(0)

with open(openapi_path) as f:
    spec = json.load(f)

filtered_paths = {}
for path, path_item in spec.get("paths", {}).items():
    filtered_methods = {}
    for method, operation in path_item.items():
        if method.lower() in ("get","post","put","patch","delete","options","head"):
            if (method.lower(), path) in high_risk:
                filtered_methods[method] = operation
    if filtered_methods:
        filtered_paths[path] = filtered_methods

spec["paths"] = filtered_paths
with open(output_path, "w") as f:
    json.dump(spec, f, indent=2, ensure_ascii=False)

print(f"✅ Spec filtrada: {len(filtered_paths)} paths de alto risco → {output_path}")
PYEOF

    SPEC_TO_USE="$FILTERED_SPEC"
    echo -e "${GREEN}✅ Spec filtrada gerada: $SPEC_TO_USE${NC}"
fi

# ── Configuração do Hook (CORRIGIDA) ─────────────────────────────────────────
# SOLUÇÃO 1: Usar --hooks com caminho de arquivo (recomendado para Schemathesis 3.x)
# SOLUÇÃO 2: Configurar PYTHONPATH para importar o módulo corretamente

# Obtém o diretório base do projeto
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Adiciona o diretório raiz ao PYTHONPATH
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$PROJECT_ROOT"

# Converte o caminho absoluto para um caminho relativo ao PYTHONPATH
# Ex: /home/user/projeto/src/infrastructure/interfaces/hooks/schemathesis_auth_hook.py
#  → src.infrastructure.interfaces.hooks.schemathesis_auth_hook
if [ -f "$AUTH_HOOK" ]; then
    # Remove o PROJECT_ROOT do início do caminho
    RELATIVE_PATH="${AUTH_HOOK#$PROJECT_ROOT/}"
    # Remove a extensão .py e converte / para .
    HOOK_MODULE="${RELATIVE_PATH%.py}"
    HOOK_MODULE="${HOOK_MODULE//\//.}"
    
    echo -e "${BLUE}🔌 Configurando hook de autenticação:${NC}"
    echo "   - Hook file: $AUTH_HOOK"
    echo "   - Module: $HOOK_MODULE"
    echo "   - PYTHONPATH: $PYTHONPATH"
    
    export SCHEMATHESIS_HOOKS="$HOOK_MODULE"
else
    echo -e "${YELLOW}⚠️  Hook de autenticação não encontrado: $AUTH_HOOK${NC}"
    echo "   Continuando sem autenticação..."
    unset SCHEMATHESIS_HOOKS
fi

# ── Monta argumentos do Schemathesis ─────────────────────────────────────────
SCHEMATHESIS_ARGS=(
    run "$SPEC_TO_USE"
    --url "$BASE_URL"
    --checks all
    -n "$MAX_EXAMPLES"
    --report junit
    --report-junit-path "$JUNIT_XML"
    --seed 42
    --output-truncate false
)

# Verbosidade
if [ "$VERBOSE" = "true" ]; then
    SCHEMATHESIS_ARGS+=(--workers auto -v)
fi

# ── Executa ───────────────────────────────────────────────────────────────────
echo -e "${BLUE}🚀 Iniciando Schemathesis...${NC}"
echo "Comando: schemathesis ${SCHEMATHESIS_ARGS[*]}" | tee "$LOGFILE"
echo "---" >> "$LOGFILE"

set +e  # Não abortar no exit code ≠ 0 do Schemathesis (falhas de teste são esperadas)
schemathesis "${SCHEMATHESIS_ARGS[@]}" 2>&1 | tee -a "$LOGFILE"
EXIT_CODE=${PIPESTATUS[0]}
set -e

echo "============================================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ Schemathesis concluído sem falhas${NC}"
elif [ $EXIT_CODE -eq 1 ]; then
    echo -e "${YELLOW}⚠️  Schemathesis encontrou falhas de teste (exit 1)${NC}"
    echo -e "   Verifique o relatório: $JUNIT_XML"
else
    echo -e "${RED}❌ Schemathesis encerrou com erro inesperado (exit $EXIT_CODE)${NC}"
fi
echo "📄 Log completo:  $LOGFILE"
echo "📊 JUnit XML:     $JUNIT_XML"
echo "============================================================"

# Propaga exit code para o orquestrador
exit $EXIT_CODE