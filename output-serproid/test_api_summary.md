# 🔒 Relatório de Testes Schemathesis

*Gerado em: 2026-06-24 11:00:12*

## ⚙️ Configuração dos Testes

✅ **Teste completo**: Todos os endpoints da OpenAPI spec foram testados.

## 📊 Resumo Geral dos Testes

| Métrica | Valor |
|---------|-------|
| **Total de casos de teste gerados** | **614** |
| ✅ Testes bem-sucedidos | 45 |
| ❌ Testes com falha | 144 |
| ⚠️ Erros de schema | 0 |
| ⏭️ Testes ignorados | 78 |
| **Taxa de sucesso** | **23.8%** |
| ⏱️ Duração total | 60.07s |

## 🎯 Cobertura de Endpoints

| Métrica | Valor |
|---------|-------|
| Total de operações na spec | 78 |
| ✅ Endpoints testados | 78 |
| ⚠️ Endpoints com erro | 0 |
| ⏭️ Endpoints ignorados | 0 |

## 🔍 Tipos de Falha Encontrados

| Tipo de Falha | Quantidade | Severidade |
|---------------|------------|------------|
| Erro interno do servidor (500) | 67 | 🔴 Alta |
| Rejeita requisição válida (falso positivo) | 67 | 🟠 Média |
| Status HTTP não documentado | 67 | 🟡 Baixa |

## 📋 Detalhamento por Endpoint (Top 10 com mais falhas)

| Método | Endpoint | Testes | ✅ | ❌ | ⚠️ |
|--------|----------|--------|----|----|-----|

## 🐛 Principais Falhas Encontradas

**1. POST /oauth/v1/oauth/aplicativos/solicitacao/assinatura**

```
1. Test Case ID: pk1p7a  - API rejected schema-compliant request      Valid data should have been accepted     Expected: 2xx, 401, 403, 404, 409, 5xx  - Undocumented HTTP status code      Received: 415     Documented: 200, 400, 401, 403, 404, 500  [415] Unsupported Media Type:      `[{"error_descrip
```

**2. POST /oauth/v1/oauth/applications/{clientId}/activation**

```
1. Test Case ID: OnbKe9  - API rejected schema-compliant request      Valid data should have been accepted     Expected: 2xx, 401, 403, 404, 409, 5xx  - Undocumented HTTP status code      Received: 412     Documented: 200, 400, 401, 403, 404, 500  [412] Precondition Failed:      `{"code":"CLIENTE_OA
```

**3. POST /oauth/v1/oauth/applications/{clientId}/redirect-uris**

```
1. Test Case ID: bcEnxT  - Undocumented HTTP status code      Received: 415     Documented: 200, 400, 401, 403, 404, 500  [415] Unsupported Media Type:      `[{"error_description":["RESTEASY003065: Cannot consume content type"],"error":"Http exception"}]`  Reproduce with:      curl -X POST 'https://
```

**4. POST /oauth/v1/oauth/dispositivos/cadastrar-com-credencial-pedido/pedido/{numeroReferencia}**

```
1. Test Case ID: 7rMJpp  - Undocumented HTTP status code      Received: 406     Documented: 200, 400, 401, 403, 404, 500  [406] Not Acceptable:      `{"code":"VERSAO_APP_INCOMPATIVEL","msg":"Versão da aplicação incompatível com a versão atual.","debug":""}`  Reproduce with:      curl -X POST 'https:
```

**5. POST /oauth/v1/oauth/dispositivos/email/otp/enviar**

```
1. Test Case ID: OMarBW  - API rejected schema-compliant request      Valid data should have been accepted     Expected: 2xx, 401, 403, 404, 409, 5xx  - Undocumented HTTP status code      Received: 406     Documented: 200, 400, 401, 403, 404, 500  [406] Not Acceptable:      `{"code":"VERSAO_APP_INCO
```

**6. POST /oauth/v1/oauth/dispositivos/otp/validar**

```
1. Test Case ID: dDm07M  - API rejected schema-compliant request      Valid data should have been accepted     Expected: 2xx, 401, 403, 404, 409, 5xx  - Undocumented HTTP status code      Received: 406     Documented: 200, 400, 401, 403, 404, 500  [406] Not Acceptable:      `{"code":"VERSAO_APP_INCO
```

**7. POST /oauth/v1/oauth/dispositivos/sms/otp/enviar**

```
1. Test Case ID: qr3WHH  - API rejected schema-compliant request      Valid data should have been accepted     Expected: 2xx, 401, 403, 404, 409, 5xx  - Undocumented HTTP status code      Received: 406     Documented: 200, 400, 401, 403, 404, 500  [406] Not Acceptable:      `{"code":"VERSAO_APP_INCO
```

**8. POST /oauth/v1/oauth/dispositivos/{dispositivo}/chave/instalacao/{idInstalacao}**

```
1. Test Case ID: 8Loejl  - API rejected schema-compliant request      Valid data should have been accepted     Expected: 2xx, 401, 403, 404, 409, 5xx  - Undocumented HTTP status code      Received: 406     Documented: 200, 400, 401, 403, 404, 500  [406] Not Acceptable:      `{"code":"VERSAO_APP_INCO
```

**9. POST /oauth/v1/oauth/drivers/assinatura**

```
1. Test Case ID: CRVlOp  - Undocumented HTTP status code      Received: 412     Documented: 200, 400, 401, 403, 404, 500  [412] Precondition Failed:      `{"code":"UUID_NAO_INFORMADO","msg":"UUID não foi informado","debug":""}`  Reproduce with:      curl -X POST 'https://hom.serproid.serpro.gov.br/o
```

**10. POST /oauth/v1/oauth/v2/drivers/assinatura**

```
1. Test Case ID: qwzNo8  - Undocumented HTTP status code      Received: 412     Documented: 200, 400, 401, 403, 404, 500  [412] Precondition Failed:      `{"code":"UUID_NAO_INFORMADO","msg":"UUID não foi informado","debug":""}`  Reproduce with:      curl -X POST 'https://hom.serproid.serpro.gov.br/o
```

*... e mais 57 falhas*

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
