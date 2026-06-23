# 🔒 Relatório de Testes Schemathesis

*Gerado em: 2026-06-23 15:41:03*

## ⚙️ Configuração dos Testes

✅ **Teste completo**: Todos os endpoints da OpenAPI spec foram testados.

## 📊 Resumo Geral dos Testes

| Métrica | Valor |
|---------|-------|
| **Total de casos de teste gerados** | **446** |
| ✅ Testes bem-sucedidos | 44 |
| ❌ Testes com falha | 166 |
| ⚠️ Erros de schema | 0 |
| ⏭️ Testes ignorados | 33 |
| **Taxa de sucesso** | **21.0%** |
| ⏱️ Duração total | 6.45s |

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
| Erro interno do servidor (500) | 53 | 🔴 Alta |
| Header obrigatório ausente não rejeitado | 41 | 🔴 Alta |
| Aceita autenticação inválida | 1 | 🔴 Alta |
| Rejeita requisição válida (falso positivo) | 11 | 🟠 Média |
| Resposta viola schema documentado | 3 | 🟠 Média |
| Status HTTP não documentado | 30 | 🟡 Baixa |

## 📋 Detalhamento por Endpoint (Top 10 com mais falhas)

| Método | Endpoint | Testes | ✅ | ❌ | ⚠️ |
|--------|----------|--------|----|----|-----|

## 🐛 Principais Falhas Encontradas

**1. POST /api/v1/clientes**

```
1. Test Case ID: cauIAI  - Server error  [500] Internal Server Error:      <EMPTY>  Reproduce with:      curl -X POST -H 'Authorization: [Filtered]' -H 'Content-Type: application/json' -d '{"contratante": {"tipoCliente": "TRIBUNAL", "nome": "Tribunal de Justi\u00e7a", "identificador": "1234567800019
```

**2. POST /api/v1/contas/perfil/{perfil}**

```
1. Test Case ID: dAqcrR  - Server error  [500] Internal Server Error:      <EMPTY>  Reproduce with:      curl -X POST -H 'Authorization: [Filtered]' -H 'Content-Type: application/json' -d '{"nome": "Gestor Exemplo", "codigo": "94287999045", "tipoCodigo": "CPF", "tipoConta": "PESSOA", "email": "gesto
```

**3. POST /api/v1/fluxos**

```
1. Test Case ID: NaDXmh  - Server error  [500] Internal Server Error:      <EMPTY>  Reproduce with:      curl -X POST -H 'Authorization: [Filtered]' -H 'Content-Type: application/json' -d '{"dadosBasicos": {"nome": "Fluxo de Assinatura", "descricao": "Fluxo para assinatura de contratos", "idRequisit
```

**4. POST /api/v1/fluxos/adicionar**

```
1. Test Case ID: Df1gsA  - Server error  [500] Internal Server Error:      <EMPTY>  Reproduce with:      curl -X POST -H 'Authorization: [Filtered]' -H 'Content-Type: application/json' -d '{"dadosBasicos": {"nome": "Fluxo de Assinatura", "descricao": "Fluxo para assinatura de contratos", "idRequisit
```

**5. POST /api/v1/grupos**

```
1. Test Case ID: uBAmdM  - Server error  [500] Internal Server Error:      <EMPTY>  Reproduce with:      curl -X POST -H 'Authorization: [Filtered]' -H 'Content-Type: application/json' -d '{"preferencias": {"tipoAssinatura": {"permiteAlteracao": true, "tipo": "ELETRONICA"}}, "nome": "", "idCliente":
```

**6. POST /api/v1/verify-authentication**

```
1. Test Case ID: DP7pjH  - Undocumented HTTP status code      Received: 422     Documented: 200, 400, 401, 500  [422] Unprocessable Content:      `{"property":"authenticatorResponse","message":"Parâmetro 'authenticatorResponse' é obrigatório.","data":null}`  Reproduce with:      curl -X POST -H 'Con
```

**7. POST /api/v1/verify-registration**

```
1. Test Case ID: 6QhJMz  - Undocumented HTTP status code      Received: 422     Documented: 200, 400, 401, 500  [422] Unprocessable Content:      `{"property":"authenticatorResponse","message":"Parâmetro 'authenticatorResponse' é obrigatório.","data":null}`  Reproduce with:      curl -X POST -H 'Con
```

**8. PUT /api/v1/login-sistema**

```
1. Test Case ID: Ro5o56  - Response violates schema      null is not of type "object"      Schema at /components/schemas/PhoneOutput:          {             "type": "object",             "required": [                 "number",                 "nationalNumber",                 "countryCode",         
```

**9. PUT /api/v1/token**

```
1. Test Case ID: IIs5oT  - Undocumented HTTP status code      Received: 403     Documented: 200, 401, 500  [403] Forbidden:      `{"error":"CSRF validation failed."}`  Reproduce with:      curl -X PUT -H 'Authorization: [Filtered]' -H 'Cookie: [Filtered]' http://localhost/api/v1/token
```

**10. GET /api/monitoracao/dlqs**

```
1. Test Case ID: R6hwL4  - Undocumented HTTP status code      Received: 404     Documented: 200  [404] Not Found:      `404 page not found`  Reproduce with:      curl -X GET 'http://localhost/api/monitoracao/dlqs?nomeCliente=&data='
```

*... e mais 52 falhas*

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
