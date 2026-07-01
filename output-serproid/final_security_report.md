# Relatório de Análise de Segurança de API

## 📊 Resumo

| Métrica | Valor |
|---------|-------|
| **Total de endpoints** | 80 |
| **Alto risco** | 7 (8.8%) |
| **Médio risco** | 40 (50.0%) |
| **Baixo risco** | 33 (41.2%) |
| **Com dados PII** | 6 (7.5%) |

## 🛡️ OWASP API Top 10 2023

| ID | Categoria | Endpoints afetados |
|----|-----------|-------------------|
| API7:2023 | Server-Side Request Forgery | 2 |

## 📊 SANS Top 25

| Rank | CWE | Endpoints afetados |
|------|-----|-------------------|
| 8 | CWE-918 | 2 |

## 🔴 Endpoints de Alto Risco

| Método | Path | Vulnerabilidades |
|--------|------|------------------|
| POST | `/dispositivos/{dispositivo}/certificados/{certificadoId}/email-recuperacao` | sem mapeamento explícito (Contém PII: email) |
| POST | `/dispositivos/{dispositivo}/certificados/{certificadoId}/email-recuperacao/access-token` | sem mapeamento explícito (Contém PII: email) |
| GET | `/dispositivos/{dispositivo}/certificados/{certificadoId}/email-recuperacao/verificar` | sem mapeamento explícito (Contém PII: email) |
| POST | `/dispositivos/{dispositivo}/certificados/{idCertificado}/enviar-email-recuperacao` | sem mapeamento explícito (Contém PII: email) |
| POST | `/atualizacao-serproid-desktop/enviar-emails` | sem mapeamento explícito (Contém PII: email) |
| POST | `/applications/{clientId}/redirect-uris` | ssrf, open_redirect |
| DELETE | `/applications/{clientId}/redirect-uris` | ssrf, open_redirect |

---
*Relatório gerado por step4_analyzer_and_enricher.py em 24/06/2026 10:59:06*
