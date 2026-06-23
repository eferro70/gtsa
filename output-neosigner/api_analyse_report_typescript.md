# Relatório de Análise de API - typescript

## Resumo

- **Total de endpoints encontrados:** 74
- **Endpoints principais:** 74
- **Endpoints auxiliares:** 0
- **Métodos HTTP:** DELETE, GET, PATCH, POST, PUT

## Endpoints por Método

- **DELETE:** 2
- **GET:** 31
- **PATCH:** 26
- **POST:** 8
- **PUT:** 7

## Lista de Endpoints

| Método | Path | Handler | Arquivo | Linha | Tipo |
|--------|------|---------|---------|-------|------|
| DELETE | `/api/documentos/:id` | `anonymous` | infra/api/routes/DocumentoRoutes.ts | 102 | ✅ Principal |
| DELETE | `/api/fluxo/:id` | `anonymous` | infra/api/routes/FluxoRoutes.ts | 183 | ✅ Principal |
| GET | `/api/autenticar-certificado` | `anonymous` | infra/api/routes/AutenticationsRoutes.ts | 496 | ✅ Principal |
| GET | `/api/authentication-options` | `anonymous` | infra/api/routes/AutenticationsRoutes.ts | 86 | ✅ Principal |
| GET | `/api/clientes` | `anonymous` | infra/api/routes/ClienteRoutes.ts | 94 | ✅ Principal |
| GET | `/api/clientes/:id` | `anonymous` | infra/api/routes/ClienteRoutes.ts | 193 | ✅ Principal |
| GET | `/api/confirmacao-conta/:idConta` | `anonymous` | infra/api/routes/AutenticationsRoutes.ts | 308 | ✅ Principal |
| GET | `/api/confirmacao-interessado/:email/:idConta` | `anonymous` | infra/api/routes/AutenticationsRoutes.ts | 617 | ✅ Principal |
| GET | `/api/contas` | `anonymous` | infra/api/routes/ContaRoutes.ts | 280 | ✅ Principal |
| GET | `/api/contas/codigo/:codigo` | `anonymous` | infra/api/routes/ContaRoutes.ts | 354 | ✅ Principal |
| GET | `/api/contas/id/:id` | `anonymous` | infra/api/routes/ContaRoutes.ts | 227 | ✅ Principal |
| GET | `/api/contas/perfil/:perfil` | `anonymous` | infra/api/routes/ContaRoutes.ts | 182 | ✅ Principal |
| GET | `/api/contas/sumario` | `anonymous` | infra/api/routes/ContaRoutes.ts | 313 | ✅ Principal |
| GET | `/api/controlador/hello` | `anonymous` | infra/api/routes/HelloRoutes.ts | 120 | ✅ Principal |
| GET | `/api/controlador/meu-ip` | `anonymous` | infra/api/routes/HelloRoutes.ts | 172 | ✅ Principal |
| GET | `/api/fluxo/:id` | `anonymous` | infra/api/routes/FluxoRoutes.ts | 453 | ✅ Principal |
| GET | `/api/fluxos` | `anonymous` | infra/api/routes/FluxoRoutes.ts | 414 | ✅ Principal |
| GET | `/api/fluxos-interessado` | `anonymous` | infra/api/routes/FluxoRoutes.ts | 857 | ✅ Principal |
| GET | `/api/fluxos/:id/hashes-documentos/:algoritmo` | `anonymous` | infra/api/routes/FluxoRoutes.ts | 492 | ✅ Principal |
| GET | `/api/fluxos/:id/interessados` | `anonymous` | infra/api/routes/FluxoRoutes.ts | 596 | ✅ Principal |
| GET | `/api/fluxos/:id/sumario` | `anonymous` | infra/api/routes/FluxoRoutes.ts | 896 | ✅ Principal |
| GET | `/api/fluxos/arquivados` | `anonymous` | infra/api/routes/FluxoRoutes.ts | 548 | ✅ Principal |
| GET | `/api/getlink` | `anonymous` | infra/api/routes/DevelopRoutes.ts | 57 | ✅ Principal |
| GET | `/api/grupos` | `anonymous` | infra/api/routes/GrupoRoutes.ts | 240 | ✅ Principal |
| GET | `/api/grupos-gestor-mais-requisitante` | `anonymous` | infra/api/routes/GrupoRoutes.ts | 318 | ✅ Principal |
| GET | `/api/grupos-requisitante` | `anonymous` | infra/api/routes/GrupoRoutes.ts | 276 | ✅ Principal |
| GET | `/api/grupos/id/:id` | `anonymous` | infra/api/routes/GrupoRoutes.ts | 160 | ✅ Principal |
| GET | `/api/listar-contas/:email` | `anonymous` | infra/api/routes/AutenticationsRoutes.ts | 274 | ✅ Principal |
| GET | `/api/monitoracao/dlqs` | `anonymous` | infra/api/routes/MonitoracaoRoutes.ts | 98 | ✅ Principal |
| GET | `/api/resposta/:id` | `anonymous` | infra/api/routes/FluxoRoutes.ts | 637 | ✅ Principal |
| GET | `/api/respostas-gerencial` | `anonymous` | infra/api/routes/FluxoRoutes.ts | 797 | ✅ Principal |
| GET | `/api/webhook/validar/:idRequisitante` | `anonymous` | infra/api/routes/WebhookRoutes.ts | 47 | ✅ Principal |
| GET | `/metrics` | `anonymous` | infra/metrics/MetricsServer.ts | 11 | ✅ Principal |
| PATCH | `/api/contas/reenviar-credenciais-sistema` | `anonymous` | infra/api/routes/ContaRoutes.ts | 391 | ✅ Principal |
| PATCH | `/api/enviar-otp` | `anonymous` | infra/api/routes/AutenticationsRoutes.ts | 352 | ✅ Principal |
| PATCH | `/api/fluxos/:id/arquivar` | `anonymous` | infra/api/routes/FluxoRoutes.ts | 344 | ✅ Principal |
| PATCH | `/api/fluxos/:id/assinar` | `anonymous` | infra/api/routes/ResponderFluxoRoutes.ts | 132 | ✅ Principal |
| PATCH | `/api/fluxos/:id/assinar-bird-id` | `anonymous` | infra/api/routes/ResponderFluxoRoutes.ts | 352 | ✅ Principal |
| PATCH | `/api/fluxos/:id/assinar-certisign` | `anonymous` | infra/api/routes/ResponderFluxoRoutes.ts | 647 | ✅ Principal |
| PATCH | `/api/fluxos/:id/assinar-desktop/:algoritmo` | `anonymous` | infra/api/routes/ResponderFluxoRoutes.ts | 710 | ✅ Principal |
| PATCH | `/api/fluxos/:id/assinar-ds-cloud` | `anonymous` | infra/api/routes/ResponderFluxoRoutes.ts | 529 | ✅ Principal |
| PATCH | `/api/fluxos/:id/assinar-safe-id` | `anonymous` | infra/api/routes/ResponderFluxoRoutes.ts | 411 | ✅ Principal |
| PATCH | `/api/fluxos/:id/assinar-serpro-id` | `anonymous` | infra/api/routes/ResponderFluxoRoutes.ts | 293 | ✅ Principal |
| PATCH | `/api/fluxos/:id/assinar-syn-id` | `anonymous` | infra/api/routes/ResponderFluxoRoutes.ts | 588 | ✅ Principal |
| PATCH | `/api/fluxos/:id/assinar-vidaas` | `anonymous` | infra/api/routes/ResponderFluxoRoutes.ts | 470 | ✅ Principal |
| PATCH | `/api/fluxos/:id/cancelar` | `anonymous` | infra/api/routes/FluxoRoutes.ts | 306 | ✅ Principal |
| PATCH | `/api/fluxos/:id/finalizar` | `anonymous` | infra/api/routes/FluxoRoutes.ts | 264 | ✅ Principal |
| PATCH | `/api/fluxos/:id/iniciar` | `anonymous` | infra/api/routes/FluxoRoutes.ts | 222 | ✅ Principal |
| PATCH | `/api/fluxos/:id/rejeitar` | `anonymous` | infra/api/routes/ResponderFluxoRoutes.ts | 75 | ✅ Principal |
| PATCH | `/api/fluxos/:id/revisao` | `anonymous` | infra/api/routes/ResponderFluxoRoutes.ts | 237 | ✅ Principal |
| PATCH | `/api/fluxos/:id/revisar` | `anonymous` | infra/api/routes/ResponderFluxoRoutes.ts | 186 | ✅ Principal |
| PATCH | `/api/fluxos/arquivar` | `anonymous` | infra/api/routes/CronRoutes.ts | 87 | ✅ Principal |
| PATCH | `/api/fluxos/finalizar` | `anonymous` | infra/api/routes/CronRoutes.ts | 64 | ✅ Principal |
| PATCH | `/api/link` | `anonymous` | infra/api/routes/AutenticationsRoutes.ts | 462 | ✅ Principal |
| PATCH | `/api/notificar` | `anonymous` | infra/api/routes/CronRoutes.ts | 36 | ✅ Principal |
| PATCH | `/api/reenviar-links` | `anonymous` | infra/api/routes/LinkRoutes.ts | 62 | ✅ Principal |
| PATCH | `/api/verificar-certificado` | `anonymous` | infra/api/routes/AutenticationsRoutes.ts | 529 | ✅ Principal |
| PATCH | `/api/verificar-certificado-nuvem` | `anonymous` | infra/api/routes/AutenticationsRoutes.ts | 575 | ✅ Principal |
| PATCH | `/api/verificar-otp` | `anonymous` | infra/api/routes/AutenticationsRoutes.ts | 383 | ✅ Principal |
| POST | `/api/clientes` | `anonymous` | infra/api/routes/ClienteRoutes.ts | 123 | ✅ Principal |
| POST | `/api/contas/perfil/:perfil` | `anonymous` | infra/api/routes/ContaRoutes.ts | 69 | ✅ Principal |
| POST | `/api/documentos` | `anonymous` | infra/api/routes/DocumentoRoutes.ts | 64 | ✅ Principal |
| POST | `/api/fluxos` | `anonymous` | infra/api/routes/FluxoRoutes.ts | 61 | ✅ Principal |
| POST | `/api/fluxos/adicionar` | `anonymous` | infra/api/routes/FluxoRoutes.ts | 95 | ✅ Principal |
| POST | `/api/grupos` | `anonymous` | infra/api/routes/GrupoRoutes.ts | 62 | ✅ Principal |
| POST | `/api/verify-authentication` | `anonymous` | infra/api/routes/AutenticationsRoutes.ts | 195 | ✅ Principal |
| POST | `/api/verify-registration` | `anonymous` | infra/api/routes/AutenticationsRoutes.ts | 139 | ✅ Principal |
| PUT | `/api/clientes/:id` | `anonymous` | infra/api/routes/ClienteRoutes.ts | 160 | ✅ Principal |
| PUT | `/api/contas/perfil/:perfil/:id` | `anonymous` | infra/api/routes/ContaRoutes.ts | 135 | ✅ Principal |
| PUT | `/api/fluxos/:id` | `anonymous` | infra/api/routes/FluxoRoutes.ts | 152 | ✅ Principal |
| PUT | `/api/grupos/:id` | `anonymous` | infra/api/routes/GrupoRoutes.ts | 119 | ✅ Principal |
| PUT | `/api/login-sistema` | `anonymous` | infra/api/routes/AutenticationsRoutes.ts | 233 | ✅ Principal |
| PUT | `/api/logout` | `anonymous` | infra/api/routes/AutenticationsRoutes.ts | 600 | ✅ Principal |
| PUT | `/api/token` | `anonymous` | infra/api/routes/AutenticationsRoutes.ts | 419 | ✅ Principal |
