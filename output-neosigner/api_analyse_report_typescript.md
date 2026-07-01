# Relatório de Análise de API - typescript

## Resumo

- **Total de endpoints encontrados:** 73
- **Endpoints principais:** 73
- **Endpoints auxiliares:** 0
- **Métodos HTTP:** DELETE, GET, PATCH, POST, PUT

## Endpoints por Método

- **DELETE:** 2
- **GET:** 30
- **PATCH:** 26
- **POST:** 8
- **PUT:** 7

## Lista de Endpoints

| Método | Path | Handler | Arquivo | Linha | Tipo |
|--------|------|---------|---------|-------|------|
| DELETE | `/api/documentos/:id` | `anonymous` | infra/api/routes/DocumentoRoutes.ts | 104 | ✅ Principal |
| DELETE | `/api/fluxo/:id` | `anonymous` | infra/api/routes/FluxoRoutes.ts | 191 | ✅ Principal |
| GET | `/api/autenticar-certificado` | `anonymous` | infra/api/routes/AutenticationsRoutes.ts | 505 | ✅ Principal |
| GET | `/api/authentication-options` | `anonymous` | infra/api/routes/AutenticationsRoutes.ts | 85 | ✅ Principal |
| GET | `/api/clientes` | `anonymous` | infra/api/routes/ClienteRoutes.ts | 96 | ✅ Principal |
| GET | `/api/clientes/:id` | `anonymous` | infra/api/routes/ClienteRoutes.ts | 197 | ✅ Principal |
| GET | `/api/confirmacao-conta/:idConta` | `anonymous` | infra/api/routes/AutenticationsRoutes.ts | 313 | ✅ Principal |
| GET | `/api/contas` | `anonymous` | infra/api/routes/ContaRoutes.ts | 290 | ✅ Principal |
| GET | `/api/contas/codigo/:codigo` | `anonymous` | infra/api/routes/ContaRoutes.ts | 371 | ✅ Principal |
| GET | `/api/contas/id/:id` | `anonymous` | infra/api/routes/ContaRoutes.ts | 233 | ✅ Principal |
| GET | `/api/contas/perfil/:perfil` | `anonymous` | infra/api/routes/ContaRoutes.ts | 186 | ✅ Principal |
| GET | `/api/contas/sumario` | `anonymous` | infra/api/routes/ContaRoutes.ts | 323 | ✅ Principal |
| GET | `/api/controlador/hello` | `anonymous` | infra/api/routes/HelloRoutes.ts | 120 | ✅ Principal |
| GET | `/api/controlador/meu-ip` | `anonymous` | infra/api/routes/HelloRoutes.ts | 172 | ✅ Principal |
| GET | `/api/fluxo/:id` | `anonymous` | infra/api/routes/FluxoRoutes.ts | 465 | ✅ Principal |
| GET | `/api/fluxos` | `anonymous` | infra/api/routes/FluxoRoutes.ts | 424 | ✅ Principal |
| GET | `/api/fluxos-interessado` | `anonymous` | infra/api/routes/FluxoRoutes.ts | 880 | ✅ Principal |
| GET | `/api/fluxos/:id/hashes-documentos/:algoritmo` | `anonymous` | infra/api/routes/FluxoRoutes.ts | 509 | ✅ Principal |
| GET | `/api/fluxos/:id/interessados` | `anonymous` | infra/api/routes/FluxoRoutes.ts | 617 | ✅ Principal |
| GET | `/api/fluxos/:id/sumario` | `anonymous` | infra/api/routes/FluxoRoutes.ts | 921 | ✅ Principal |
| GET | `/api/fluxos/arquivados` | `anonymous` | infra/api/routes/FluxoRoutes.ts | 567 | ✅ Principal |
| GET | `/api/getlink` | `anonymous` | infra/api/routes/DevelopRoutes.ts | 57 | ✅ Principal |
| GET | `/api/grupos` | `anonymous` | infra/api/routes/GrupoRoutes.ts | 248 | ✅ Principal |
| GET | `/api/grupos-gestor-mais-requisitante` | `anonymous` | infra/api/routes/GrupoRoutes.ts | 326 | ✅ Principal |
| GET | `/api/grupos-requisitante` | `anonymous` | infra/api/routes/GrupoRoutes.ts | 284 | ✅ Principal |
| GET | `/api/grupos/id/:id` | `anonymous` | infra/api/routes/GrupoRoutes.ts | 168 | ✅ Principal |
| GET | `/api/listar-contas/:email` | `anonymous` | infra/api/routes/AutenticationsRoutes.ts | 277 | ✅ Principal |
| GET | `/api/monitoracao/dlqs` | `anonymous` | infra/api/routes/MonitoracaoRoutes.ts | 100 | ✅ Principal |
| GET | `/api/resposta/:id` | `anonymous` | infra/api/routes/FluxoRoutes.ts | 660 | ✅ Principal |
| GET | `/api/respostas-gerencial` | `anonymous` | infra/api/routes/FluxoRoutes.ts | 820 | ✅ Principal |
| GET | `/api/webhook/validar/:idRequisitante` | `anonymous` | infra/api/routes/WebhookRoutes.ts | 47 | ✅ Principal |
| GET | `/metrics` | `anonymous` | infra/metrics/MetricsServer.ts | 11 | ✅ Principal |
| PATCH | `/api/contas/reenviar-credenciais-sistema` | `anonymous` | infra/api/routes/ContaRoutes.ts | 408 | ✅ Principal |
| PATCH | `/api/enviar-otp` | `anonymous` | infra/api/routes/AutenticationsRoutes.ts | 359 | ✅ Principal |
| PATCH | `/api/fluxos/:id/arquivar` | `anonymous` | infra/api/routes/FluxoRoutes.ts | 352 | ✅ Principal |
| PATCH | `/api/fluxos/:id/assinar` | `anonymous` | infra/api/routes/ResponderFluxoRoutes.ts | 140 | ✅ Principal |
| PATCH | `/api/fluxos/:id/assinar-bird-id` | `anonymous` | infra/api/routes/ResponderFluxoRoutes.ts | 376 | ✅ Principal |
| PATCH | `/api/fluxos/:id/assinar-certisign` | `anonymous` | infra/api/routes/ResponderFluxoRoutes.ts | 691 | ✅ Principal |
| PATCH | `/api/fluxos/:id/assinar-desktop/:algoritmo` | `anonymous` | infra/api/routes/ResponderFluxoRoutes.ts | 759 | ✅ Principal |
| PATCH | `/api/fluxos/:id/assinar-ds-cloud` | `anonymous` | infra/api/routes/ResponderFluxoRoutes.ts | 565 | ✅ Principal |
| PATCH | `/api/fluxos/:id/assinar-safe-id` | `anonymous` | infra/api/routes/ResponderFluxoRoutes.ts | 439 | ✅ Principal |
| PATCH | `/api/fluxos/:id/assinar-serpro-id` | `anonymous` | infra/api/routes/ResponderFluxoRoutes.ts | 313 | ✅ Principal |
| PATCH | `/api/fluxos/:id/assinar-syn-id` | `anonymous` | infra/api/routes/ResponderFluxoRoutes.ts | 628 | ✅ Principal |
| PATCH | `/api/fluxos/:id/assinar-vidaas` | `anonymous` | infra/api/routes/ResponderFluxoRoutes.ts | 502 | ✅ Principal |
| PATCH | `/api/fluxos/:id/cancelar` | `anonymous` | infra/api/routes/FluxoRoutes.ts | 314 | ✅ Principal |
| PATCH | `/api/fluxos/:id/finalizar` | `anonymous` | infra/api/routes/FluxoRoutes.ts | 272 | ✅ Principal |
| PATCH | `/api/fluxos/:id/iniciar` | `anonymous` | infra/api/routes/FluxoRoutes.ts | 230 | ✅ Principal |
| PATCH | `/api/fluxos/:id/rejeitar` | `anonymous` | infra/api/routes/ResponderFluxoRoutes.ts | 79 | ✅ Principal |
| PATCH | `/api/fluxos/:id/revisao` | `anonymous` | infra/api/routes/ResponderFluxoRoutes.ts | 253 | ✅ Principal |
| PATCH | `/api/fluxos/:id/revisar` | `anonymous` | infra/api/routes/ResponderFluxoRoutes.ts | 198 | ✅ Principal |
| PATCH | `/api/fluxos/arquivar` | `anonymous` | infra/api/routes/CronRoutes.ts | 89 | ✅ Principal |
| PATCH | `/api/fluxos/finalizar` | `anonymous` | infra/api/routes/CronRoutes.ts | 66 | ✅ Principal |
| PATCH | `/api/link` | `anonymous` | infra/api/routes/AutenticationsRoutes.ts | 471 | ✅ Principal |
| PATCH | `/api/notificar` | `anonymous` | infra/api/routes/CronRoutes.ts | 38 | ✅ Principal |
| PATCH | `/api/reenviar-links` | `anonymous` | infra/api/routes/LinkRoutes.ts | 64 | ✅ Principal |
| PATCH | `/api/verificar-certificado` | `anonymous` | infra/api/routes/AutenticationsRoutes.ts | 540 | ✅ Principal |
| PATCH | `/api/verificar-certificado-nuvem` | `anonymous` | infra/api/routes/AutenticationsRoutes.ts | 586 | ✅ Principal |
| PATCH | `/api/verificar-otp` | `anonymous` | infra/api/routes/AutenticationsRoutes.ts | 390 | ✅ Principal |
| POST | `/api/clientes` | `anonymous` | infra/api/routes/ClienteRoutes.ts | 127 | ✅ Principal |
| POST | `/api/contas/perfil/:perfil` | `anonymous` | infra/api/routes/ContaRoutes.ts | 71 | ✅ Principal |
| POST | `/api/documentos` | `anonymous` | infra/api/routes/DocumentoRoutes.ts | 64 | ✅ Principal |
| POST | `/api/fluxos` | `anonymous` | infra/api/routes/FluxoRoutes.ts | 63 | ✅ Principal |
| POST | `/api/fluxos/adicionar` | `anonymous` | infra/api/routes/FluxoRoutes.ts | 99 | ✅ Principal |
| POST | `/api/grupos` | `anonymous` | infra/api/routes/GrupoRoutes.ts | 64 | ✅ Principal |
| POST | `/api/verify-authentication` | `anonymous` | infra/api/routes/AutenticationsRoutes.ts | 196 | ✅ Principal |
| POST | `/api/verify-registration` | `anonymous` | infra/api/routes/AutenticationsRoutes.ts | 140 | ✅ Principal |
| PUT | `/api/clientes/:id` | `anonymous` | infra/api/routes/ClienteRoutes.ts | 164 | ✅ Principal |
| PUT | `/api/contas/perfil/:perfil/:id` | `anonymous` | infra/api/routes/ContaRoutes.ts | 139 | ✅ Principal |
| PUT | `/api/fluxos/:id` | `anonymous` | infra/api/routes/FluxoRoutes.ts | 158 | ✅ Principal |
| PUT | `/api/grupos/:id` | `anonymous` | infra/api/routes/GrupoRoutes.ts | 123 | ✅ Principal |
| PUT | `/api/login-sistema` | `anonymous` | infra/api/routes/AutenticationsRoutes.ts | 234 | ✅ Principal |
| PUT | `/api/logout` | `anonymous` | infra/api/routes/AutenticationsRoutes.ts | 611 | ✅ Principal |
| PUT | `/api/token` | `anonymous` | infra/api/routes/AutenticationsRoutes.ts | 428 | ✅ Principal |
