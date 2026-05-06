# GTSA - Gerador de Testes de Segurança de APIs

Este projeto executa uma pipeline automatizada para análise de segurança de APIs, gerando relatórios detalhados sobre potenciais riscos, exemplos de dados, enriquecimento de informações e testes automatizados com LLMs. O objetivo é facilitar a avaliação de segurança de APIs REST a partir de código-fonte ou especificações OpenAPI.

## Início Rápido

```bash
# 1. Configurar variáveis de ambiente (opcional)
# Editar .env para habilitar/desabilitar passos opcionais
nano .env

# 2. Executar a pipeline completa
./orquestrador.sh
```

## Estrutura do Projeto

```
gtsa/
├── orquestrador.sh                 # Script principal da pipeline
├── .env                            # Configuração de passos opcionais
├── README.md                       # Este arquivo
├── requirements.txt                # Dependências Python
├── config/                         # Configurações
│   ├── auth_config.json           # Configurações de autenticação
│   ├── pii_patterns.json          # Padrões de detecção de dados sensíveis
│   └── vulnerability_mapping.json # Mapeamento de vulnerabilidades
├── output/                         # Artefatos gerados
│   ├── openapi.json               # Especificação OpenAPI gerada
│   ├── openapi.yaml               # Especificação OpenAPI (YAML)
│   ├── openapi.json-report.md     # Relatório dos endpoints OpenAPI
│   ├── final_security_report.md   # Relatório detalhado de segurança
│   └── test_api_llm_summary.md    # Sumário dos testes executados
└── src/
    ├── application/pipeline/       # Scripts da pipeline
    │   ├── step1_scan.py          # Scan AST do código-fonte
    │   ├── step2_openapi.py       # Geração OpenAPI (opcional)
    │   ├── step3_dados_exemplo.py # Dados de exemplo (opcional)
    │   ├── step4_analyzer_and_enricher.py  # Análise de segurança
    │   ├── step5_generator.py     # Gerador de testes
    │   ├── step6_run_llm_tests.sh # Executor de testes com LLM
    │   ├── step7_gerar_relatorio_markdown.py # Gerador de relatório
    │   └── tests/
    │       ├── dados/             # Exemplos de dados gerados
    │       └── scan_*/            # Resultados dos scans
    └── infrastructure/            # Utilitários e hooks
        └── interfaces/
            └── hooks/             # Hooks de autenticação e LLM
```

## Configuração

### Variáveis de Ambiente (`.env`)

```bash
# Controle dos passos opcionais
STEP_2_ENABLED=false      # Gerar OpenAPI (true/false)
STEP_3_ENABLED=false      # Gerar dados de exemplo (true/false)

# Configurações LLM
LLM_BACKEND=ollama        # Backend LLM (ollama, gatiator, etc)
LLM_MODEL=gemma          # Modelo LLM a usar
```

## Pipeline de Execução

### Passo 1: Scan AST do Código-Fonte

```bash
python3 src/application/pipeline/step1_scan.py -i <caminho_projeto>
```

**Descrição**: Analisa recursivamente o código-fonte (Node/TypeScript/Python), extraindo endpoints de APIs usando parser AST.

**Entradas**:

- Diretório raiz do projeto (`-i`)
- (Opcional) Tipo de parser (`--parser`)

**Saídas**:

- `src/application/pipeline/tests/scan_<timestamp>/all_endpoints.json`
- Relatórios JSON/Markdown

---

### Passo 2: Geração OpenAPI (Opcional)

```bash
python3 src/application/pipeline/step2_openapi.py
```

**Descrição**: Gera especificação OpenAPI 3.0 a partir dos endpoints extraídos.

**Dependências**: Passo 1 deve ter executado antes

**Controle**: `STEP_2_ENABLED=true` no `.env`

**Saídas**:

- `output/openapi.json`
- `output/openapi.yaml` (se PyYAML instalado)
- `output/openapi.json-report.md`

---

### Passo 3: Dados de Exemplo (Opcional)

```bash
python3 src/application/pipeline/step3_dados_exemplo.py <openapi.json>
```

**Descrição**: Gera exemplos de dados para cada endpoint (body, path params).

**Dependências**: OpenAPI deve existir

**Controle**: `STEP_3_ENABLED=true` no `.env`

**Prioridade de exemplo**:

1. Exemplo inline no requestBody → usa diretamente
2. Mapa de exemplos → pega o primeiro
3. Exemplo no schema `$ref` → usa diretamente
4. Fallback: gera via LLM

**Saídas**:

- `src/application/pipeline/tests/dados/METHOD_endpoint.json`

---

### Passo 4: Análise de Segurança

```bash
python3 src/application/pipeline/step4_analyzer_and_enricher.py <all_endpoints.json>
```

**Descrição**: Análise de risco com enriquecimento de dados. Detecta vulnerabilidades, identifica PII e mapeia para OWASP API Top 10 2023 e SANS Top 25.

**Funcionalidades**:

- 🔄 **Modo Híbrido**: LLM local com fallback para heurística
- 🛡️ **OWASP API Top 10 2023**: Mapeamento automático
- 📊 **SANS Top 25**: Classificação de vulnerabilidades
- 🔍 **10+ vulnerabilidades**: BOLA, BFLA, Injection, SSRF, etc
- 📝 **Detecção PII**: CPF, CNPJ, email, telefone
- ⚡ **Determinístico**: Mapeamento 100% heurístico

