#!/bin/bash

# Configurações
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENRICHED_ENDPOINTS_JSON="$SCRIPT_DIR/tests/enriched_endpoints.json"
TEST_SCRIPT="$SCRIPT_DIR/tests/test_api_security.py"
LOGFILE="$(cd "$SCRIPT_DIR/../../.." && pwd)/test_api_llm.log"
SUMMARY_FILE="output/test_api_llm_summary.md"
BASE_URL="http://localhost"
MAX_PARALLEL=4

export PYTHONPATH="$(cd "$SCRIPT_DIR/../../.." && pwd)"

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
get_token() {
    local role="$1"
    local env_var="TOKEN_${role^^}"
    local token="${!env_var}"
    echo "$token"
}

# Função para executar teste de um endpoint/role
run_test() {
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

# Processa endpoints do enriched_endpoints.json
COUNT=0
FAIL=0
SUCCESS=0
PIDS=()

while IFS= read -r row; do
    method=$(echo "$row" | jq -r '.method')
    endpoint=$(echo "$row" | jq -r '.path')
    roles=$(echo "$row" | jq -r '.roles // empty | @sh')
    base_name=$(echo "$endpoint" | sed 's|^/||; s|/|_|g; s/{[^}]*}/X/g')
    test_data_file="$SCRIPT_DIR/tests/dados/${method}_${base_name}.json"

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
for pid in "${PIDS[@]}"; do
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