# GTSA – Gerador de Testes de Segurança para APIs

## Visão Geral

O GTSA é uma ferramenta automatizada para análise, geração e execução de testes de segurança em APIs REST, com integração opcional a LLMs (Modelos de Linguagem) para geração inteligente de dados de teste e análise de riscos.

- **Geração de testes baseada em OpenAPI**
- **Análise heurística e via LLM dos endpoints**
- **Execução automatizada com Pytest**
- **Relatórios de riscos, PII e vulnerabilidades**
- **Suporte a autenticação (token, cookies, headers)**

## Estrutura do Projeto

```
gtsa/
├── README.md                        # Documentação principal
├── requirements.txt                 # Dependências Python
├── pytest.ini                       # Configuração de testes
├── orquestrador.sh                  # Orquestrador da pipeline completa
├── config/                          # Configurações declarativas
│   ├── auth_config.json             # Regras de autenticação e tokens por role
│   └── pii_patterns.json            # Padrões de campos PII
├── output/                          # Artefatos gerados pela pipeline
│   ├── openapi.json / openapi.yaml  # Especificação OpenAPI
│   ├── enriched_endpoints.json      # Endpoints enriquecidos (base dos testes)
│   ├── enrichment_report.json       # Relatório do enriquecimento
│   ├── analysis_with_llm.json       # Análise de risco via LLM
│   ├── analysis_with_llm_report.md  # Relatório da análise LLM
│   ├── analises/                    # Resultados de análise de risco e enriquecimento (sempre sobrescritos)
│   ├── scan_<data-hora>/            # Resultados do scan estático por execução
│   │   ├── all_endpoints.json
│   │   ├── REPORT.md
│   │   └── summary.json
│   └── tests/                       # Testes gerados automaticamente
│       ├── test_api_security.py
│       ├── run_llm_tests.sh
│       ├── test_api_llm.log
│       ├── test_api_llm_summary.md
│       └── dados/                   # Payloads de exemplo por endpoint
└── src/                             # Código-fonte principal
    ├── application/
    │   ├── pipeline/                # Um módulo por etapa da pipeline
    │   │   ├── step1_scan.py
    │   │   ├── step2_openapi.py
    │   │   ├── step3_dados_exemplo.py
    │   │   ├── step4_ast_parser.py
    │   │   ├── step5_analyzer.py
    │   │   ├── step6_enricher.py
    │   │   └── step7_generator.py
    │   └── reporting/
    │       └── gerar_relatorio_markdown.py
    ├── domain/
    │   └── security_payloads.py     # Payloads e regras de segurança
    ├── infrastructure/
    │   ├── generators/
    │   │   ├── gerar_dados_exemplo.py
    │   │   ├── node_openapi_generator.py
    │   │   └── smart_generator.py
    │   ├── llm/
    │   │   └── llm_analyzer.py
    │   └── parsers/
    │       ├── ast_parser_node.py
    │       └── test_parser.py
    └── interfaces/
        ├── hooks/                   # Hooks de autenticação para os testes
        │   ├── auth_hooks.py
        │   └── llm_hooks.py
        └── stateful/                # Testes stateful baseados em Hypothesis
            ├── api_state_machine.py
            └── test_stateful_api.py
```

**Principais diretórios e funções:**