**Entradas**:

- `all_endpoints.json` (Passo 1)
- (Opcional) OpenAPI (`--openapi`)
- (Opcional) parâmetros LLM

**Saídas**:

- `src/application/pipeline/tests/enriched_endpoints.json`
- `output/final_security_report.md`

---

### Passo 5: Gerador de Testes

```bash
python3 src/application/pipeline/step5_generator.py <openapi.json>
```

**Descrição**: Gera testes Python automaticamente com verificações de segurança avançadas.

**Funcionalidades**:

- 🔒 Testes específicos por vulnerabilidade
- 🛡️ Verificação de vazamento de PII
- 📊 Contexto de segurança por endpoint
- 🔑 Hooks de autenticação e roles
- 🚀 Runner Bash otimizado com filtros

**Entradas**:

- `output/openapi.json`
- `src/application/pipeline/tests/enriched_endpoints.json`

**Saídas**:

- `src/application/pipeline/tests/test_api_security.py`
- `src/application/pipeline/step6_run_llm_tests.sh`
- Hooks de autenticação em `src/infrastructure/interfaces/hooks/`

---

### Passo 6: Execução de Testes com LLM

```bash
bash src/application/pipeline/step6_run_llm_tests.sh \
  --llm-backend ollama \
  --llm-model gemma
```

**Descrição**: Executa testes de segurança com LLMs, gerando sumário dos resultados.

**Funcionalidades**:

- 🔴 Filtro por nível de risco: `ONLY_HIGH_RISK=true`
- 📊 Filtro por score: `MAX_RISK_SCORE=0.7`
- ⏭️ Pular endpoints sem auth: `SKIP_NO_AUTH=true`
- 🔄 Execução paralela: `PARALLEL_JOBS=2`

**Entradas**:

- `src/application/pipeline/tests/enriched_endpoints.json`
- `src/application/pipeline/tests/test_api_security.py`
- `config/auth_config.json`

**Saídas**:

- `llm_analyzer.log` (log detalhado)
- Sumário integrado ao relatório final

---

### Passo 7: Geração de Relatório Final

```bash
python3 src/application/pipeline/step7_gerar_relatorio_markdown.py
```

**Descrição**: Consolida resultados de todos os passos em relatório final em Markdown.

**Entradas**:

- `llm_analyzer.log`
- `output/final_security_report.md`
- Resultados dos testes

**Saídas**:

- `output/test_api_llm_summary.md`

---

## Exemplos de Uso

### Execução Completa da Pipeline

```bash
./orquestrador.sh
```

Log será salvo em `orquestrador.log` e os artefatos em `output/` e `src/application/pipeline/tests/`.

### Pular Passos Opcionais

```bash
# Editar .env
STEP_2_ENABLED=false
STEP_3_ENABLED=false

./orquestrador.sh
```

### Teste com Apenas Endpoints de Alto Risco

```bash
ONLY_HIGH_RISK=true ./src/application/pipeline/step6_run_llm_tests.sh
```

### Teste com Score Máximo e Jobs Paralelos

```bash
MAX_RISK_SCORE=0.7 PARALLEL_JOBS=2 ./src/application/pipeline/step6_run_llm_tests.sh
```

## Fluxo de Dados

```
Código-Fonte
    ↓ (Passo 1: Scan AST)
all_endpoints.json
    ↓
    ├─→ (Passo 2 - opcional) → openapi.json ──┐
    │                                          ↓
    │                          (Passo 3 - opcional) → dados/
    │                                          ↑
    └─────────────────────────────────────────┘
                    ↓
    (Passo 4: Análise) → enriched_endpoints.json
                    ↓
    (Passo 5: Gerador) → test_api_security.py
                    ↓
    (Passo 6: Testes) → llm_analyzer.log
                    ↓
    (Passo 7: Relatório) → test_api_llm_summary.md
```

## Artefatos Gerados

### Em `output/`

- `openapi.json` - Especificação OpenAPI
- `openapi.yaml` - Especificação em YAML
- `openapi.json-report.md` - Relatório dos endpoints
- `final_security_report.md` - Análise detalhada de segurança
- `test_api_llm_summary.md` - Sumário final dos testes

### Em `src/application/pipeline/tests/`

- `scan_<timestamp>/` - Resultados do scan AST
- `dados/` - Exemplos de dados gerados
- `enriched_endpoints.json` - Endpoints com análise de segurança
- `test_api_security.py` - Testes executáveis
- `test_api_llm_summary.md` - Resultados dos testes

## Requisitos

- Python 3.8+
- Bash 4.0+
- (Opcional) Ollama ou Gatiator para LLM local
- Dependências Python: `pip install -r requirements.txt`

## Instalação

```bash
# Clonar e instalar
git clone <repo>
cd gtsa

# Criar ambiente virtual
python3 -m venv .venv
source .venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Configurar (se necessário)
cp .env.example .env
nano .env
```

## Suporte

Consulte os logs para detalhes:

- `orquestrador.log` - Execução geral da pipeline
- `llm_analyzer.log` - Detalhes dos testes com LLM
- `output/` - Relatórios finais

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
