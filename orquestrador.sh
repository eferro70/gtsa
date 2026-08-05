#!/usr/bin/env bash
# ============================================================================
# 🚀 Orquestrador GTSA - Pipeline de Análise e Teste de APIs
# ============================================================================
set -euo pipefail

# ============================================================================
# 📦 CONFIGURAÇÃO
# ============================================================================
API_NAME="${1:-}"  # ← Usa valor padrão vazio se $1 não existir
if [[ -z "$API_NAME" ]]; then
    echo "❌ Uso: $0 <api_name>"
    exit 1
fi
REPORTS_DIR="output-${API_NAME}"
LLM_MODEL="gemma"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPENAPI_LOCAL="$SCRIPT_DIR/openapi.json"
mkdir -p "$SCRIPT_DIR/logs"
LOGFILE="$SCRIPT_DIR/logs/${API_NAME}.log"

# Garante que o pacote 'gtsa' (layout src/) seja importável sem instalação.
export PYTHONPATH="$SCRIPT_DIR/src:${PYTHONPATH:-}"
# Comando Python padronizado para todos os passos do pipeline.
PYTHON_CMD=(env PYTHONPATH="$PYTHONPATH" python3)

# Carrega variáveis de ambiente do arquivo apis/${API_NAME}/.env
ENV_FILE="$SCRIPT_DIR/apis/${API_NAME}/.env"
if [[ -f "$ENV_FILE" ]]; then
    set +u
    # shellcheck source=.env.${API_NAME}
    source "$ENV_FILE"
    set -u
else
    echo "⚠️  Arquivo .env.${API_NAME} não encontrado em: $ENV_FILE"
    exit 1
fi

# Força isolamento por API e evita fallback acidental para "output/".
REPORTS_DIR="output-${API_NAME}"
export REPORTS_DIR

# Verifica se API_SOURCE está definido
if [[ -z "${API_SOURCE:-}" ]]; then
    echo "❌ API_SOURCE não definido no .env.${API_NAME}"
    exit 1
fi

# Define OPENAPI_JSON
OPENAPI_JSON="${OPENAPI_JSON:-${REPORTS_DIR}/openapi.json}"

cp $OPENAPI_JSON "$OPENAPI_LOCAL" 2>/dev/null || true

# Configurações padrão
VERBOSE_FLAG=""
if [[ "${VERBOSE:-false}" == "true" ]]; then
    VERBOSE_FLAG="--verbose"
fi

# Limpa log anterior
> "$LOGFILE"

# ────────────────────────────────────────────────────────────────────────────
# 🛠️ FUNÇÕES AUXILIARES
# ────────────────────────────────────────────────────────────────────────────
log() {
    local message="$1"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $message" | tee -a "$LOGFILE"
}

run_step() {
    local step_num="$1"
    local description="$2"
    shift 2
    local cmd=("$@")

    log "🔹 [Passo $step_num] Iniciando: $description"
    local start
    start=$(date +%s)

    if "${cmd[@]}" >> "$LOGFILE" 2>&1; then
        local elapsed=$(( $(date +%s) - start ))
        log "✅ [Passo $step_num] Concluído em ${elapsed}s"
    else
        local elapsed=$(( $(date +%s) - start ))
        log "❌ [Passo $step_num] FALHOU após ${elapsed}s. Detalhes em: $LOGFILE"
        exit 1
    fi
    echo "---" >> "$LOGFILE"
}

