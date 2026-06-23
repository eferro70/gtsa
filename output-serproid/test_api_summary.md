# 🔒 Relatório de Testes Schemathesis

*Gerado em: 2026-06-23 10:46:13*

## ⚙️ Configuração dos Testes

✅ **Teste completo**: Todos os endpoints da OpenAPI spec foram testados.

## 📊 Resumo Geral dos Testes

| Métrica | Valor |
|---------|-------|
| **Total de casos de teste gerados** | **48** |
| ✅ Testes bem-sucedidos | 4 |
| ❌ Testes com falha | 8 |
| ⚠️ Erros de schema | 0 |
| ⏭️ Testes ignorados | 6 |
| **Taxa de sucesso** | **33.3%** |
| ⏱️ Duração total | 3.23s |

## 🎯 Cobertura de Endpoints

| Métrica | Valor |
|---------|-------|
| Total de operações na spec | 6 |
| ✅ Endpoints testados | 6 |
| ⚠️ Endpoints com erro | 0 |
| ⏭️ Endpoints ignorados | 0 |

## 🔍 Tipos de Falha Encontrados

| Tipo de Falha | Quantidade | Severidade |
|---------------|------------|------------|
| Erro interno do servidor (500) | 4 | 🔴 Alta |
| Rejeita requisição válida (falso positivo) | 4 | 🟠 Média |
| Status HTTP não documentado | 4 | 🟡 Baixa |

## 📋 Detalhamento por Endpoint (Top 10 com mais falhas)

| Método | Endpoint | Testes | ✅ | ❌ | ⚠️ |
|--------|----------|--------|----|----|-----|

## 🐛 Principais Falhas Encontradas

**1. PUT /oauth/v1/oauth/applications/{clientId}**

```
1. Test Case ID: nmSIkj  - Undocumented HTTP status code      Received: 415     Documented: 200, 400, 401, 403, 404, 500  [415] Unsupported Media Type:      `[{"error_description":["RESTEASY003065: Cannot consume content type"],"error":"Http exception"}]`  Reproduce with:      curl -X PUT 'https://h
```

**2. POST /oauth/v1/oauth/applications/{clientId}/activation**

```
1. Test Case ID: x8ujcP  - API rejected schema-compliant request      Valid data should have been accepted     Expected: 2xx, 401, 403, 404, 409, 5xx  - Undocumented HTTP status code      Received: 412     Documented: 200, 400, 401, 403, 404, 500  [412] Precondition Failed:      `{"code":"CLIENTE_OA
```

**3. POST /oauth/v1/oauth/applications/{clientId}/redirect-uris**

```
1. Test Case ID: a6mqj9  - Undocumented HTTP status code      Received: 415     Documented: 200, 400, 401, 403, 404, 500  [415] Unsupported Media Type:      `[{"error_description":["RESTEASY003065: Cannot consume content type"],"error":"Http exception"}]`  Reproduce with:      curl -X POST 'https://
```

**4. DELETE /oauth/v1/oauth/applications/{clientId}/redirect-uris**

```
1. Test Case ID: ya17X1  - Undocumented HTTP status code      Received: 415     Documented: 200, 400, 401, 403, 404, 500  [415] Unsupported Media Type:      `[{"error_description":["RESTEASY003065: Cannot consume content type"],"error":"Http exception"}]`  Reproduce with:      curl -X DELETE 'https:
```

## 💡 Recomendações

### 🔴 Críticas (Corrigir Imediatamente)

1. **Erros internos do servidor (500)** - API está quebrando com entradas válidas
   - Verifique logs do servidor para stack traces
   - Adicione tratamento de exceções nos endpoints
   - Valide inputs antes de processar

## 📁 Informações Técnicas

- **Arquivo de log:** `/home/s231991563/projetos/gtsa/output-serproid/schemathesis_execution.log`
- **Relatório JUnit:** `/home/s231991563/projetos/gtsa/output-serproid/schemathesis_results.xml`
- **Ferramenta:** [Schemathesis](https://schemathesis.readthedocs.io/)
- **Comando executado:** `schemathesis run --checks all --report junit`

*Relatório gerado automaticamente pelo pipeline de testes GTSA.*
