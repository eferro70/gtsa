# GTSA – Gerador de Testes de Segurança para APIs

## Visão Geral

O GTSA é uma ferramenta automatizada para análise, geração e execução de testes de segurança em APIs REST, com integração opcional a LLMs (Modelos de Linguagem) para geração inteligente de dados de teste e análise de riscos.

- **Geração de testes baseada em OpenAPI**
- **Análise heurística e via LLM dos endpoints**
- **Execução automatizada com Schemathesis + Pytest**
- **Relatórios de riscos, PII e vulnerabilidades**
- **Suporte a autenticação (token, cookies, headers)**

## Estrutura do Projeto

```
├── README.md                  # Documentação principal
├── requirements.txt           # Dependências Python
├── output/                    # Resultados e artefatos gerados
│   ├── ast/                   # Saída de análise estática (endpoints, relatórios, scans)
│   └── tests/                 # Testes gerados automaticamente (Pytest/Schemathesis)
├── src/                       # Código-fonte principal
│   ├── analyzers/             # Analisadores heurísticos e LLM
│   │   └── llm_analyzer.py
│   ├── ast/                   # Parsers e scripts de análise estática
│   │   ├── auto_enricher.py
│   │   ├── test_parser.py
│   │   └── parsers/
│   │       └── ast_parser_node.py
│   ├── generators/            # Geradores de testes e artefatos
│   │   ├── openapi_generator.py
│   │   └── smart_generator.py
│   └── utils/                 # Utilitários e payloads de segurança
│       ├── extrair_roles_krakend.py
│       ├── security_payloads.py
│       └── stateful/          # Testes stateful (fluxos)
```

**Principais diretórios e funções:**

