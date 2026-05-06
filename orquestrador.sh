#!/usr/bin/env bash
# ============================================================================
# 🚀 Orquestrador GTSA - Pipeline de Análise e Teste de APIs
# ============================================================================
set -euo pipefail  # Sai imediatamente em erros, trata pipes e variáveis não definidas

# ────────────────────────────────────────────────────────────────────────────
# 📦 CONFIGURAÇÃO
# ────────────────────────────────────────────────────────────────────────────
API_SOURCE="/home/s231991563/projetos/neosigner/controlador-api/src"
OPENAPI_JSON="$API_SOURCE/swagger/specs/openapi.json"
LOGFILE="orquestrador.log"
REPORTS_DIR="output"
SCAN_DIR=src/application/pipeline/tests/scan_20260428_160549
LLM_MODEL="gemma"

# Variáveis padrão para controle de passos (podem ser sobrescritas pelo .env)
STEP_2_ENABLED="true"
STEP_3_ENABLED="true"

# Carrega variáveis de ambiente do arquivo .env (sobrescreve os padrões se definidas)
ENV_FILE="$(dirname "${BASH_SOURCE[0]}")/.env"
if [[ -f "$ENV_FILE" ]]; then
    set +u  # Desabilita verificação de variáveis não definidas para sourcing
    # shellcheck source=.env
    source "$ENV_FILE"
    set -u  # Re-habilita verificação
fi

# Limpa log anterior para garantir execução limpa
> "$LOGFILE"

# ────────────────────────────────────────────────────────────────────────────
# 🛠️ FUNÇÕES AUXILIARES
# ────────────────────────────────────────────────────────────────────────────
log() {
    local message="$1"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    # Imprime no console e anexa ao arquivo de log
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

    # Executa o comando. Saída vai para o log, console mostra apenas o progresso.
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

get_latest_scan_dir() {
    # Busca diretórios scan_* ordenados por data (mais recente primeiro)
    local dir
    dir=$(ls -td "$REPORTS_DIR"/scan_* 2>/dev/null | head -n1) || true
    
    if [[ -z "$dir" ]]; then
        log "❌ Nenhum diretório 'scan_*' encontrado em '$REPORTS_DIR/'"
        log "💡 Execute primeiro o Passo 4 (Parser AST)"
        exit 1
    fi
    echo "$dir"
}

# ────────────────────────────────────────────────────────────────────────────
# 🚀 PIPELINE PRINCIPAL
# ────────────────────────────────────────────────────────────────────────────
main() {
    log "🚀 Iniciando orquestrador GTSA"
    log "📁 Fonte: $API_SOURCE"
    log "📄 OpenAPI: $OPENAPI_JSON"
    log "⚙️  Controle de passos: STEP_2_ENABLED=$STEP_2_ENABLED | STEP_3_ENABLED=$STEP_3_ENABLED"
    echo "" >> "$LOGFILE"

    START_TOTAL=$(date +%s)

    # Passo 1: Scan inicial
    run_step 1 "Scan do projeto" \
        python3 src/application/pipeline/step1_scan.py -i "$API_SOURCE"

    # Passo 2: Geração de OpenAPI (opcional)
    if [[ "$STEP_2_ENABLED" == "true" || "$STEP_2_ENABLED" == "1" ]]; then
        run_step 2 "Geração automática da especificação OpenAPI" \
            python3 src/application/pipeline/step2_openapi.py
    else
        log "⏭️  [Passo 2] Pulando: Geração automática da especificação OpenAPI (STEP_2_ENABLED=false)"
    fi

    # Passo 3: [LLM] Dados de exemplo (opcional)
    if [[ "$STEP_3_ENABLED" == "true" || "$STEP_3_ENABLED" == "1" ]]; then
        run_step 3 "[LLM] Geração de dados de exemplo para testes" \
            python3 src/application/pipeline/step3_dados_exemplo.py "$OPENAPI_JSON" --only-with-body --llm-backend ollama --llm-model "$LLM_MODEL"
    else
        log "⏭️  [Passo 3] Pulando: Geração de dados de exemplo para testes (STEP_3_ENABLED=false)"
    fi

    # Descobre diretório do scan mais recente automaticamente
    SCAN_DIR=$(ls -td src/application/pipeline/tests/scan_* 2>/dev/null | head -n1)
    if [[ -z "$SCAN_DIR" ]]; then
        log "❌ Nenhum diretório 'scan_*' encontrado em 'src/application/pipeline/tests/'"
        log "💡 Execute primeiro o Passo 4 (Parser AST)"
        exit 1
    fi

    # Passo 4: [LLM] Análise de risco (Heurística)
    run_step 4 "[LLM] Análise de risco e enriquecimento" \
        python3 src/application/pipeline/step4_analyzer_and_enricher.py "$SCAN_DIR/all_endpoints.json" --openapi docs/openapi.yaml --llm-backend ollama

    # Passo 5: Gerador de testes
    run_step 5 "Gerar testes inteligentes" \
        python3 src/application/pipeline/step5_generator.py "$OPENAPI_JSON" 

    # Passo 6: [LLM] Execução dos testes
    run_step 6 "[LLM] Executar testes gerados" \
        bash src/application/pipeline/step6_run_llm_tests.sh --llm-backend ollama --llm-model "$LLM_MODEL"

    # Passo 7: Relatório
    run_step 7 "Gerar relatório de testes" \
        python3 src/application/pipeline/step7_gerar_relatorio_markdown.py

    # ────────────────────────────────────────────────────────────────────────
    # 📊 FINALIZAÇÃO
    # ────────────────────────────────────────────────────────────────────────
    END_TOTAL=$(date +%s)
    ELAPSED_TOTAL=$((END_TOTAL - START_TOTAL))
    log "⏱️  Pipeline concluído! Tempo total: ${ELAPSED_TOTAL}s"
    log "📄 Log detalhado salvo em: $LOGFILE"
}

# Executa o pipeline
main "$@"