# 🔒 Relatório de Testes Schemathesis

*Gerado em: 2026-07-01 10:51:07*

## ⚙️ Configuração dos Testes

✅ **Teste completo**: Todos os endpoints da OpenAPI spec foram testados.

## 📊 Resumo Geral dos Testes

| Métrica | Valor |
|---------|-------|
| **Total de casos de teste gerados** | **1,081** |
| ✅ Testes bem-sucedidos | 172 |
| ❌ Testes com falha | 148 |
| ⚠️ Erros de schema | 0 |
| ⏭️ Testes ignorados | 33 |
| **Taxa de sucesso** | **53.8%** |
| ⏱️ Duração total | 23.12s |

## 🎯 Cobertura de Endpoints

| Métrica | Valor |
|---------|-------|
| Total de operações na spec | 69 |
| ✅ Endpoints testados | 66 |
| ⚠️ Endpoints com erro | 0 |
| ⏭️ Endpoints ignorados | 3 |

## 🔍 Tipos de Falha Encontrados

| Tipo de Falha | Quantidade | Severidade |
|---------------|------------|------------|
| Erro interno do servidor (500) | 1 | 🔴 Alta |
| Header obrigatório ausente não rejeitado | 1 | 🔴 Alta |
| Aceita autenticação inválida | 7 | 🔴 Alta |
| Rejeita requisição válida (falso positivo) | 29 | 🟠 Média |
| Resposta viola schema documentado | 2 | 🟠 Média |
| Status HTTP não documentado | 15 | 🟡 Baixa |
| Outras falhas | 42 | 🟡 Baixa |

## 📋 Detalhamento por Endpoint (Top 10 com mais falhas)

| Método | Endpoint | Testes | ✅ | ❌ | ⚠️ |
|--------|----------|--------|----|----|-----|

## 🐛 Principais Falhas Encontradas

**1. POST /api/v1/clientes**

```
1. Test Case ID: 0eYp8h  - JSON deserialization error      Response must be valid JSON with 'Content-Type: application/json' header:        Expecting value: line 1 column 1 (char 0)  - Missing Content-Type header      The following media types are documented in the schema:     - `application/json`  
```

**2. POST /api/v1/contas/perfil/{perfil}**

```
1. Test Case ID: Pze4IJ  - API accepts invalid authentication      Expected 401, got `201 Created` for `POST /api/v1/contas/perfil/{perfil}` (generated auth likely invalid)  - Response violates schema      null is not of type "string"      Schema at /components/schemas/ContaSimplesOutput/properties/
```

**3. POST /api/v1/fluxos**

```
1. Test Case ID: VCUB6t  - API rejected schema-compliant request      Valid data should have been accepted     Expected: 2xx, 401, 403, 404, 409, 5xx  [422] Unprocessable Content:      `{"property":"dataLimiteResposta","message":"A data limite da resposta deve ser superior a data atual.","data":null
```

**4. POST /api/v1/fluxos/adicionar**

```
1. Test Case ID: SS8y1e  - API rejected schema-compliant request      Valid data should have been accepted     Expected: 2xx, 401, 403, 404, 409, 5xx     Hint: The request body contains 3 additional properties not defined in the schema (`dadosBasicos`, `documentos`, `interessados`). The server likel
```

**5. POST /api/v1/grupos**

```
1. Test Case ID: ZVfrlc  - API accepts invalid authentication      Expected 401, got `201 Created` for `POST /api/v1/grupos` (generated auth likely invalid)  [201] Created:      `{"id":"6ad74663-9357-4b3c-8d60-f9a07e528211","idCliente":"1ae08e30-d3d9-4230-be09-200663596bdf","nome":"Grupo Jurídico","
```

**6. POST /api/v1/verify-authentication**

```
1. Test Case ID: 40WKz1  - Undocumented HTTP status code      Received: 422     Documented: 200, 400, 401, 500  [422] Unprocessable Content:      `{"property":"authenticatorResponse","message":"Parâmetro 'authenticatorResponse' é obrigatório.","data":null}`  Reproduce with:      curl -X POST -H 'Con
```

**7. POST /api/v1/verify-registration**

```
1. Test Case ID: jIKubs  - API rejected schema-compliant request      Valid data should have been accepted     Expected: 2xx, 401, 403, 404, 409, 5xx  [422] Unprocessable Content:      `{"property":"authenticatorResponse","message":"Parâmetro 'authenticatorResponse' é obrigatório.","data":null}`  Re
```

**8. PUT /api/v1/login-sistema**

```
1. Test Case ID: yDVRgC  - API rejected schema-compliant request      Valid data should have been accepted     Expected: 2xx, 401, 403, 404, 409, 5xx  [422] Unprocessable Content:      `{"property":"x-chave-acesso-sistema","message":"Parâmetro 'x-chave-acesso-sistema' é obrigatório.","data":null}`  
```

**9. PUT /api/v1/token**

```
1. Test Case ID: enHWve  - JSON deserialization error      Response must be valid JSON with 'Content-Type: application/json' header:        Expecting value: line 1 column 1 (char 0)  - Missing Content-Type header      The following media types are documented in the schema:     - `application/json`  
```

**10. GET /api/v1/clientes**

```
1. Test Case ID: HYa9Db  - JSON deserialization error      Response must be valid JSON with 'Content-Type: application/json' header:        Expecting value: line 1 column 1 (char 0)  - Missing Content-Type header      The following media types are documented in the schema:     - `application/json`  
```

*... e mais 51 falhas*

## 💡 Recomendações

### 🔴 Críticas (Corrigir Imediatamente)

1. **Erros internos do servidor (500)** - API está quebrando com entradas válidas
   - Verifique logs do servidor para stack traces
   - Adicione tratamento de exceções nos endpoints
   - Valide inputs antes de processar

### 🟠 Segurança

1. **Falhas de autenticação** - Endpoints aceitando tokens inválidos
   - Implemente validação rigorosa de tokens JWT
   - Retorne 401 para credenciais inválidas

### 🟡 Documentação

1. **Inconsistências de schema** - Respostas não correspondem à documentação
   - Atualize a OpenAPI spec para refletir a implementação real
   - Ou corrija a implementação para seguir a spec

## 📁 Informações Técnicas

- **Arquivo de log:** `/home/s231991563/projetos/gtsa/output-neosigner/schemathesis_execution.log`
- **Relatório JUnit:** `/home/s231991563/projetos/gtsa/output-neosigner/schemathesis_results.xml`
- **Ferramenta:** [Schemathesis](https://schemathesis.readthedocs.io/)
- **Comando executado:** `schemathesis run --checks all --report junit`

*Relatório gerado automaticamente pelo pipeline de testes GTSA.*
