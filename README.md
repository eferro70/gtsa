# GTSA — Gerador de Testes de Segurança de APIs

O **GTSA** é uma ferramenta de análise e teste de segurança para APIs REST. A partir do
código-fonte de um projeto (Java, TypeScript, Python, Go ou Ruby) ou de uma especificação OpenAPI
existente, o GTSA extrai endpoints, classifica riscos segundo o **OWASP API Top 10 2023** e
**SANS Top 25**, executa testes de conformidade e fuzzing com
[Schemathesis](https://schemathesis.readthedocs.io/) e consolida tudo em relatórios Markdown.

A ferramenta é **agnóstica à API testada**: toda configuração específica de um projeto fica
isolada em `apis/<nome>/` (arquivo `.env`, hooks Python opcionais), sem tocar no código do GTSA.

---

## Sumário

- [Início Rápido](#início-rápido)
- [Arquitetura](#arquitetura)
- [Instalação](#instalação)
- [Configurando uma Nova API](#configurando-uma-nova-api)
  - [Exemplo: Neosigner](#exemplo-neosigner)
- [Pipeline de Execução](#pipeline-de-execução)
- [Fluxo de Dados](#fluxo-de-dados)
- [Hooks Customizados por API](#hooks-customizados-por-api)
- [Scripts de Console](#scripts-de-console)
- [Artefatos Gerados](#artefatos-gerados)
- [Testes](#testes)
- [Suporte / Logs](#suporte--logs)

---

## Início Rápido

```bash
# 1. Criar e ativar o ambiente virtual
python3 -m venv .venv
source .venv/bin/activate

# 2. Instalar o pacote (modo editável) com as dependências
pip install -e .

# 3. Criar o diretório e o arquivo de ambiente da API alvo
mkdir -p apis/minha-api
cp apis/neosigner/.env apis/minha-api/.env   # use como base
nano apis/minha-api/.env                     # ajuste as variáveis

# 4. Executar a pipeline completa
./orquestrador.sh minha-api
```

O log fica em `logs/<api>.log` e os relatórios em `output-<api>/`.

---

## Arquitetura

O GTSA segue **Clean Architecture**: as camadas internas não conhecem as externas. A regra de
dependência diz que as setas de importação só apontam para dentro.

```
┌─────────────────────────────────────────────────────────┐
│  interfaces/cli  (step1..step6)                         │  ← entrada do usuário
│        │ chama                                          │
│        ▼                                                │
│  application/use_cases                                  │  ← orquestra o fluxo
│        │ chama contratos (ports) definidos em           │
│        ▼                                                │
│  domain  (entities, value_objects, ports, services)     │  ← regras puras, sem deps externas
│        ▲                                                │
│        │ implementa os ports                            │
│  infrastructure  (adapters)                             │  ← detalhes técnicos
│    ├── parsers (tree-sitter)                            │
│    ├── openapi, analysis, reporting                     │
│    ├── testing (Schemathesis)                           │
│    ├── auth, http, llm, persistence                     │
│    └── ...                                              │
└─────────────────────────────────────────────────────────┘
```

**Como ler:** a `infrastructure` implementa os contratos (`ports`) que o `domain` define, mas
nunca ao contrário. A `application` só enxerga o `domain`. As CLIs (`interfaces`) só enxergam a
`application`. Isso permite trocar qualquer adapter (ex.: LLM, parser, banco) sem tocar nas
regras de negócio.

O **`bootstrap.py`** é o único ponto onde todas as camadas se encontram: ele instancia os
adapters concretos e os injeta nos casos de uso via `build_container()`.

### Estrutura do projeto

```
gtsa/
├── orquestrador.sh                # Pipeline completa (recebe <api_name>)
├── pyproject.toml
├── apis/                          # Configuração por API (gitignored para .env)
│   └── <api_name>/
│       ├── .env                   # Variáveis de ambiente da API
│       └── hooks.py               # Hooks Schemathesis específicos (opcional)
├── logs/                          # Logs de execução por API
│   └── <api_name>.log
├── config/                        # Configurações globais versionadas
│   ├── pii_patterns.json
│   └── vulnerability_mapping.json
├── src/gtsa/
│   ├── bootstrap.py
│   ├── domain/
│   ├── application/use_cases/
│   ├── infrastructure/
│   └── interfaces/cli/
├── tests/
├── runtime/                       # Artefatos de execução (gitignored)
│   ├── scans/scan_<timestamp>/
│   └── dados/
└── output-<api>/                  # Relatórios finais por API
```

---

## Instalação

```bash
git clone <repo>
cd gtsa

python3 -m venv .venv
source .venv/bin/activate

pip install -e .

# Extras opcionais
pip install -e ".[llm]"   # Suporte a LLM local (transformers, torch, accelerate)
pip install -e ".[dev]"   # Ferramentas de desenvolvimento (pytest, ruff, mypy)
```

Requisitos: Python 3.9+, Bash 4.0+, e opcionalmente um backend LLM local (Ollama, etc.).

---

## Configurando uma Nova API

Toda a configuração de uma API fica em `apis/<nome>/`:

```
apis/
  <nome>/
    .env        ← variáveis obrigatórias e tokens
    hooks.py    ← hooks Schemathesis específicos (opcional)
```

### Variáveis do `.env`

```bash
# Fonte do código a analisar (obrigatório)
API_SOURCE="/caminho/para/o/projeto"

# URL base da API em execução
API_BASE_URL="http://localhost:8080"

# Linguagem do projeto (opcional — detectada automaticamente se omitida)
# API_LANGUAGE=java

# Especificação OpenAPI de entrada (padrão: output-<api>/openapi.json)
OPENAPI_JSON="output-<api>/openapi.json"

# Controle de passos opcionais
STEP_2_ENABLED=false   # gerar OpenAPI a partir do scan
STEP_3_ENABLED=true    # gerar dados de exemplo (usa LLM)

# LLM
LLM_BACKEND=ollama
LLM_MODEL=gemma

# Filtros de execução
ONLY_HIGH_RISK=false
MAX_EXAMPLES=10
VERBOSE=false

# Tokens de autenticação por role
CHAVE_ACESSO_SISTEMA="..."
TOKEN_ADMINISTRADOR="eyJ..."
TOKEN_GESTOR="eyJ..."
TOKEN_REQUISITANTE="eyJ..."
TOKEN_INTERESSADO="eyJ..."

# Hooks Python específicos desta API (opcional)
SCHEMATHESIS_HOOKS_EXTRA=apis/<nome>/hooks.py
```

### Exemplo: Neosigner

A API Neosigner (`apis/neosigner/`) ilustra o caso mais completo: autenticação com múltiplos
perfis de usuário, dados de exemplo gerados por LLM e hooks customizados.

**`apis/neosigner/.env`** (fragmento):

```bash
API_SOURCE="/caminho/para/neosigner/controlador-api"
API_BASE_URL="http://localhost"
OPENAPI_JSON="output-neosigner/openapi.json"
STEP_2_ENABLED=false
STEP_3_ENABLED=true
LLM_BACKEND=ollama
LLM_MODEL=gemma
TOKEN_ADMINISTRADOR="eyJ..."
TOKEN_GESTOR="eyJ..."
TOKEN_REQUISITANTE="eyJ..."
TOKEN_INTERESSADO="eyJ..."
SCHEMATHESIS_HOOKS_EXTRA=apis/neosigner/hooks.py
```

**`apis/neosigner/hooks.py`** — customizações necessárias para esta API:

```python
import secrets
import schemathesis

def _gerar_cnpj():
    """Gera CNPJ válido a cada chamada para evitar conflito de duplicata."""
    def _d(nums, pesos):
        r = sum(n * p for n, p in zip(nums, pesos)) % 11
        return 0 if r < 2 else 11 - r
    base = [secrets.randbelow(10) for _ in range(12)]
    d = base + [_d(base, [5,4,3,2,9,8,7,6,5,4,3,2])]
    return ''.join(map(str, d + [_d(d, [6,5,4,3,2,9,8,7,6,5,4,3,2])]))

@schemathesis.hook
def before_call(context, case, kwargs):
    if case.operation.path == '/api/v1/clientes' and case.operation.method.upper() == 'POST':
        if case.body and isinstance(case.body.get('contratante'), dict):
            import copy
            b = copy.deepcopy(case.body)
            b['contratante']['identificador'] = _gerar_cnpj()
            for t in b['contratante'].get('tecnicosProducao') or []:
                if not isinstance(t, dict): continue
                if not isinstance(t.get('telefone'), (str, type(None))): t['telefone'] = None
                if not isinstance(t.get('paisIso3'), (str, type(None))): t['paisIso3'] = None
            case.body = b
```

Para executar:

```bash
./orquestrador.sh neosigner
```

---

## Pipeline de Execução

Cada passo é um módulo CLI executado com `python -m gtsa.interfaces.cli.stepN_*`. O orquestrador
encadeia os seis passos automaticamente. Todos aceitam `--env-file` e `--output-dir`.

| Passo | Módulo                           | Função                                   |
| ----- | -------------------------------- | ---------------------------------------- |
| 1     | `step1_scan`                     | Varre o código-fonte e extrai endpoints  |
| 2     | `step2_openapi`                  | Gera OpenAPI a partir do scan (opcional) |
| 3     | `step3_dados_exemplo`            | Gera dados de exemplo via LLM (opcional) |
| 4     | `step4_analyzer_and_enricher`    | Classifica riscos e enriquece a spec     |
| 5     | `step5_schemathesis_with_data`   | Executa testes com Schemathesis          |
| 6     | `step6_gerar_relatorio_markdown` | Consolida resultados em Markdown         |

### Passo 1 — Scan

```bash
python -m gtsa.interfaces.cli.step1_scan -i <projeto> --output-dir output-<api> [--language java]
```

Parsers baseados em tree-sitter extraem endpoints. Linguagem detectada automaticamente ou forçada
via `--language`. **Saída:** `runtime/scans/scan_<ts>/all_endpoints.json`.

### Passo 2 — OpenAPI (opcional)

```bash
python -m gtsa.interfaces.cli.step2_openapi --output-dir output-<api> --env-file apis/<api>/.env
```

Gera especificação OpenAPI 3.0 a partir dos endpoints. Ativo com `STEP_2_ENABLED=true`.

### Passo 3 — Dados de exemplo (opcional)

```bash
python -m gtsa.interfaces.cli.step3_dados_exemplo openapi.json --only-with-body \
  --env-file apis/<api>/.env --llm-backend ollama --llm-model gemma
```

Gera corpos de requisição realistas para os endpoints. **Saída:** `runtime/dados/`.

### Passo 4 — Análise de risco

```bash
python -m gtsa.interfaces.cli.step4_analyzer_and_enricher all_endpoints.json \
  --output-dir output-<api> --openapi openapi.json --env-file apis/<api>/.env [--no-llm]
```

Classifica riscos (OWASP API Top 10, SANS Top 25) e detecta PII. `--no-llm` usa apenas
heurísticas determinísticas. **Saídas:** `openapi_enriched.json`, `final_security_report.md`.

### Passo 5 — Schemathesis

```bash
python -m gtsa.interfaces.cli.step5_schemathesis_with_data \
  --output-dir output-<api> --env-file apis/<api>/.env [--only-high-risk]
```

Executa testes de conformidade, coverage e fuzzing com autenticação condicional por role. Gera
`schemathesis_hooks.py` no diretório de saída; se `SCHEMATHESIS_HOOKS_EXTRA` estiver definido,
appenda o arquivo de hooks da API. **Saída:** `schemathesis_results.xml`.

### Passo 6 — Relatório

```bash
python -m gtsa.interfaces.cli.step6_gerar_relatorio_markdown \
  --output-dir output-<api> --env-file apis/<api>/.env [--full] [--hide-success]
```

Consolida os resultados em um relatório Markdown. **Saída:** `test_api_summary.md`.

---

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

---

## Hooks Customizados por API

O Passo 5 gera `output-<api>/schemathesis_hooks.py` com infraestrutura genérica (autenticação,
query fixtures). Para comportamentos específicos da API testada, crie `apis/<nome>/hooks.py` e
aponte com `SCHEMATHESIS_HOOKS_EXTRA=apis/<nome>/hooks.py` no `.env`.

O conteúdo do arquivo extra é appendado ao hooks gerado a cada execução. Isso mantém o código do
GTSA livre de lógica específica de qualquer API.

---

## Scripts de Console

Após `pip install -e .`:

| Comando             | Módulo                                               |
| ------------------- | ---------------------------------------------------- |
| `gtsa-scan`         | `gtsa.interfaces.cli.step1_scan`                     |
| `gtsa-openapi`      | `gtsa.interfaces.cli.step2_openapi`                  |
| `gtsa-examples`     | `gtsa.interfaces.cli.step3_dados_exemplo`            |
| `gtsa-analyze`      | `gtsa.interfaces.cli.step4_analyzer_and_enricher`    |
| `gtsa-schemathesis` | `gtsa.interfaces.cli.step5_schemathesis_with_data`   |
| `gtsa-report`       | `gtsa.interfaces.cli.step6_gerar_relatorio_markdown` |

---

## Artefatos Gerados

**`output-<api>/`** (relatórios por API):

- `openapi.json` / `openapi_enriched.json` — especificação e versão enriquecida
- `final_security_report.md` — análise de segurança (OWASP / SANS)
- `schemathesis_results.xml` — resultado bruto dos testes
- `test_api_summary.md` — sumário final dos testes

**`runtime/`** (temporário, gitignored):

- `scans/scan_<timestamp>/all_endpoints.json` — endpoints extraídos
- `dados/` — dados de exemplo gerados

---

## Testes

```bash
pip install -e ".[dev]"
pytest
```

---

## Suporte / Logs

- `logs/<api>.log` — execução geral da pipeline
- `output-<api>/schemathesis_execution.log` — log detalhado do Schemathesis
