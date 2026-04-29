# Relatório de Análise de API Endpoints

Data da análise: 2026-04-29 12:35:22

Projeto: `/home/s231991563/projetos/neosigner/controlador-api/src`

## Resumo

- 📁 Arquivos analisados: **609**
- 🎯 Arquivos com endpoints: **14**
- 🔗 Total de endpoints encontrados: **77**
- ❌ Erros encontrados: **0**

## Endpoints Encontrados

### 📄 `app.ts`

| Método | Path | Handler | Parâmetros |
|--------|------|---------|------------|
| USE | `/swagger/custom` | `anonymous` | - |
| USE | `/swagger/specs` | `anonymous` | - |
| USE | `/swagger/scripts` | `anonymous` | - |
| USE | `/swagger` | `anonymous` | - |
| GET | `/metrics` | `anonymous` | - |

### 📄 `infra/api/routes/HelloRoutes.ts`

| Método | Path | Handler | Parâmetros |
|--------|------|---------|------------|
| GET | `/api/controlador/hello` | `anonymous` | - |
| GET | `/api/controlador/meu-ip` | `anonymous` | - |

### 📄 `infra/api/routes/ContaRoutes.ts`

| Método | Path | Handler | Parâmetros |
|--------|------|---------|------------|
| POST | `/api/contas/perfil/:perfil` | `anonymous` | - |
| PUT | `/api/contas/perfil/:perfil/:id` | `anonymous` | - |
| GET | `/api/contas/perfil/:perfil` | `anonymous` | - |
| GET | `/api/contas/id/:id` | `anonymous` | - |
| GET | `/api/contas` | `anonymous` | - |
| GET | `/api/contas/sumario` | `anonymous` | - |
| GET | `/api/contas/codigo/:codigo` | `anonymous` | - |
| PATCH | `/api/contas/reenviar-credenciais-sistema` | `anonymous` | - |

### 📄 `infra/api/routes/LinkRoutes.ts`

| Método | Path | Handler | Parâmetros |
|--------|------|---------|------------|
| PATCH | `/api/reenviar-links` | `anonymous` | - |

### 📄 `infra/api/routes/DocumentoRoutes.ts`

| Método | Path | Handler | Parâmetros |
|--------|------|---------|------------|
| POST | `/api/documentos` | `anonymous` | - |
| DELETE | `/api/documentos/:id` | `anonymous` | - |

### 📄 `infra/api/routes/WebhookRoutes.ts`

| Método | Path | Handler | Parâmetros |
|--------|------|---------|------------|
| GET | `/api/webhook/validar/:idRequisitante` | `anonymous` | - |

### 📄 `infra/api/routes/FluxoRoutes.ts`

| Método | Path | Handler | Parâmetros |
|--------|------|---------|------------|
| POST | `/api/fluxos` | `anonymous` | - |
| POST | `/api/fluxos/adicionar` | `anonymous` | - |
| PUT | `/api/fluxos/:id` | `anonymous` | - |
| DELETE | `/api/fluxo/:id` | `anonymous` | - |
| PATCH | `/api/fluxos/:id/iniciar` | `anonymous` | - |
| PATCH | `/api/fluxos/:id/finalizar` | `anonymous` | - |
| PATCH | `/api/fluxos/:id/cancelar` | `anonymous` | - |
| PATCH | `/api/fluxos/:id/arquivar` | `anonymous` | - |
| GET | `/api/fluxos` | `anonymous` | - |
| GET | `/api/fluxo/:id` | `anonymous` | - |
| GET | `/api/fluxos/:id/hashes-documentos/:algoritmo` | `anonymous` | - |
| GET | `/api/fluxos/arquivados` | `anonymous` | - |
| GET | `/api/fluxos/:id/interessados` | `anonymous` | - |
| GET | `/api/resposta/:id` | `anonymous` | - |
| GET | `/api/fluxos-interessado` | `anonymous` | - |
| GET | `/api/fluxos/:id/sumario` | `anonymous` | - |

### 📄 `infra/api/routes/MonitoracaoRoutes.ts`

