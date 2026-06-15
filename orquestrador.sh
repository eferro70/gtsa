#!/usr/bin/env bash
# ============================================================================
# 🚀 Orquestrador GTSA - Pipeline de Análise e Teste de APIs
# ============================================================================
set -euo pipefail

# ────────────────────────────────────────────────────────────────────────────
# 📦 CONFIGURAÇÃO
# ────────────────────────────────────────────────────────────────────────────
API_SOURCE="/home/s231991563/projetos/neosigner/controlador-api/src"
OPENAPI_JSON="$API_SOURCE/swagger/specs/openapi.json"
LOGFILE="orquestrador.log"
REPORTS_DIR="output"
SCAN_DIR=src/application/pipeline/tests/scan_20260428_160549
LLM_MODEL="gemma"
OPENAPI_LOCAL="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/openapi.json"

# Carrega variáveis de ambiente do arquivo .env
ENV_FILE="$(dirname "${BASH_SOURCE[0]}")/.env"
if [[ -f "$ENV_FILE" ]]; then
    set +u
    # shellcheck source=.env
    source "$ENV_FILE"
    set -u
fi

# Configurações padrão (respeita .env)
STEP_2_ENABLED="${STEP_2_ENABLED:-false}"
STEP_3_ENABLED="${STEP_3_ENABLED:-true}"
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
    log "🚀 Iniciando orquestrador GTSA"
    log "📁 Fonte: $API_SOURCE"
    log "📄 OpenAPI: $OPENAPI_JSON"
    log "⚙️  STEP_2_ENABLED=$STEP_2_ENABLED | STEP_3_ENABLED=$STEP_3_ENABLED"
    echo "" >> "$LOGFILE"

    # Copia a spec OpenAPI
    log "📋 Copiando OpenAPI spec para diretório local: $OPENAPI_LOCAL"
    cp "$OPENAPI_JSON" "$OPENAPI_LOCAL"
    export OPENAPI_LOCAL

    START_TOTAL=$(date +%s)

    # Passo 1: Scan inicial
    run_step 1 "Scan do projeto" \
        python3 src/application/pipeline/step1_scan.py -i "$API_SOURCE"

    # Passo 2: Geração de OpenAPI (opcional)
    if [[ "$STEP_2_ENABLED" == "true" ]]; then
        run_step 2 "Geração automática da especificação OpenAPI" \
            python3 src/application/pipeline/step2_openapi.py
    else
        log "⏭️  [Passo 2] Pulando (STEP_2_ENABLED=false)"
    fi

    # Passo 3: [LLM] Dados de exemplo
    if [[ "$STEP_3_ENABLED" == "true" ]]; then
        run_step 3 "[LLM] Geração de dados de exemplo para testes" \
            python3 src/application/pipeline/step3_dados_exemplo.py "$OPENAPI_LOCAL" --only-with-body --llm-backend ollama --llm-model "$LLM_MODEL"
    else
        log "⏭️  [Passo 3] Pulando (STEP_3_ENABLED=false)"
    fi

    # Descobre diretório do scan mais recente
    SCAN_DIR=$(ls -td src/application/pipeline/tests/scan_* 2>/dev/null | head -n1)
    if [[ -z "$SCAN_DIR" ]]; then
        log "❌ Nenhum diretório 'scan_*' encontrado"
        exit 1
    fi

    # Passo 4: Análise de risco
    run_step 4 "Análise de risco e enriquecimento" \
        python3 src/application/pipeline/step4_analyzer_and_enricher.py "$SCAN_DIR/all_endpoints.json" --openapi "$OPENAPI_LOCAL" --no-llm

    # Passo 5: Schemathesis com dados reais
    log "🔹 [Passo 5] Iniciando: Schemathesis com dados reais"
    
    # Exporta tokens para o subprocesso
    export TOKEN_REQUISITANTE="${TOKEN_REQUISITANTE:-}"
    export TOKEN_GESTOR="${TOKEN_GESTOR:-}"
    export TOKEN_ADMINISTRADOR="${TOKEN_ADMINISTRADOR:-}"
    export TOKEN_INTERESSADO="${TOKEN_INTERESSADO:-}"
    export CHAVE_ACESSO_SISTEMA="${CHAVE_ACESSO_SISTEMA:-}"
    export API_BASE_URL="${API_BASE_URL:-http://localhost}"
    export ONLY_HIGH_RISK="${ONLY_HIGH_RISK:-false}"
    export MAX_EXAMPLES="${MAX_EXAMPLES:-10}"
    export VERBOSE="${VERBOSE:-false}"
    
    # Executa o Schemathesis
    STEP5_EXIT=0
    python3 src/application/pipeline/step5_schemathesis_with_data.py $VERBOSE_FLAG || STEP5_EXIT=$?
    
    if [ $STEP5_EXIT -eq 0 ]; then
        log "✅ [Passo 5] Concluído com sucesso"
    else
        log "⚠️ [Passo 5] Concluído com exit $STEP5_EXIT"
    fi

    # Passo 6: Relatório
    run_step 6 "Gerar relatório de testes" \
        python3 src/application/pipeline/step6_gerar_relatorio_markdown.py

    # Propaga falha do passo 6
    [ $STEP6_EXIT -eq 0 ] || exit $STEP6_EXIT

    END_TOTAL=$(date +%s)
    ELAPSED_TOTAL=$((END_TOTAL - START_TOTAL))
    log "⏱️  Pipeline concluído! Tempo total: ${ELAPSED_TOTAL}s"
    log "📄 Log detalhado salvo em: $LOGFILE"
}

main "$@"