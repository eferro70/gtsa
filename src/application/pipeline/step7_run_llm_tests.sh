#!/bin/bash

# ============================================================
# step7_run_llm_tests.sh (OTIMIZADO)
# ============================================================
# Configurações de segurança
ONLY_HIGH_RISK="${ONLY_HIGH_RISK:-false}"           # Testar apenas endpoints de alto risco
SKIP_NO_AUTH="${SKIP_NO_AUTH:-false}"               # Pular endpoints sem autenticação
MAX_RISK_SCORE="${MAX_RISK_SCORE:-1.0}"             # Score máximo (0.0-1.0)
TEST_BY_VULN="${TEST_BY_VULN:-false}"               # Testar especificamente por vulnerabilidade
VERBOSE="${VERBOSE:-false}"                         # Log detalhado
PARALLEL_JOBS="${PARALLEL_JOBS:-4}"                 # Jobs paralelos

# Configurações padrão
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENRICHED_ENDPOINTS_JSON="$SCRIPT_DIR/tests/enriched_endpoints.json"
TEST_SCRIPT="$SCRIPT_DIR/tests/test_api_security.py"
LOGFILE="$(cd "$SCRIPT_DIR/../../.." && pwd)/test_api_llm.log"
SUMMARY_FILE="output/test_api_llm_summary.md"
BASE_URL="${API_BASE_URL:-http://localhost}"
MAX_PARALLEL="$PARALLEL_JOBS"

export PYTHONPATH="$(cd "$SCRIPT_DIR/../../.." && pwd)"
export USE_LLM_DATA=true
export TEST_LOG_FILE="$LOGFILE"
export TEST_SUMMARY_FILE="$SUMMARY_FILE"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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
get_token() {
    local role="$1"
    local env_var="TOKEN_${role^^}"
    local token="${!env_var}"
    echo "$token"
}

normalize_endpoint_for_filename() {
    local endpoint="$1"
    echo "$endpoint" | sed -E 's|:[^/]+|X|g; s|\{[^}]+\}|X|g; s|^/||; s|/|_|g'
}

resolve_test_data_file() {
    local method="$1"
    local endpoint="$2"
    local candidate_file=""

    local base_name
    base_name="$(normalize_endpoint_for_filename "$endpoint")"
    candidate_file="$SCRIPT_DIR/tests/dados/${method}_${base_name}.json"
    if [ -f "$candidate_file" ]; then
        echo "$candidate_file"
        return
    fi

    if [[ "$endpoint" =~ ^/api/ ]] && [[ ! "$endpoint" =~ ^/api/v1/ ]]; then
        local endpoint_v1
        endpoint_v1="${endpoint/#\/api\//\/api\/v1\/}"
        base_name="$(normalize_endpoint_for_filename "$endpoint_v1")"
        candidate_file="$SCRIPT_DIR/tests/dados/${method}_${base_name}.json"
        if [ -f "$candidate_file" ]; then
            echo "$candidate_file"
            return
        fi
    fi

    echo ""
}

# Função para executar teste de um endpoint/role
run_test() {
    local method="$1"
    local endpoint="$2"
    local role="$3"
    local risk_level="$4"
    local vulnerabilities="$5"
    local pii_fields="$6"
    local test_data_file="$7"
    
    local security_context=$(jq -n         --arg risk "$risk_level"         --argjson vulns "$(echo "$vulnerabilities" | jq -R 'split(",")')"         --argjson pii "$(echo "$pii_fields" | jq -R 'split(",")')"         '{risk_level: $risk, vulnerabilities: $vulns, pii_fields: $pii}')
    
    echo "[INFO] Iniciando teste: $method $endpoint (role: $role, risco: $risk_level)" >> "$LOGFILE"
    
    local token="$(get_token "$role")"
    local args=(--method "$method" --endpoint "$endpoint" --base-url "$BASE_URL")
    [ -n "$token" ] && args+=(--token "$token")
    [ -n "$test_data_file" ] && [ -f "$test_data_file" ] && args+=(--test-data "$test_data_file")
    args+=(--security-context "$security_context")
    
    local TIMEOUT=120
    timeout $TIMEOUT python3 "$TEST_SCRIPT" "${args[@]}" >> "$LOGFILE" 2>&1
    local exit_code=$?
    
    local vuln_display=$(echo "$vulnerabilities" | sed 's/,/, /g')
    if [ -z "$vuln_display" ] || [ "$vuln_display" = "null" ]; then
        vuln_display="-"
    fi
    
    if [ $exit_code -eq 0 ]; then
        echo -e "$GREEN✅ $method $endpoint (role: $role)$NC"
        echo "| $endpoint | $method | $risk_level | $vuln_display | ✅ Sucesso |" >> "$SUMMARY_FILE"
    elif [ $exit_code -eq 124 ]; then
        echo -e "$RED❌ $method $endpoint (role: $role) [TIMEOUT]${NC}"
        echo "| $endpoint | $method | $risk_level | $vuln_display | ⏱️ Timeout |" >> "$SUMMARY_FILE"
    else
        echo -e "$RED❌ $method $endpoint (role: $role) [exit $exit_code]${NC}"
        echo "| $endpoint | $method | $risk_level | $vuln_display | ❌ Falha (exit $exit_code) |" >> "$SUMMARY_FILE"
    fi
    return $exit_code
}

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
    echo -e "$BLUE🔒 $method $endpoint - Risco: $risk_level ($risk_score) | Vulns: ${vulnerabilities:-nenhuma} | PII: ${pii_fields:-nenhuma}$NC"
    
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
for pid in "${PIDS[@]}"; do
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