| Método | Path | Handler | Parâmetros |
|--------|------|---------|------------|
| GET | `/api/monitoracao/dlqs` | `anonymous` | - |

### 📄 `infra/api/routes/ResponderFluxoRoutes.ts`

| Método | Path | Handler | Parâmetros |
|--------|------|---------|------------|
| PATCH | `/api/fluxos/:id/rejeitar` | `anonymous` | - |
| PATCH | `/api/fluxos/:id/assinar` | `anonymous` | - |
| PATCH | `/api/fluxos/:id/revisar` | `anonymous` | - |
| PATCH | `/api/fluxos/:id/revisao` | `anonymous` | - |
| PATCH | `/api/fluxos/:id/assinar-serpro-id` | `anonymous` | - |
| PATCH | `/api/fluxos/:id/assinar-bird-id` | `anonymous` | - |
| PATCH | `/api/fluxos/:id/assinar-safe-id` | `anonymous` | - |
| PATCH | `/api/fluxos/:id/assinar-vidaas` | `anonymous` | - |
| PATCH | `/api/fluxos/:id/assinar-ds-cloud` | `anonymous` | - |
| PATCH | `/api/fluxos/:id/assinar-syn-id` | `anonymous` | - |
| PATCH | `/api/fluxos/:id/assinar-desktop/:algoritmo` | `anonymous` | - |

### 📄 `infra/api/routes/DevelopRoutes.ts`

| Método | Path | Handler | Parâmetros |
|--------|------|---------|------------|
| GET | `/api/getlink` | `anonymous` | - |

### 📄 `infra/api/routes/ClienteRoutes.ts`

| Método | Path | Handler | Parâmetros |
|--------|------|---------|------------|
| GET | `/api/clientes/:id` | `anonymous` | - |
| GET | `/api/clientes` | `anonymous` | - |
| POST | `/api/clientes` | `anonymous` | - |
| PUT | `/api/clientes/:id` | `anonymous` | - |
| GET | `/api/clientes/:id` | `anonymous` | - |

### 📄 `infra/api/routes/AutenticationsRoutes.ts`

| Método | Path | Handler | Parâmetros |
|--------|------|---------|------------|
| GET | `/api/authentication-options` | `anonymous` | - |
| POST | `/api/verify-registration` | `anonymous` | - |
| POST | `/api/verify-authentication` | `anonymous` | - |
| PUT | `/api/login-sistema` | `anonymous` | - |
| GET | `/api/listar-contas/:email` | `anonymous` | - |
| GET | `/api/confirmacao-conta/:idConta` | `anonymous` | - |
| PATCH | `/api/enviar-otp` | `anonymous` | - |
| PATCH | `/api/verificar-otp` | `anonymous` | - |
| PUT | `/api/token` | `anonymous` | - |
| PATCH | `/api/link` | `anonymous` | - |
| GET | `/api/autenticar-certificado` | `anonymous` | - |
| PATCH | `/api/verificar-certificado` | `anonymous` | - |
| PATCH | `/api/verificar-certificado-nuvem` | `anonymous` | - |
| PUT | `/api/logout` | `anonymous` | - |
| GET | `/api/confirmacao-interessado/:email/:idConta` | `anonymous` | - |

### 📄 `infra/api/routes/GrupoRoutes.ts`

| Método | Path | Handler | Parâmetros |
|--------|------|---------|------------|
| POST | `/api/grupos` | `anonymous` | - |
| PUT | `/api/grupos/:id` | `anonymous` | - |
| GET | `/api/grupos/id/:id` | `anonymous` | - |
| GET | `/api/grupos` | `anonymous` | - |
| GET | `/api/grupos-requisitante` | `anonymous` | - |
| GET | `/api/grupos-gestor-mais-requisitante` | `anonymous` | - |

### 📄 `infra/api/routes/CronRoutes.ts`

| Método | Path | Handler | Parâmetros |
|--------|------|---------|------------|
| PATCH | `/api/notificar` | `anonymous` | - |
| PATCH | `/api/fluxos/finalizar` | `anonymous` | - |
| PATCH | `/api/fluxos/arquivar` | `anonymous` | - |

