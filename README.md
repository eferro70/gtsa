# GTSA — Gerador de Testes de Segurança de APIs

O GTSA executa uma pipeline automatizada de análise de segurança de APIs REST. A partir do
código-fonte de um projeto (ou de uma especificação OpenAPI), ele extrai endpoints, enriquece a
especificação, avalia riscos (OWASP API Top 10 2023 / SANS Top 25), executa testes com
[Schemathesis](https://schemathesis.readthedocs.io/) e consolida tudo em relatórios Markdown.

O projeto segue **Clean Architecture** com _src layout_: as regras de negócio ficam isoladas em
`domain`/`application`, e a `infrastructure` implementa as portas (interfaces) definidas pelo
domínio. As interfaces de linha de comando (`interfaces/cli`) apenas orquestram os casos de uso.

## Início Rápido

```bash
# 1. Criar e ativar o ambiente virtual
python3 -m venv .venv
source .venv/bin/activate

# 2. Instalar o pacote (modo editável) com as dependências
pip install -e .

# 3. Criar o arquivo de ambiente da API alvo (ex.: neosigner)
#    Veja a seção "Configuração" para as variáveis obrigatórias
nano .env.neosigner

# 4. Executar a pipeline completa para essa API
./orquestrador.sh neosigner
```

O log fica em `orquestrador-<api>.log` e os relatórios em `output-<api>/`.

## Arquitetura

A pipeline é organizada em camadas, respeitando a regra de dependência (setas apontam para
dentro; a infraestrutura implementa as portas do domínio):

```
interfaces (CLI)  ──►  application (use cases)  ──►  domain (entities / ports / services)
                                                          ▲
                            infrastructure (adapters) ─────┘
```

- **domain/** — Núcleo independente de frameworks.
  - `entities.py`, `value_objects.py`, `errors.py`
  - `ports/` — contratos (parsing, openapi, analysis, testing, reporting, auth, http, llm, storage…)
  - `services/` — regras puras (`pii_rules.py`, `vulnerability_rules.py`)
- **application/use_cases/** — Um caso de uso por passo da pipeline:
  `scan_source`, `generate_openapi`, `generate_example_data`, `analyze_and_enrich`,
  `run_schemathesis`, `build_report`.
- **infrastructure/** — Implementações concretas das portas: `parsers/` (tree-sitter),
  `openapi/`, `examples/`, `analysis/`, `testing/` (Schemathesis), `reporting/`, `auth/`,
  `http/`, `llm/`, `persistence/`, `config/`.
- **interfaces/cli/** — Pontos de entrada `stepN_*` invocados via `python -m`.
- **bootstrap.py** — _Composition root_: instancia os adapters, injeta-os nos casos de uso e
  devolve um `Container` pronto para as interfaces.

### Estrutura do projeto

```
gtsa/
├── orquestrador.sh                # Pipeline completa (recebe <api_name>)
├── pyproject.toml                 # Empacotamento, dependências e scripts de console
├── requirements.txt               # Dependências (uso alternativo ao pip install -e .)
├── conftest.py                    # Insere src/ no path para os testes
├── config/                        # Configurações versionadas
│   ├── auth_config.json           # Headers fixos e tokens por role
│   ├── pii_patterns.json          # Padrões de detecção de PII
│   └── vulnerability_mapping.json # Mapeamento de vulnerabilidades
├── src/gtsa/
│   ├── bootstrap.py               # Composition root (build_container)
│   ├── domain/                    # Entidades, value objects, ports e services
│   ├── application/use_cases/     # Casos de uso da pipeline
│   ├── infrastructure/            # Adapters (parsers, openapi, testing, ...)
│   └── interfaces/
│       ├── cli/                   # step1..6 (entrypoints python -m)
│       └── stateful/              # Testes stateful (state machine)
├── tests/                         # Testes unitários (pytest)
├── runtime/                       # Artefatos de execução (gitignored)
│   ├── scans/scan_<timestamp>/    # Resultado de cada scan (all_endpoints.json)
│   └── dados/                     # Dados de exemplo gerados
└── output-<api>/                  # Relatórios finais por API
```

## Instalação

```bash
git clone <repo>
cd gtsa

python3 -m venv .venv
source .venv/bin/activate

# Opção recomendada: instala o pacote e expõe os scripts de console
pip install -e .

# Extras opcionais
pip install -e ".[llm]"   # Suporte a LLM local (transformers, torch, accelerate)
pip install -e ".[dev]"   # Ferramentas de desenvolvimento (pytest, ruff, mypy, ...)
```

Requisitos:

- Python 3.9+
- Bash 4.0+
- (Opcional) Backend LLM local (Ollama, Gatiator, etc.) para os passos que usam LLM

> Se preferir não instalar o pacote, o `orquestrador.sh` já exporta `PYTHONPATH=src`, permitindo
> rodar os módulos diretamente com `PYTHONPATH=src python -m gtsa.interfaces.cli.stepN_*`.

## Configuração

### Arquivo `.env.<api_name>`

O orquestrador é sempre invocado com o nome da API (`./orquestrador.sh <api_name>`) e carrega o
arquivo `.env.<api_name>` correspondente. As variáveis principais:

```bash
# Fonte do código a analisar (obrigatório)
API_SOURCE="/caminho/para/o/projeto"

# URL base da API sob teste
API_BASE_URL="http://localhost:8080"

# Especificação OpenAPI (padrão: output-<api>/openapi.json)
OPENAPI_JSON="output-neosigner/openapi.json"

# Controle de passos opcionais
STEP_2_ENABLED=false   # Gerar OpenAPI a partir do scan
STEP_3_ENABLED=true    # Gerar dados de exemplo (usa LLM)

# LLM
LLM_BACKEND=ollama
LLM_MODEL=gemma

# Filtros de execução e relatório
ONLY_HIGH_RISK=false
MAX_EXAMPLES=10
VERBOSE=false
PYTHON_DEBUG=false

# Tokens por role (usados nos testes autenticados)
CHAVE_ACESSO_SISTEMA="..."
TOKEN_ADMINISTRADOR="eyJhbGciOiJIUzI1NiIs..."
TOKEN_GESTOR="eyJhbGciOiJIUzI1NiIs..."
TOKEN_REQUISITANTE="eyJhbGciOiJIUzI1NiIs..."
TOKEN_INTERESSADO="eyJhbGciOiJIUzI1NiIs..."
```

### `config/auth_config.json`

Mapeia headers fixos e os tokens por role para variáveis de ambiente (definidas no `.env.<api>`):

```json
{
  "fixed_headers": [
    { "name": "x-chave-acesso-sistema", "env_var": "CHAVE_ACESSO_SISTEMA" }
  ],
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

## Pipeline de Execução

Cada passo é um módulo CLI executado com `python -m gtsa.interfaces.cli.stepN_*`. Todos aceitam
`--env-file` e `--output-dir`. O orquestrador encadeia os seis passos automaticamente.

### Passo 1 — Scan do código-fonte

```bash
python -m gtsa.interfaces.cli.step1_scan -i <caminho_projeto> --output-dir output-<api> [--language typescript] [--debug]
```

Varre o projeto e extrai endpoints usando parsers baseados em tree-sitter. A linguagem é
detectada automaticamente (TypeScript/JavaScript, Java, Python, Go, Ruby) ou forçada via
`--language`.

**Saída:** `runtime/scans/scan_<timestamp>/all_endpoints.json` (contrato oficial da pipeline).

### Passo 2 — Geração de OpenAPI (opcional)

```bash
python -m gtsa.interfaces.cli.step2_openapi --output-dir output-<api> --env-file .env.<api> [--title ...] [--version ...] [--prefix ...] [--base-url ...]
```

Gera uma especificação OpenAPI 3.0 a partir dos endpoints do scan. Habilitado por
`STEP_2_ENABLED=true`.

**Saída:** `output-<api>/openapi.json`.

### Passo 3 — Dados de exemplo (opcional, LLM)

```bash
python -m gtsa.interfaces.cli.step3_dados_exemplo <openapi.json> --only-with-body --env-file .env.<api> --llm-backend ollama --llm-model gemma
```

Gera dados de exemplo (body/parâmetros) para os endpoints, priorizando exemplos inline do próprio
schema e recorrendo ao LLM como fallback. Habilitado por `STEP_3_ENABLED=true`.

**Saída:** `runtime/dados/`.

### Passo 4 — Análise de risco e enriquecimento

```bash
python -m gtsa.interfaces.cli.step4_analyzer_and_enricher <all_endpoints.json> --output-dir output-<api> --openapi <openapi.json> --env-file .env.<api> [--no-llm]
```

Classifica riscos, detecta PII e mapeia vulnerabilidades para OWASP API Top 10 2023 e SANS Top 25.
Opera em modo híbrido (LLM com fallback heurístico); `--no-llm` usa apenas as heurísticas
determinísticas.

**Saídas:** `output-<api>/openapi_enriched.json` e `output-<api>/final_security_report.md`.

### Passo 5 — Schemathesis com dados reais

```bash
python -m gtsa.interfaces.cli.step5_schemathesis_with_data --output-dir output-<api> --env-file .env.<api> [--only-high-risk] [--verbose]
```

Executa o Schemathesis contra a API, injetando dados de exemplo e autenticação condicional por
role. Um hook (`schemathesis_hooks.py`) é gerado no diretório de saída. `--only-high-risk`
restringe os testes aos endpoints de maior risco.

**Saída:** `output-<api>/schemathesis_results.xml`.

### Passo 6 — Relatório Markdown

```bash
python -m gtsa.interfaces.cli.step6_gerar_relatorio_markdown --output-dir output-<api> --env-file .env.<api> [--full] [--hide-success] [--hide-skip]
```

Consolida os resultados do Schemathesis em um relatório final. As flags controlam a verbosidade
(incluir todos os endpoints, omitir sucessos, omitir pulados).

**Saída:** `output-<api>/test_api_summary.md`.

## Fluxo de Dados

```
Código-Fonte
   │  (Passo 1: scan)
   ▼
runtime/scans/scan_<ts>/all_endpoints.json
   │
   ├─► (Passo 2, opcional) ─► output-<api>/openapi.json
   │                              │
   │        (Passo 3, opcional) ─► runtime/dados/
   ▼
(Passo 4: análise) ─► openapi_enriched.json + final_security_report.md
   │
   ▼
(Passo 5: Schemathesis) ─► schemathesis_results.xml
   │
   ▼
(Passo 6: relatório) ─► test_api_summary.md
```

## Scripts de Console

Após `pip install -e .`, os passos ficam disponíveis como comandos:

| Comando             | Módulo                                               |
| ------------------- | ---------------------------------------------------- |
| `gtsa-scan`         | `gtsa.interfaces.cli.step1_scan`                     |
| `gtsa-openapi`      | `gtsa.interfaces.cli.step2_openapi`                  |
| `gtsa-examples`     | `gtsa.interfaces.cli.step3_dados_exemplo`            |
| `gtsa-analyze`      | `gtsa.interfaces.cli.step4_analyzer_and_enricher`    |
| `gtsa-schemathesis` | `gtsa.interfaces.cli.step5_schemathesis_with_data`   |
| `gtsa-report`       | `gtsa.interfaces.cli.step6_gerar_relatorio_markdown` |

## Artefatos Gerados

**`output-<api>/`** (relatórios por API):

- `openapi.json` / `openapi_enriched.json` — especificação e versão enriquecida
- `final_security_report.md` — análise de segurança (OWASP / SANS)
- `schemathesis_results.xml` — resultado bruto dos testes
- `test_api_summary.md` — sumário final dos testes

**`runtime/`** (temporário, gitignored):

- `scans/scan_<timestamp>/all_endpoints.json` — endpoints extraídos
- `dados/` — dados de exemplo gerados

## Testes

```bash
pip install -e ".[dev]"
pytest
```

Os testes ficam em `tests/`; o `conftest.py` garante que `src/` esteja no `sys.path`.
A configuração do pytest está centralizada no `pyproject.toml`.

## Suporte / Logs

- `orquestrador-<api>.log` — execução geral da pipeline
- `output-<api>/` — relatórios finais e artefatos por API