- **output/**: Resultados gerados (relatórios, endpoints, testes).
- **src/analyzers/**: Scripts para análise de risco, PII e integração com LLM.
- **src/ast/**: Ferramentas para análise estática de código TypeScript.
- **src/generators/**: Geração automática de testes de segurança.
- **src/utils/**: Funções auxiliares, payloads e lógica de apoio.

## Instação e Configuração

### 1. Instale as dependências

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Adapte os arquivos JSON de configuração à sua API

- **auth_config.json**: Define regras de autenticação, headers fixos, tokens de roles e prefixos de autenticação usados nos testes automatizados. Permite customizar como cada teste irá autenticar na API.

- **pii_patterns.json**: Lista de padrões de campos considerados PII (informação pessoal sensível) para análise heurística e LLM. Exemplo:

  [
  "cpf",
  "cnpj",
  "email",
  "telefone",
  "celular",
  "nome",
  "documento"
  ]

  > Edite este arquivo para adaptar a detecção de PII ao seu domínio. O formato é um array JSON simples, sem comentários (limitação do padrão JSON).

- **outros arquivos .json em output/**: São artefatos gerados automaticamente (endpoints, relatórios, enriquecimento, etc). Não devem ser editados manualmente.

### 3. Configuração do arquivo .env

O arquivo `.env` centraliza variáveis de ambiente sensíveis e parâmetros de execução para o GTSA. Ele é carregado automaticamente pelos scripts Python do projeto (via python-dotenv).

**Principais variáveis suportadas:**

- `API_BASE_URL` – URL base da API a ser testada (ex: http://localhost, https://api.suaempresa.com)
- `ENDPOINT_PREFIX` – Prefixo dos endpoints da API (ex: /api, /api/v1)
- `AUTH_COOKIE_NAME` – Nome do cookie de autenticação, se aplicável
- `TOKEN_ADMIN_PRIMEIRO`, `TOKEN_GESTOR1`, ... – Tokens JWT para diferentes perfis de usuário (usados nos testes)
- `CHAVE_ACESSO_SISTEMA` – Chave de acesso do sistema, se necessário
- `LLM_BACKEND` – Backend LLM a ser usado (ex: gatiator, ollama)
- `LLM_BASE_URL` – URL do serviço LLM (ex: http://localhost:1313/v1/chat/completions)
- `LLM_MODEL` – Nome do modelo LLM (ex: codellama:7b, phi:2.7b)

**Exemplo de .env:**

```dotenv
API_BASE_URL=http://localhost
ENDPOINT_PREFIX=/api
AUTH_COOKIE_NAME=neosigner-auth
TOKEN_ADMIN_PRIMEIRO=eyJhbGciOi...
CHAVE_ACESSO_SISTEMA=...
LLM_BACKEND=gatiator
LLM_BASE_URL=http://localhost:1313/v1/chat/completions
LLM_MODEL=codellama:7b
```

> **Dicas:**
>
> - Não versionar o arquivo `.env` com segredos reais em repositórios públicos.
> - Sempre revise as variáveis antes de rodar testes em produção.
> - Variáveis de autenticação (tokens, cookies) podem ser usadas automaticamente pelos hooks de teste.

## Execução

### Passo 1: Faça o scan do projeto

O primeiro passo da análise estática é executar o scan do projeto TypeScript:

```bash
python3 src/ast/test_parser.py -i <caminho/para/o/projeto> [--parser ast_parser_node]
```

- Antes de iniciar, o script **limpa apenas os diretórios `output/ast/scan_*`** (removendo resultados de execuções anteriores), preservando outros arquivos em `output/ast`.
- Ele percorre todos os arquivos `.ts` e `.tsx` do projeto, ignora pastas de testes e dependências, e extrai todos os endpoints de API encontrados.
- Para cada arquivo analisado, gera um arquivo `.json` detalhado com os endpoints e um resumo da AST.
- Ao final, gera também:
  - `all_endpoints.json`: lista plana com todos os endpoints encontrados no projeto
  - `REPORT.md`: relatório em Markdown com resumo e tabela dos endpoints
  - `summary.json`: resumo da análise (quantidade de arquivos, endpoints, erros, etc)
  - `errors.log`: log de erros encontrados (se houver)
- Todos esses arquivos ficam em um diretório `output/ast/scan_<data-hora>/` exclusivo para cada execução.

**Para que serve essa saída?**

Esses arquivos servem como base para:

- Visualizar rapidamente todos os endpoints expostos pela API
- Mapear a superfície de ataque do sistema
- Alimentar as próximas etapas de geração e execução de testes de segurança
- Auditar mudanças e comparar execuções ao longo do tempo

### Passo 2: Geração Automática da Especificação da API (opcional)

Se você não possui uma documentação OpenAPI (openapi.json) oficial da sua API, pode gerar uma especificação automaticamente a partir do código-fonte usando o script `src/generators/node_openapi_generator.py`.

**Como funciona:**

- O script analisa o código do backend (ex: Node.js/TypeScript) e tenta extrair rotas, métodos e descrições para montar um arquivo `openapi.json` básico.
- É útil para projetos legados ou APIs sem documentação formal, acelerando a integração com o GTSA.

**Como usar:**

```bash
python3 src/generators/node_openapi_generator.py
```

> **Importante:**
>
> - Se sua API já possui um arquivo OpenAPI oficial, basta usá-lo diretamente nas etapas seguintes (não é necessário rodar este script).
> - A geração automática pode não capturar todos os detalhes (ex: exemplos, descrições, schemas complexos). Sempre revise e ajuste o arquivo gerado conforme necessário.

### Passo 3: Gere dados de exemplo para testes (opcional, recomendado)

O script `gerar_dados_exemplo.py` automatiza a criação de arquivos JSON com exemplos de payload para cada endpoint definido no seu OpenAPI. Esses arquivos são usados nos testes automatizados para garantir que cada rota seja exercitada com dados realistas e válidos.

**O que o script faz:**

- Para cada endpoint/método do OpenAPI, gera um arquivo em `output/tests/dados/{METHOD}_{endpoint}.json`.
- Prioriza exemplos já definidos no OpenAPI (`example` ou `examples`).
- Se não houver exemplo, gera dados automaticamente usando um modelo LLM (Ollama ou Gatiator), conforme configurado no `.env`.
- Salva parâmetros de path resolvidos no campo especial `_path_params` do JSON.

**Como usar:**

```bash
python src/generators/gerar_dados_exemplo.py <caminho/para/openapi.json>
```

**Principais opções:**

- `--llm-backend ollama|gatiator` — Define o backend LLM para geração automática de exemplos (default: valor do .env).
- `--llm-model <modelo>` — Define o modelo LLM a ser usado (ex: codellama:7b, phi:2.7b).
- `--only-with-body` — Gera arquivos apenas para endpoints que possuem requestBody.
- `--no-overwrite` — Não sobrescreve arquivos já existentes.

**Exemplo:**

```bash
python src/generators/gerar_dados_exemplo.py output/openapi.json --llm-backend ollama --llm-model llama3
```

**Saída:**

- Um arquivo JSON para cada endpoint/método em `output/tests/dados/`, pronto para ser usado nos testes.
- Cada arquivo contém um exemplo de payload realista, alinhado ao schema do endpoint.

> Recomenda-se rodar este passo sempre que atualizar o OpenAPI ou quiser garantir exemplos atualizados para os testes.

### Passo 4: Execute o parser AST apontando para o diretório do seu projeto TypeScript

```bash
python3 src/ast/parsers/ast_parser_node.py <caminho/para/o/projeto>
```

1. O script irá:
   - Percorrer todos os arquivos `.ts` e `.tsx` (exceto testes e node_modules)
   - Extrair endpoints de API (método, path, handler, parâmetros, linha, contexto)
   - Detectar se a rota exige autenticação ou é pública
   - Gerar relatórios detalhados em JSON e Markdown no diretório de saída, com nomes:
     - `endpoints_<data-hora>.json`: lista completa dos endpoints extraídos
     - `report_<data-hora>.md`: relatório em Markdown com resumo e tabela dos endpoints

2. Consulte os relatórios gerados em `output/ast/` para visualizar todos os endpoints e suas características.

> Esse processo é essencial para mapear a superfície de ataque da API antes de gerar e executar os testes dinâmicos.

### Passo 5: Análise de risco e enriquecimento dos endpoints (LLM ou heurística)

Após gerar o arquivo `all_endpoints.json`, é hora de enriquecer e analisar os endpoints para identificar riscos, dados sensíveis (PII) e possíveis vulnerabilidades. Isso pode ser feito de duas formas:

#### **A) Modo LLM (análise inteligente com IA) — recomendado**

Utiliza um modelo de linguagem (LLM) para analisar cada endpoint de forma mais contextualizada e inteligente.

**Comando:**

```bash
python src/analyzers/llm_analyzer.py output/ast/scan_YYYYMMDD_HHMMSS/all_endpoints.json
```

**Arquivos gerados:**

- `output/analysis_with_llm.json`: análise detalhada dos endpoints feita pelo LLM.
- `output/analysis_with_llm_report.md`: relatório em Markdown com estatísticas, riscos e vulnerabilidades.

#### **B) Modo heurístico (análise rápida, sem IA)**

Utiliza apenas regras fixas do script para analisar os endpoints. É mais rápido e não depende de modelo LLM, mas a análise é menos sofisticada.

**Comando:**

```bash
python src/analyzers/llm_analyzer.py output/ast/scan_YYYYMMDD_HHMMSS/all_endpoints.json --heuristic
```

**Arquivos gerados:**

- `output/analysis_heuristic.json`: análise heurística dos endpoints.
- `output/analysis_heuristic_report.md`: relatório em Markdown com estatísticas, riscos e vulnerabilidades.

#### **Resumo das diferenças**

| Modo         | Inteligência | Velocidade | Dependência de IA | Arquivos gerados             |
| ------------ | ------------ | ---------- | ----------------- | ---------------------------- |
| LLM (padrão) | Alta         | Média      | Sim               | analysis_with_llm.json, .md  |
| Heurístico   | Média        | Alta       | Não               | analysis_heuristic.json, .md |

> **Dica:** Use o modo heurístico para testes rápidos ou quando não quiser depender do modelo LLM. Para auditoria e análise mais profunda, prefira o modo LLM.

### Passo 6: Gerar enriched_endpoints.json

O arquivo `output/ast/enriched_endpoints.json` é gerado pelo script:

```bash
python3 src/ast/auto_enricher.py <openapi.json|yaml> --source <caminho/codigo>
```

- `<openapi.json|yaml>`: Caminho para o arquivo OpenAPI (JSON ou YAML) da API.
- `--output`: (opcional) Nome do arquivo de saída (por padrão, `enriched_endpoints.json` em `output/ast/`).
- `--source`: (opcional, atualmente ignorado) Caminho para o código-fonte da API.

**Arquivos gerados:**

- `output/ast/enriched_endpoints.json`: Lista de endpoints enriquecidos, com informações detalhadas extraídas do OpenAPI e enriquecidas por regras ou LLM (quando configurado).
- `output/ast/enrichment_report.json`: Relatório-resumo da etapa de enriquecimento, contendo estatísticas como total de endpoints, quantos foram enriquecidos com LLM e quantos possuem exemplos realistas.

**Para que servem:**

- O `enriched_endpoints.json` é a base para a geração de testes inteligentes, pois contém contexto de negócio, exemplos, regras e cenários de teste para cada endpoint.
- O `enrichment_report.json` permite auditar e acompanhar a qualidade do enriquecimento realizado, facilitando ajustes e validação do processo.

### Passo 7: Gerar testes inteligentes com smart_generator.py

Gere toda a estrutura de testes automatizados a partir do enriched_endpoints.json (sempre buscado automaticamente em output/ast/enriched_endpoints.json) e do seu arquivo OpenAPI:

```bash
python3 src/generators/smart_generator.py <caminho/para/openapi.json>
```

O script irá criar todos os arquivos necessários em `output/tests/`, incluindo:

- test_api_security.py (arquivo principal de testes)
- hooks/ (hooks de autenticação e manipulação de requests)
- run_llm_tests.sh (script automatizado para execução dos testes)

### Passo 8: Execute os testes gerados

Para rodar todos os testes automatizados, execute o script:

```bash
output/tests/run_llm_tests.sh
```

Esse script prepara o ambiente e executa o Pytest/Schemathesis, rodando:

- **Testes de segurança gerados automaticamente** (test_api_security.py e outros)
- **Testes stateful** (baseados em máquina de estados, localizados em `src/utils/stateful/`)

Os testes stateful, implementados com Hypothesis, simulam fluxos reais de uso da API, como sequências de criação, leitura, atualização e deleção de recursos, além de cenários de autenticação e manipulação de tokens. Eles ajudam a identificar bugs e falhas que só aparecem em interações complexas e sequenciais.

O resultado dos testes é exibido no terminal e também pode ser consultado nos arquivos de log gerados em `output/tests/`.

> **Dica:** Para rodar apenas os testes stateful, utilize:
>
> ```bash
> pytest src/utils/stateful/
> ```

## Saídas: Testes e Relatórios

O GTSA gera diversos arquivos e pastas durante o processo de análise, enriquecimento e execução de testes. Abaixo estão as principais saídas e seu propósito:

### output/ast/

- **scan\_\*/all_endpoints.json**: Lista plana de todos os endpoints encontrados no código-fonte.
- **scan*\*/endpoints*\*.json**: Endpoints extraídos por arquivo ou execução.
- **scan*\*/report*\*.md**: Relatório em Markdown com tabela de endpoints.
- **scan\_\*/summary.json**: Resumo da análise estática (quantidade de arquivos, endpoints, erros, etc).
- **scan\_\*/errors.log**: Log de erros encontrados durante o parsing.
- **enriched_endpoints.json**: Endpoints enriquecidos com contexto de negócio, exemplos e regras (base para geração de testes inteligentes).
- **enrichment_report.json**: Estatísticas e resumo do enriquecimento dos endpoints.

### output/

- **analysis_with_llm.json**: Resultado da análise de risco e PII usando LLM.
- **analysis_with_llm_report.md**: Relatório em Markdown da análise LLM.
- **analysis_heuristic_report.md**: Relatório de análise heurística (sem LLM).
- **analysis_heuristic_report.json**: Resultado da análise heurística em JSON.
- **openapi.json / openapi.yaml**: Especificação OpenAPI gerada ou fornecida, usada como base para os testes.

### output/tests/

- **test_api_security.py**: Arquivo principal de testes gerado automaticamente (Pytest/Schemathesis).
- **hooks/**: Hooks de autenticação e manipulação de requests para os testes.
- **run_llm_tests.sh**: Script para execução automatizada dos testes.

> Todos os arquivos em `output/` podem ser versionados para auditoria.
