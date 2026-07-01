# Relatório de Análise de Segurança de API

## 📊 Resumo

| Métrica | Valor |
|---------|-------|
| **Total de endpoints** | 73 |
| **Alto risco** | 5 (6.8%) |
| **Médio risco** | 50 (68.5%) |
| **Baixo risco** | 18 (24.7%) |
| **Com dados PII** | 4 (5.5%) |

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

---
*Relatório gerado por step4_analyzer_and_enricher.py em 01/07/2026 10:49:54*
