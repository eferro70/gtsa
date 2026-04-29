#!/bin/bash

export PYTHONPATH="$(pwd)"
# Configurações
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENRICHED_ENDPOINTS_JSON="$SCRIPT_DIR/tests/enriched_endpoints.json"
TEST_SCRIPT="$SCRIPT_DIR/tests/test_api_security.py"
DATA_DIR="$SCRIPT_DIR/dados"
LOGFILE="$(dirname "$SCRIPT_DIR")/../../test_api_llm.log"
SUMMARY_FILE="output/test_api_llm_summary.md"
BASE_URL="http://localhost"
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