# Relatório de Análise de Segurança de API

## 📊 Resumo

| Métrica | Valor |
|---------|-------|
| **Total de endpoints** | 74 |
| **Alto risco** | 6 (8.1%) |
| **Médio risco** | 50 (67.6%) |
| **Baixo risco** | 18 (24.3%) |
| **Com dados PII** | 5 (6.8%) |

## 🛡️ OWASP API Top 10 2023

| ID | Categoria | Endpoints afetados |
|----|-----------|-------------------|
| API7:2023 | Server-Side Request Forgery | 1 |

## 📊 SANS Top 25

| Rank | CWE | Endpoints afetados |
|------|-----|-------------------|
| 8 | CWE-918 | 1 |

## 🔴 Endpoints de Alto Risco

| Método | Path | Vulnerabilidades |
|--------|------|------------------|
| POST | `/api/documentos` | sem mapeamento explícito (Contém PII: documento) |
| DELETE | `/api/documentos/:id` | sem mapeamento explícito (Contém PII: documento) |
| GET | `/api/webhook/validar/:idRequisitante` | ssrf, unsafe_consumption |
| GET | `/api/fluxos/:id/hashes-documentos/:algoritmo` | sem mapeamento explícito (Contém PII: documento) |
| GET | `/api/listar-contas/:email` | sem mapeamento explícito (Contém PII: email) |
| GET | `/api/confirmacao-interessado/:email/:idConta` | sem mapeamento explícito (Contém PII: email) |

---
*Relatório gerado por step4_analyzer_and_enricher.py em 23/06/2026 15:40:10*