# ────────────────────────────────────────────────────────────────────────────
# 🚀 PIPELINE PRINCIPAL
# ────────────────────────────────────────────────────────────────────────────
main() {
    log "🚀 Iniciando orquestrador GTSA - Neosigner"
    log "📁 Fonte: $API_SOURCE"
    log "📄 OpenAPI: $OPENAPI_JSON"
    log "🤖 LLM Model: ${LLM_MODEL:-gemma}"
    log "📡 LLM Backend: ${LLM_BACKEND:-ollama}"
    log "⚙️  STEP_2_ENABLED=${STEP_2_ENABLED:-false} | STEP_3_ENABLED=${STEP_3_ENABLED:-true}"
    log "⚙️  ONLY_HIGH_RISK=${ONLY_HIGH_RISK:-false} | MAX_EXAMPLES=${MAX_EXAMPLES:-10}"
    log "⚙️  VERBOSE=${VERBOSE:-false} | PYTHON_DEBUG=${PYTHON_DEBUG:-false}"
    echo "" >> "$LOGFILE"

    START_TOTAL=$(date +%s)

    ##############################################################################
    # INICIO DO PIPELINE
    ##############################################################################

    # Limpar dados da execução anterior
    log "🧹 Limpando diretório de relatórios: $REPORTS_DIR"
    rm -rf "$REPORTS_DIR"
    mkdir -p "$REPORTS_DIR"

    # Passo 1: Scan inicial
    run_step 1 "Scan do projeto" \
        "${PYTHON_CMD[@]}" -m gtsa.interfaces.cli.step1_scan -i "$API_SOURCE" \
        --output-dir "$REPORTS_DIR" \
        ${API_LANGUAGE:+--language "$API_LANGUAGE"} \
        ${PYTHON_DEBUG:+--debug}

    # Passo 2: Geração de OpenAPI (opcional)
    if [[ "${STEP_2_ENABLED:-false}" == "true" ]]; then
        run_step 2 "Geração automática da especificação OpenAPI" \
            "${PYTHON_CMD[@]}" -m gtsa.interfaces.cli.step2_openapi \
            --output-dir "$REPORTS_DIR" \
            --env-file "$ENV_FILE"
    else
        log "⏭️  [Passo 2] Pulando (STEP_2_ENABLED=false)"
    fi

    # Passo 3: [LLM] Dados de exemplo
    if [[ "$STEP_3_ENABLED" == "true" ]]; then
        run_step 3 "[LLM] Geração de dados de exemplo para testes" \
            "${PYTHON_CMD[@]}" -m gtsa.interfaces.cli.step3_dados_exemplo "$OPENAPI_LOCAL" \
            --only-with-body \
            --env-file "$ENV_FILE" \
            --llm-backend "$LLM_BACKEND" \
            --llm-model "$LLM_MODEL"
    else
        log "⏭️  [Passo 3] Pulando (STEP_3_ENABLED=false)"
    fi

    # Descobre diretório do scan mais recente
    SCAN_DIR=$(ls -td "$SCRIPT_DIR"/runtime/scans/scan_* 2>/dev/null | head -n1)
    if [[ -z "$SCAN_DIR" ]]; then
        log "❌ Nenhum diretório 'scan_*' encontrado"
        exit 1
    fi

    # Passo 4: Análise de risco
    run_step 4 "Análise de risco e enriquecimento" \
        "${PYTHON_CMD[@]}" -m gtsa.interfaces.cli.step4_analyzer_and_enricher "$SCAN_DIR/all_endpoints.json" \
        --output-dir "$REPORTS_DIR" \
        --openapi "$OPENAPI_LOCAL" \
        --env-file "$ENV_FILE" \
        --no-llm

    # Passo 5: Schemathesis com dados reais
    log "🔹 [Passo 5] Iniciando: Schemathesis com dados reais"

    # Exporta apenas o necessário para o subprocesso (os scripts vão usar --env-file)
    export API_BASE_URL="$API_BASE_URL"
    export OPENAPI_JSON="$OPENAPI_JSON"
    export ENV_FILE="$ENV_FILE"  # necessário para o schemathesis_hooks.py carregar o .env correto

    ONLY_HIGH_RISK_FLAG=""
    if [[ "${ONLY_HIGH_RISK:-false}" == "true" ]]; then
        ONLY_HIGH_RISK_FLAG="--only-high-risk"
    fi

    STEP5_EXIT=0
    "${PYTHON_CMD[@]}" -m gtsa.interfaces.cli.step5_schemathesis_with_data \
        --output-dir "$REPORTS_DIR" \
        --env-file "$ENV_FILE" \
        $ONLY_HIGH_RISK_FLAG \
        $VERBOSE_FLAG || STEP5_EXIT=$?

    # Passo 6: Relatório
    run_step 6 "Gerar relatório de testes" \
        "${PYTHON_CMD[@]}" -m gtsa.interfaces.cli.step6_gerar_relatorio_markdown \
        --output-dir "$REPORTS_DIR" \
        --env-file "$ENV_FILE" \
        ${FULL_REPORT:+--full} \
        ${HIDE_SUCCESS:+--hide-success} \
        ${HIDE_SKIP:+--hide-skip}
    }

main "$@"