- **config/**: Configurações declarativas de autenticação e padrões PII. Devem ser adaptados para cada API testada.
- **output/**: Todos os artefatos gerados pela pipeline. Podem ser versionados para auditoria.
- **src/application/pipeline/**: Scripts de orquestração de cada etapa da pipeline (steps 1–7).
- **src/application/reporting/**: Geração do relatório Markdown a partir do log de testes.
- **src/infrastructure/generators/**: Geração de dados de exemplo, OpenAPI e testes inteligentes.
- **src/infrastructure/parsers/**: Parsers de AST e extração de endpoints do código TypeScript.
- **src/infrastructure/llm/**: Integração com modelos de linguagem para análise de risco e PII.
- **src/domain/**: Payloads e regras de segurança reutilizáveis.
- **src/interfaces/hooks/**: Hooks de autenticação usados pelos testes gerados.
- **src/interfaces/stateful/**: Testes stateful que simulam fluxos reais de uso da API.

## Instalação e Configuração

### 1. Instale as dependências

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Adapte os arquivos de configuração à sua API

- **config/auth_config.json**: Define regras de autenticação, headers fixos, tokens por role e prefixos usados nos testes. Permite customizar como cada teste autentica na API.

- **config/pii_patterns.json**: Lista de padrões de campos considerados PII (informação pessoal sensível). Exemplo:

  ```json
  ["cpf", "cnpj", "email", "telefone", "celular", "nome", "documento"]
  ```

  > Edite este arquivo para adaptar a detecção de PII ao seu domínio.

- **Arquivos em output/**: São artefatos gerados automaticamente. Não devem ser editados manualmente.

### 3. Configuração do arquivo .env

O arquivo `.env` centraliza variáveis de ambiente sensíveis e parâmetros de execução. É carregado automaticamente pelos scripts Python via `python-dotenv`.

**Principais variáveis:**

- `API_BASE_URL` – URL base da API (ex: `http://localhost`, `https://api.suaempresa.com`)
- `ENDPOINT_PREFIX` – Prefixo dos endpoints (ex: `/api`, `/api/v1`)
- `AUTH_COOKIE_NAME` – Nome do cookie de autenticação, se aplicável
- `TOKEN_REQ`, `TOKEN_GES`, `TOKEN_ADM`, ... – Tokens JWT por perfil de usuário
- `CHAVE_ACESSO_SISTEMA` – Chave de acesso do sistema, se necessário
- `LLM_BACKEND` – Backend LLM (ex: `gatiator`, `ollama`)
- `LLM_BASE_URL` – URL do serviço LLM (ex: `http://localhost:1313/v1/chat/completions`)
- `LLM_MODEL` – Modelo LLM (ex: `codellama:7b`, `phi:2.7b`)

**Exemplo de .env:**

```dotenv
API_BASE_URL=http://localhost
ENDPOINT_PREFIX=/api
AUTH_COOKIE_NAME=neosigner-auth
TOKEN_REQ=eyJhbGciOi...
TOKEN_GES=eyJhbGciOi...
TOKEN_ADM=eyJhbGciOi...
CHAVE_ACESSO_SISTEMA=...
LLM_BACKEND=gatiator
LLM_BASE_URL=http://localhost:1313/v1/chat/completions
LLM_MODEL=codellama:7b
```

> **Dicas:**
>
> - Não versione o `.env` com segredos reais em repositórios públicos.
> - Sempre revise as variáveis antes de rodar testes em produção.

## Execução

### Passo 1: Scan estático do projeto

Executa a análise estática do código TypeScript para extrair todos os endpoints:

```bash
python3 src/infrastructure/parsers/test_parser.py -i <caminho/para/o/projeto>
```

- Percorre todos os arquivos `.ts` e `.tsx`, ignorando testes e `node_modules`.
- Gera um diretório `output/scan_<data-hora>/` com:
  - `all_endpoints.json`: lista plana de todos os endpoints encontrados
  - `REPORT.md`: relatório em Markdown com tabela de endpoints
  - `summary.json`: resumo da análise (arquivos, endpoints, erros)
  - `errors.log`: log de erros, se houver

**Para que serve:** mapear a superfície de ataque e alimentar as etapas seguintes.

### Passo 2: Geração automática do OpenAPI (opcional)

Se a API não possui documentação OpenAPI oficial, gere uma especificação básica a partir do código-fonte:

```bash
python3 src/infrastructure/generators/node_openapi_generator.py
```

> Se sua API já possui um OpenAPI oficial, pule este passo e use-o diretamente nas etapas seguintes.

### Passo 3: Geração de dados de exemplo (opcional, recomendado)

Gera payloads JSON realistas para cada endpoint, usados nos testes automatizados:

```bash
python3 src/infrastructure/generators/gerar_dados_exemplo.py <caminho/para/openapi.json>
```

**Principais opções:**

- `--llm-backend ollama|gatiator` — Backend LLM para geração automática (default: valor do `.env`)
- `--llm-model <modelo>` — Modelo LLM a usar (ex: `codellama:7b`)
- `--only-with-body` — Gera apenas para endpoints com `requestBody`
- `--no-overwrite` — Não sobrescreve arquivos já existentes

**Saída:** um arquivo JSON por endpoint em `output/tests/dados/`, pronto para uso nos testes.

> Recomenda-se rodar sempre que o OpenAPI for atualizado.

### Passo 4: Parser AST detalhado

Extrai endpoints com contexto detalhado (handler, parâmetros, autenticação):

```bash
python3 src/application/pipeline/step4_ast_parser.py <caminho/para/o/projeto>
```

Gera em `output/`:

- `regular_endpoints.json`: lista completa dos endpoints extraídos (sempre sobrescrito)
- `regular_endpoints_report.md`: relatório em Markdown (sempre sobrescrito)

### Passo 5: Análise de risco e PII

Analisa os endpoints para identificar riscos, dados sensíveis (PII) e possíveis vulnerabilidades, utilizando LLM local (Ollama ou Gatiator) ou heurística.

#### Execução (LLM ou heurística)

```bash
python3 src/application/pipeline/step5_analyzer.py output/scan_<data-hora>/all_endpoints.json [opções]
```

Principais opções:

- `--llm-backend gatiator|ollama|none` — Backend LLM a ser usado (default: valor do .env)
- `--llm-model <modelo>` — Modelo LLM (ex: codellama:7b)
- `--llm-url <url>` — URL customizada do backend LLM
- `--no-llm` — Usa apenas heurística, sem IA
- `--dry-run` — Executa sem gravar arquivos de saída

**O script limpa automaticamente o diretório `output/analises/` antes de cada execução (exceto se usar `--dry-run`). Todos os arquivos de saída são gravados diretamente em `output/analises/`.**

Saídas geradas em `output/analises/`:

- `enriched_endpoints.json`: endpoints enriquecidos com análise de risco, PII, vulnerabilidades e contexto de negócio
- `enriched_endpoints_report.md`: relatório detalhado em Markdown

| Modo         | Inteligência | Velocidade | Dependência de IA |
| ------------ | ------------ | ---------- | ----------------- |
| LLM (padrão) | Alta         | Média      | Sim               |
| Heurístico   | Média        | Alta       | Não               |

### Passo 6: Enriquecimento dos endpoints

Gera o `enriched_endpoints.json` que serve de base para a geração de testes inteligentes:

```bash
python3 src/infrastructure/parsers/ast_parser_node.py <openapi.json|yaml> --source <caminho/codigo>
```

Gera em `output/`:

- `enriched_endpoints.json`: endpoints com contexto de negócio, exemplos e regras
- `enrichment_report.json`: estatísticas do enriquecimento

### Passo 7: Geração dos testes inteligentes

Gera toda a estrutura de testes a partir do `enriched_endpoints.json` e do OpenAPI:

```bash
python3 src/infrastructure/generators/smart_generator.py <caminho/para/openapi.json>
```

Cria em `output/tests/`:

- `test_api_security.py`: script principal de testes
- `run_llm_tests.sh`: script de execução automatizada
- (os hooks são lidos de `src/interfaces/hooks/`)

### Passo 8: Execução dos testes

```bash
output/tests/run_llm_tests.sh
```

O script executa `test_api_security.py` para cada endpoint em paralelo (até 4 simultâneos), rodando os seguintes testes por endpoint:

- **test_specific_data**: com payload real do arquivo `output/tests/dados/`
- **test_basic**: com dados mínimos gerados a partir do schema
- **test_property_based**: testes baseados em propriedades com Hypothesis
- **test_multiple_examples**: múltiplos exemplos aleatórios
- **test_response_schema**: valida a resposta contra o schema OpenAPI
- **test_endpoint_without_body**: para endpoints GET/DELETE sem body

Após a execução, gere o relatório:

```bash
python3 src/application/reporting/gerar_relatorio_markdown.py
```

O relatório é salvo em `output/tests/test_api_llm_summary.md`.

> Para rodar apenas os testes stateful:
>
> ```bash
> pytest src/interfaces/stateful/
> ```

## Saídas: Testes e Relatórios

### output/scan\_<data-hora>/

### output/

| Arquivo                       | Descrição                                                     |
| ----------------------------- | ------------------------------------------------------------- |
| `regular_endpoints.json`      | Lista completa dos endpoints extraídos pelo parser AST        |
| `regular_endpoints_report.md` | Relatório em Markdown dos endpoints extraídos pelo parser AST |
| ...                           | ...                                                           |

### output/analises/analise\_<data-hora>/

| Arquivo                        | Descrição                                                   |
| ------------------------------ | ----------------------------------------------------------- |
| `enriched_endpoints.json`      | Endpoints enriquecidos (sempre sobrescrito a cada execução) |
| `enriched_endpoints_report.md` | Relatório detalhado da análise (sempre sobrescrito)         |

### output/

| Arquivo                        | Descrição                                                               |
| ------------------------------ | ----------------------------------------------------------------------- |
| `enriched_endpoints.json`      | Última análise de risco e enriquecimento (gerado por step5_analyzer.py) |
| `enriched_endpoints_report.md` | Último relatório detalhado da análise (gerado por step5_analyzer.py)    |
| `enrichment_report.json`       | Estatísticas do enriquecimento (gerado por outros scripts)              |
| `analysis_with_llm.json`       | Análise LLM mais recente (legado)                                       |
| `analysis_with_llm_report.md`  | Relatório da análise LLM (legado)                                       |
| `openapi.json / openapi.yaml`  | Especificação OpenAPI usada como base                                   |

### output/tests/

| Arquivo                   | Descrição                               |
| ------------------------- | --------------------------------------- |
| `test_api_security.py`    | Script de testes gerado automaticamente |
| `run_llm_tests.sh`        | Script de execução dos testes           |
| `test_api_llm.log`        | Log detalhado da execução               |
| `test_api_llm_summary.md` | Relatório consolidado por endpoint      |
| `dados/`                  | Payloads de exemplo por endpoint        |

> Todos os arquivos em `output/` podem ser versionados para auditoria e rastreabilidade.
