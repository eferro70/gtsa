# GTSA - Gerador de Testes de Segurança de APIs

Este projeto executa uma pipeline automatizada para análise de segurança de APIs, gerando relatórios detalhados sobre potenciais riscos, exemplos de dados, enriquecimento de informações e testes automatizados com LLMs. O objetivo é facilitar a avaliação de segurança de APIs REST a partir de definições OpenAPI e exemplos reais de uso.

## Estrutura do Projeto

- **src/application/pipeline/**: Contém os passos da pipeline de análise.
- **src/application/pipeline/tests/**: Dados de teste e arquivos de apoio para validação.
- **output/**: Relatórios e resultados finais da análise.
- **config/**: Configurações de autenticação e padrões de PII.
- **orquestrador.sh**: Script principal para execução da pipeline.

## Sequência da Pipeline

---

### 1: step1_scan.py

**Descrição:**
Analisa recursivamente o código-fonte Node/TypeScript, extraindo endpoints de APIs a partir dos arquivos .ts/.tsx usando parser AST.

**Entradas:**

- Diretório raiz do projeto Node/TypeScript (`-i <caminho>`)
- (Opcional) Nome do parser AST (`--parser`)

**Saídas:**

- `all_endpoints.json` (lista de endpoints extraídos)
- Relatórios JSON/Markdown (resumo, erros, AST)

---

### 2: step2_openapi.py

**Descrição:**
Gera um schema OpenAPI 3.0 automaticamente a partir do arquivo `all_endpoints.json`.

**Entradas:**

- `all_endpoints.json` (gerado pelo passo anterior)
- (Opcional) Título, versão e prefixo dos endpoints

**Saídas:**

- `output/openapi.json` (schema OpenAPI)
- `output/openapi.yaml` (se PyYAML instalado)
- `output/report.md` (relatório dos endpoints)

---

### 3: step3_dados_exemplo.py

**Descrição:**
Gera exemplos de dados para cada endpoint definido no OpenAPI, priorizando exemplos inline e gerando via LLM se necessário.

**Entradas:**

- `output/openapi.json`
- (Opcional) parâmetros para backend/modelo LLM

**Saídas:**

- `src/application/pipeline/tests/dados/METHOD_endpoint.json` (exemplo para cada endpoint)

---

### 4: step4_ast_parser.py

**Descrição:**
Analisa o código-fonte Node/TypeScript usando tree-sitter para extrair endpoints, métodos e parâmetros.

**Entradas:**

- Diretório do projeto Node/TypeScript
- (Opcional) diretório de saída

**Saídas:**

- `src/application/pipeline/tests/regular_endpoints.json`
- `output/api_analyse_report.md`

---

### 5: step5_analyzer_and_enricher.py

**Descrição:**
**Script** que combina análise de segurança com enriquecimento de dados. Analisa riscos usando modo híbrido (LLM + Heurística) com fallback inteligente, identifica dados sensíveis (PII), detecta vulnerabilidades de segurança e mapeia automaticamente para **OWASP API Top 10 2023** e **SANS Top 25**. Além disso, enriquece os endpoints com dados do OpenAPI, exemplos reais de requisição e roles de autorização do KrakenD.

**Funcionalidades:**

- 🔄 **Modo Híbrido**: Tenta usar LLM local (Ollama/Gatiator) com fallback para heurística
- 🛡️ **OWASP API Top 10 2023**: Mapeamento automático de vulnerabilidades específicas de APIs
- 📊 **SANS Top 25**: Classificação e ranqueamento de vulnerabilidades
- 🔍 **Detecção de 10+ vulnerabilidades**: BOLA, BFLA, Injection, SSRF, Broken Auth, Mass Assignment, Security Misconfiguration, Rate Limiting, XXE, Open Redirect, Unsafe Consumption
- 📝 **Identificação de PII**: CPF, CNPJ, email, telefone, etc.
- 📄 **Enriquecimento OpenAPI**: Adiciona summary, description e schemas
- 🔑 **Roles de autorização**: Extrai roles do arquivo de configuração do KrakenD
- 📦 **Exemplos reais**: Busca exemplos de requisição em `output/tests/dados/`
- ⚡ **Determinístico**: Mapeamento OWASP/SANS 100% heurístico (sem LLM)

**Entradas:**

- `all_endpoints.json` (gerado pelo step4)
- (Opcional) Arquivo OpenAPI (`--openapi`) para enriquecimento
- (Opcional) Parâmetros de backend/modelo LLM

**Saídas:**

- `src/application/pipeline/tests/enriched_endpoints.json` (endpoint enriquecido com segurança + dados)
- `output/final_security_report.md` (relatório detalhado OWASP/SANS)

bash
bash

---

### 6: step6_generator.py

**Descrição:**
Gera automaticamente arquivos de teste para APIs REST a partir da especificação OpenAPI e endpoints enriquecidos. Cria testes Python (Schemathesis/Hypothesis) com verificações avançadas de segurança, incluindo testes específicos por vulnerabilidade, verificação de vazamento de PII e validação de autorização.

**Funcionalidades:**

- 🔒 Testes específicos por vulnerabilidade: BOLA, BFLA, etc.
- 🛡️ Verificação de vazamento de PII: Detecta exposição de dados sensíveis
- 📊 Contexto de segurança: Utiliza risk_level, vulnerabilities do enriched_endpoints.json
- 🔑 Hooks de autenticação: Suporte a roles e tokens JWT
- 🚀 Runner Bash otimizado: Com filtros por nível de risco e execução paralela

**Entradas:**

- `output/openapi.json` (especificação OpenAPI)
- `src/application/pipeline/tests/enriched_endpoints.json` (endpoints enriquecidos)

**Saídas:**

- `src/application/pipeline/tests/test_api_security.py` (testes Python)
- `src/application/pipeline/step7_run_llm_tests.sh` (runner Bash)
- `src/infrastructure/interfaces/hooks/__init__.py`
- `src/infrastructure/interfaces/hooks/auth_hooks.py`
- `src/infrastructure/interfaces/hooks/llm_hooks.py`

**Exemplo de uso:**

```bash
python3 step6_generator.py output/openapi.json
```

---

### 7: step7_run_llm_tests.sh

**Descrição:**
Executa testes automatizados de segurança com LLMs, gerando logs e sumário dos resultados. Suporta filtros avançados para priorizar endpoints críticos.

**Funcionalidades:**

- 🔴 Filtro por nível de risco: `ONLY_HIGH_RISK=true` (testa apenas endpoints de alto risco)
- 📊 Filtro por score de risco: `MAX_RISK_SCORE=0.7` (testa endpoints com score <= 0.7)
- ⏭️ Pular endpoints sem autenticação: `SKIP_NO_AUTH=true`
- 🔄 Execução paralela: Configurável via `PARALLEL_JOBS`
- 📈 Relatório detalhado: Inclui vulnerabilidades detectadas e status dos testes

**Entradas:**

- `src/application/pipeline/tests/enriched_endpoints.json`
- `src/application/pipeline/tests/test_api_security.py`
- Configurações de autenticação (`config/auth_config.json`)
- Variáveis de ambiente (`.env`)

**Saídas:**

- `output/test_api_llm_summary.md` (relatório de testes)
- `llm_analyzer.log` (log detalhado)

**Exemplo de uso:**

```bash
# Testar apenas endpoints de alto risco
ONLY_HIGH_RISK=true ./src/application/pipeline/step7_run_llm_tests.sh

# Testar com score máximo 0.7 e 2 jobs paralelos
MAX_RISK_SCORE=0.7 PARALLEL_JOBS=2 ./src/application/pipeline/step7_run_llm_tests.sh

# Teste completo (todos endpoints)
./src/application/pipeline/step7_run_llm_tests.sh
```

---

### 8: step8_gerar_relatorio_markdown.py

**Descrição:**
Gera relatório final em Markdown consolidando os resultados dos testes de segurança da API executados.

**Entradas:**

- `llm_analyzer.log` (log gerado pelo step7)

**Saídas:**

- `output/test_api_llm_summary.md` (relatório consolidado)

Saídas e Relatórios (output/)
A pasta output/ contém os principais resultados da pipeline:

**api_analyse_report.md**: Relatório detalhado da análise de segurança da API, incluindo endpoints, riscos identificados, recomendações e evidências.

**final_security_report.md**: Relatório final consolidado com OWASP API Top 10 2023 e SANS Top 25, pronto para apresentação ou auditoria.

**test_api_llm_summary.md**: Sumário dos testes automatizados realizados, destacando falhas, comportamentos suspeitos e sugestões de mitigação.

## Como Executar

Crie e ative um ambiente virtual (recomendado):

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Configure as variáveis de ambiente no arquivo .env:

```bash
# Tokens para cada role (para testes)
TOKEN_ADMINISTRADOR="eyJhbGciOiJIUzI1NiIs..."
TOKEN_GESTOR="eyJhbGciOiJIUzI1NiIs..."
TOKEN_REQUISITANTE="eyJhbGciOiJIUzI1NiIs..."
TOKEN_INTERESSADO="eyJhbGciOiJIUzI1NiIs..."
# URL base da API
API_BASE_URL="http://localhost:8080"
```

Configure a autenticação no arquivo config/auth_config.json:

```json
{
  "fixed_headers": [],
  "role_tokens": {
    "ADMINISTRADOR": { "env_var": "TOKEN_ADMINISTRADOR" },
    "GESTOR": { "env_var": "TOKEN_GESTOR" },
    "REQUISITANTE": { "env_var": "TOKEN_REQUISITANTE" },
    "INTERESSADO": { "env_var": "TOKEN_INTERESSADO" }
  },
  "default_role": "REQUISITANTE",
  "auth_header": "Authorization",
  "auth_prefix": "Bearer "
}
```

Execute o orquestrador:

```bash
bash orquestrador.sh
```

Os relatórios serão gerados na pasta output/.

## Configurações

- Ajuste arquivos em config/ conforme necessário para autenticação e padrões de dados sensíveis.
- O mapeamento de vulnerabilidades OWASP API Top 10 2023 pode ser customizado em config/vulnerability_mapping.json.
- Os dados de teste podem ser customizados em src/application/pipeline/tests/dados/.

## Observações

- A pipeline é modular: cada etapa pode ser executada individualmente para depuração.
- Os arquivos intermediários (JSON) são salvos em subpastas de tests/ para rastreabilidade.
- O projeto é extensível para novos tipos de análise ou integrações com outros sistemas de segurança.
