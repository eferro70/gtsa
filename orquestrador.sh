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
OUTPUT_DIR="output"

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
    dir=$(ls -td "$OUTPUT_DIR"/scan_* 2>/dev/null | head -n1) || true
    
    if [[ -z "$dir" ]]; then
        log "❌ Nenhum diretório 'scan_*' encontrado em '$OUTPUT_DIR/'"
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
    echo "" >> "$LOGFILE"

    START_TOTAL=$(date +%s)

    # Passo 1: Scan inicial
    run_step 1 "Scan do projeto" \
        python3 src/application/pipeline/step1_scan.py -i "$API_SOURCE"

    # Passo 2: Geração de OpenAPI (opcional)
    # run_step 2 "Geração automática da especificação OpenAPI" \
    #     python3 src/application/pipeline/step2_openapi.py

    # Passo 3: Dados de exemplo (opcional)
    # run_step 3 "Geração de dados de exemplo para testes" \
    #     python3 src/application/pipeline/step3_dados_exemplo.py "$OPENAPI_JSON"

    # Passo 4: Parser AST
    run_step 4 "Parser AST (extração de endpoints)" \
        python3 src/application/pipeline/step4_ast_parser.py "$API_SOURCE"

    # Descobre diretório do scan mais recente automaticamente
    SCAN_DIR=$(get_latest_scan_dir)
    log "🔍 Scan ativo: $(basename "$SCAN_DIR")"

    # Passo 5: Análise de risco (LLM/Heurística)
    run_step 5 "Análise de risco e enriquecimento (LLM)" \
        python3 src/application/pipeline/step5_analyzer.py "$SCAN_DIR/all_endpoints.json" \
        --llm-backend ollama --llm-model codellama:7b

    # Passo 6: Enricher
    run_step 6 "Gerar enriched_endpoints.json" \
        python3 src/application/pipeline/step6_enricher.py "$OPENAPI_JSON" \
        --source "$API_SOURCE"

    # Passo 7: Gerador de testes
    run_step 7 "Gerar testes inteligentes" \
        python3 src/application/pipeline/step7_generator.py "$OPENAPI_JSON"

    # Passo 8: Execução dos testes
    run_step 8 "Executar testes gerados" \
        bash output/tests/run_llm_tests.sh

    # Passo 9: Relatório
    run_step 9 "Gerar relatório de testes" \
        python3 src/application/reporting/gerar_relatorio_markdown.py

    # ────────────────────────────────────────────────────────────────────────
    # 📊 FINALIZAÇÃO
    # ────────────────────────────────────────────────────────────────────────
    END_TOTAL=$(date +%s)
    ELAPSED_TOTAL=$((END_TOTAL - START_TOTAL))
    log "⏱️ Pipeline concluído! Tempo total: ${ELAPSED_TOTAL}s"
    log "📄 Log detalhado salvo em: $LOGFILE"
}

# Executa o pipeline
main "$@"