# Relatório OpenAPI

## Resumo

- **Título:** API Gerada
- **Versão:** 1.0.0
- **Total de paths:** 71
- **Total de operações:** 78
- **Servidor:** https://hom.serproid.serpro.gov.br

## Métodos por Tipo

- **DELETE:** 2
- **GET:** 24
- **POST:** 47
- **PUT:** 5

## Lista de Endpoints

| Método | Path | Summary |
|--------|------|---------|
| POST | `/oauth/v1/oauth/aplicativos/solicitacao/assinatura` | endpoint |
| GET | `/oauth/v1/oauth/aplicativos/solicitacao/assinatura/{id_solicitacao}/status` | endpoint |
| POST | `/oauth/v1/oauth/aplicativos/solicitacao/autenticacao/ni/{ni}` | endpoint |
| GET | `/oauth/v1/oauth/aplicativos/solicitacao/autenticacao/{id_solicitacao}/status` | endpoint |
| GET | `/oauth/v1/oauth/applications/{clientId}` | endpoint |
| PUT | `/oauth/v1/oauth/applications/{clientId}` | endpoint |
| POST | `/oauth/v1/oauth/applications/{clientId}/activation` | endpoint |
| DELETE | `/oauth/v1/oauth/applications/{clientId}/activation` | endpoint |
| POST | `/oauth/v1/oauth/applications/{clientId}/redirect-uris` | endpoint |
| DELETE | `/oauth/v1/oauth/applications/{clientId}/redirect-uris` | endpoint |
| POST | `/oauth/v1/oauth/atualizacao-serproid-desktop/enviar-emails` | endpoint |
| GET | `/oauth/v1/oauth/authorize/code` | endpoint |
| POST | `/oauth/v1/oauth/authorize/deny` | endpoint |
| POST | `/oauth/v1/oauth/authorize/dispositivo/{dispositivo}/authorization/deny` | endpoint |
| GET | `/oauth/v1/oauth/authorize/dispositivo/{dispositivo}/authorization/info` | endpoint |
| POST | `/oauth/v1/oauth/authorize/dispositivo/{dispositivo}/login-otp-access-token` | endpoint |
| POST | `/oauth/v1/oauth/authorize/dispositivo/{dispositivo}/login-otp-pin` | endpoint |
| POST | `/oauth/v1/oauth/authorize/login-otp` | endpoint |
| POST | `/oauth/v1/oauth/authorize/login-pin` | endpoint |
| POST | `/oauth/v1/oauth/authorize/send-recover-mail/certificado/{idCertificado}` | endpoint |
| GET | `/oauth/v1/oauth/authorize/session-scope/periods` | endpoint |
| GET | `/oauth/v1/oauth/dispositivos/cadastrar` | endpoint |
| POST | `/oauth/v1/oauth/dispositivos/cadastrar-com-credencial-pedido/pedido/{numeroReferencia}` | endpoint |
| POST | `/oauth/v1/oauth/dispositivos/email/otp/enviar` | endpoint |
| POST | `/oauth/v1/oauth/dispositivos/otp/validar` | endpoint |
| GET | `/oauth/v1/oauth/dispositivos/pedidos` | endpoint |
| POST | `/oauth/v1/oauth/dispositivos/sms/otp/enviar` | endpoint |
| GET | `/oauth/v1/oauth/dispositivos/timestamp/agora` | endpoint |
| GET | `/oauth/v1/oauth/dispositivos/{dispositivo}/access-token-sem-expiracao` | endpoint |
| GET | `/oauth/v1/oauth/dispositivos/{dispositivo}/aplicativos/assinatura` | endpoint |
| POST | `/oauth/v1/oauth/dispositivos/{dispositivo}/aplicativos/assinatura/{id}` | endpoint |
| GET | `/oauth/v1/oauth/dispositivos/{dispositivo}/aplicativos/assinatura/{id}` | endpoint |
| POST | `/oauth/v1/oauth/dispositivos/{dispositivo}/aplicativos/assinatura/{id}/access-token` | endpoint |
| GET | `/oauth/v1/oauth/dispositivos/{dispositivo}/aplicativos/autenticacao` | endpoint |
| POST | `/oauth/v1/oauth/dispositivos/{dispositivo}/aplicativos/autenticacao/{id}` | endpoint |
| GET | `/oauth/v1/oauth/dispositivos/{dispositivo}/aplicativos/autenticacao/{id}` | endpoint |
| POST | `/oauth/v1/oauth/dispositivos/{dispositivo}/aplicativos/autenticacao/{id}/access-token` | endpoint |
| POST | `/oauth/v1/oauth/dispositivos/{dispositivo}/assinar` | endpoint |
| POST | `/oauth/v1/oauth/dispositivos/{dispositivo}/assinar/access-token` | endpoint |
| POST | `/oauth/v1/oauth/dispositivos/{dispositivo}/assinar/pdf` | endpoint |
| POST | `/oauth/v1/oauth/dispositivos/{dispositivo}/assinar/pdf/access-token` | endpoint |
| PUT | `/oauth/v1/oauth/dispositivos/{dispositivo}/atualizar-cadastro-legado` | endpoint |
| PUT | `/oauth/v1/oauth/dispositivos/{dispositivo}/atualizar-push-id` | endpoint |
| POST | `/oauth/v1/oauth/dispositivos/{dispositivo}/certificados` | endpoint |
| GET | `/oauth/v1/oauth/dispositivos/{dispositivo}/certificados` | endpoint |
| POST | `/oauth/v1/oauth/dispositivos/{dispositivo}/certificados/pre-emissao` | endpoint |
| POST | `/oauth/v1/oauth/dispositivos/{dispositivo}/certificados/{certificadoId}/email-recuperacao` | endpoint |
| POST | `/oauth/v1/oauth/dispositivos/{dispositivo}/certificados/{certificadoId}/email-recuperacao/access-token` | endpoint |
| GET | `/oauth/v1/oauth/dispositivos/{dispositivo}/certificados/{certificadoId}/email-recuperacao/verificar` | endpoint |
| GET | `/oauth/v1/oauth/dispositivos/{dispositivo}/certificados/{certificadoId}/sessoes-assinatura` | endpoint |
| POST | `/oauth/v1/oauth/dispositivos/{dispositivo}/certificados/{certificado}` | endpoint |
| POST | `/oauth/v1/oauth/dispositivos/{dispositivo}/certificados/{certificado}/dispositivos/{dispositivo_delete}` | endpoint |
| POST | `/oauth/v1/oauth/dispositivos/{dispositivo}/certificados/{certificado}/dispositivos/{dispositivo_delete}/access-token` | endpoint |
| POST | `/oauth/v1/oauth/dispositivos/{dispositivo}/certificados/{idCertificado}/enviar-email-recuperacao` | endpoint |
| GET | `/oauth/v1/oauth/dispositivos/{dispositivo}/certificados/{id}/dispositivos` | endpoint |
| POST | `/oauth/v1/oauth/dispositivos/{dispositivo}/chave/instalacao/{idInstalacao}` | endpoint |
| POST | `/oauth/v1/oauth/dispositivos/{dispositivo}/checagem-pin` | endpoint |
| GET | `/oauth/v1/oauth/dispositivos/{dispositivo}/drivers/assinatura` | endpoint |
| POST | `/oauth/v1/oauth/dispositivos/{dispositivo}/drivers/assinatura/{id}` | endpoint |
| POST | `/oauth/v1/oauth/dispositivos/{dispositivo}/drivers/assinatura/{id}/access-token` | endpoint |
| GET | `/oauth/v1/oauth/dispositivos/{dispositivo}/drivers/solicitacoes-assinatura-pendentes` | endpoint |
| GET | `/oauth/v1/oauth/dispositivos/{dispositivo}/maquinas` | endpoint |
| POST | `/oauth/v1/oauth/dispositivos/{dispositivo}/maquinas` | endpoint |
| POST | `/oauth/v1/oauth/dispositivos/{dispositivo}/maquinas/{maquina}` | endpoint |
| POST | `/oauth/v1/oauth/dispositivos/{dispositivo}/pedido/{numeroReferencia}/instalar-certificado` | endpoint |
| POST | `/oauth/v1/oauth/dispositivos/{dispositivo}/pedido/{numeroReferencia}/pre-instalacao-certificado` | endpoint |
| POST | `/oauth/v1/oauth/dispositivos/{dispositivo}/pedido/{numeroReferencia}/validar/biometria/instalacao` | endpoint |
| PUT | `/oauth/v1/oauth/dispositivos/{dispositivo}/renovar-atestado` | endpoint |
| PUT | `/oauth/v1/oauth/dispositivos/{dispositivo}/renovar-token` | endpoint |
| POST | `/oauth/v1/oauth/dispositivos/{dispositivo}/sessao-assinatura/{idAutorizacao}` | endpoint |
| POST | `/oauth/v1/oauth/dispositivos/{dispositivo}/sessao-assinatura/{idAutorizacao}/access-token` | endpoint |
| GET | `/oauth/v1/oauth/dispositivos/{dispositivo}/transacoes/{certificadoId}` | endpoint |
| POST | `/oauth/v1/oauth/dispositivos/{dispositivo}/v2/pedido/{numeroReferencia}/validar/biometria/instalacao` | endpoint |
| POST | `/oauth/v1/oauth/drivers/assinatura` | endpoint |
| GET | `/oauth/v1/oauth/drivers/assinatura/{id}` | endpoint |
| GET | `/oauth/v1/oauth/drivers/certificados` | endpoint |
| POST | `/oauth/v1/oauth/drivers/maquina` | endpoint |
| POST | `/oauth/v1/oauth/v2/drivers/assinatura` | endpoint |
