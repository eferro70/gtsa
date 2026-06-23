# Relatório de Análise de API - java

## Resumo

- **Total de endpoints encontrados:** 80
- **Endpoints principais:** 80
- **Endpoints auxiliares:** 0
- **Métodos HTTP:** DELETE, GET, POST, PUT

## Endpoints por Método

- **DELETE:** 2
- **GET:** 24
- **POST:** 49
- **PUT:** 5

## Lista de Endpoints

| Método | Path | Handler | Arquivo | Linha | Tipo |
|--------|------|---------|---------|-------|------|
| DELETE | `/applications/{clientId}/activation` | `deleteOauthClientApplication` | app/src/main/java/br/gov/serpro/smartcert/rest/oauth2/V1ApplicationREST.java | 99 | ✅ Principal |
| DELETE | `/applications/{clientId}/redirect-uris` | `deleteRedirectUri` | app/src/main/java/br/gov/serpro/smartcert/rest/oauth2/V1ApplicationREST.java | 155 | ✅ Principal |
| GET | `/aplicativos/solicitacao/assinatura/{id_solicitacao}/status` | `verificarStatusDaAssinatura` | app/src/main/java/br/gov/serpro/smartcert/rest/app/AplicativoREST.java | 155 | ✅ Principal |
| GET | `/aplicativos/solicitacao/autenticacao/{id_solicitacao}/status` | `verificarStatusDaAutenticacao` | app/src/main/java/br/gov/serpro/smartcert/rest/app/AplicativoREST.java | 92 | ✅ Principal |
| GET | `/applications/{clientId}` | `getOauthClientApplication` | app/src/main/java/br/gov/serpro/smartcert/rest/oauth2/V1ApplicationREST.java | 78 | ✅ Principal |
| GET | `/authorize/code` | `getCode` | app/src/main/java/br/gov/serpro/smartcert/rest/oauth/api/AuthorizeREST.java | 370 | ✅ Principal |
| GET | `/authorize/dispositivo/{dispositivo}/authorization/info` | `getAuthorizationInfo` | app/src/main/java/br/gov/serpro/smartcert/rest/oauth/api/AuthorizeREST.java | 393 | ✅ Principal |
| GET | `/authorize/session-scope/periods` | `getPeriods` | app/src/main/java/br/gov/serpro/smartcert/rest/oauth/api/AuthorizeREST.java | 245 | ✅ Principal |
| GET | `/dispositivos/cadastrar` | `verificarStatusPedidoSCDSECadastrarDispositivo` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 284 | ✅ Principal |
| GET | `/dispositivos/pedidos` | `consultarPedidos` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 170 | ✅ Principal |
| GET | `/dispositivos/timestamp/agora` | `getTimestampAgora` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 275 | ✅ Principal |
| GET | `/dispositivos/{dispositivo}/access-token-sem-expiracao` | `obterAccessTokenSemExpiracao` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 826 | ✅ Principal |
| GET | `/dispositivos/{dispositivo}/aplicativos/assinatura` | `obterSituacaoSolicitacoesAssinatura` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoParaAPIAplicativosREST.java | 179 | ✅ Principal |
| GET | `/dispositivos/{dispositivo}/aplicativos/assinatura/{id}` | `obterDadosAssinaturaParaAplicativo` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoParaAPIAplicativosREST.java | 164 | ✅ Principal |
| GET | `/dispositivos/{dispositivo}/aplicativos/autenticacao` | `obterSituacaoSolicitacoesAutenticacao` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoParaAPIAplicativosREST.java | 147 | ✅ Principal |
| GET | `/dispositivos/{dispositivo}/aplicativos/autenticacao/{id}` | `obterDadosAutenticacaoParaAplicativo` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoParaAPIAplicativosREST.java | 129 | ✅ Principal |
| GET | `/dispositivos/{dispositivo}/certificados` | `listarCertificadosPorDispositivo` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 519 | ✅ Principal |
| GET | `/dispositivos/{dispositivo}/certificados/{certificadoId}/email-recuperacao/verificar` | `verificarVinculoContatoEmail` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 481 | ✅ Principal |
| GET | `/dispositivos/{dispositivo}/certificados/{certificadoId}/sessoes-assinatura` | `listarSessoesAssinaturaPorCertificado` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 988 | ✅ Principal |
| GET | `/dispositivos/{dispositivo}/certificados/{id}/dispositivos` | `listarDispositivosPorCertificado` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 534 | ✅ Principal |
| GET | `/dispositivos/{dispositivo}/drivers/assinatura` | `obterSituacaoAutenticacoesDriver` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoParaDriverREST.java | 72 | ✅ Principal |
| GET | `/dispositivos/{dispositivo}/drivers/solicitacoes-assinatura-pendentes` | `obterSolicitacoesAssinaturaAguardandoNaoExpiradas` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoParaDriverREST.java | 89 | ✅ Principal |
| GET | `/dispositivos/{dispositivo}/maquinas` | `listarMaquinasPorDispositivo` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 550 | ✅ Principal |
| GET | `/dispositivos/{dispositivo}/transacoes/{certificadoId}` | `listarTransacoesPorCertificadoViaDispositivo` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 634 | ✅ Principal |
| GET | `/drivers/assinatura/{id}` | `verificarStatusDoDesafio` | app/src/main/java/br/gov/serpro/smartcert/rest/DriverREST.java | 115 | ✅ Principal |
| GET | `/drivers/certificados` | `solicitarListaDeCertificadosDisponiveis` | app/src/main/java/br/gov/serpro/smartcert/rest/DriverREST.java | 71 | ✅ Principal |
| POST | `/aplicativos/solicitacao/assinatura` | `solicitarAssinatura` | app/src/main/java/br/gov/serpro/smartcert/rest/app/AplicativoREST.java | 135 | ✅ Principal |
| POST | `/aplicativos/solicitacao/autenticacao/ni/{ni}` | `solicitarAutenticacao` | app/src/main/java/br/gov/serpro/smartcert/rest/app/AplicativoREST.java | 71 | ✅ Principal |
| POST | `/applications/{clientId}/activation` | `activateOauthClientApplication` | app/src/main/java/br/gov/serpro/smartcert/rest/oauth2/V1ApplicationREST.java | 63 | ✅ Principal |
| POST | `/applications/{clientId}/redirect-uris` | `createRedirectUri` | app/src/main/java/br/gov/serpro/smartcert/rest/oauth2/V1ApplicationREST.java | 137 | ✅ Principal |
| POST | `/atualizacao-serproid-desktop/enviar-emails` | `enviarEmails` | app/src/main/java/br/gov/serpro/smartcert/rest/intra/AtualizacaoSerproIDDesktopREST.java | 28 | ✅ Principal |
| POST | `/authorize/deny` | `denyAuthorizationFromWeb` | app/src/main/java/br/gov/serpro/smartcert/rest/oauth/api/AuthorizeREST.java | 566 | ✅ Principal |
| POST | `/authorize/dispositivo/{dispositivo}/authorization/deny` | `denyAuthorizationFromMobile` | app/src/main/java/br/gov/serpro/smartcert/rest/oauth/api/AuthorizeREST.java | 548 | ✅ Principal |
| POST | `/authorize/dispositivo/{dispositivo}/login-otp-access-token` | `loginOTPAccessToken` | app/src/main/java/br/gov/serpro/smartcert/rest/oauth/api/AuthorizeREST.java | 449 | ✅ Principal |
| POST | `/authorize/dispositivo/{dispositivo}/login-otp-pin` | `loginOTPPin` | app/src/main/java/br/gov/serpro/smartcert/rest/oauth/api/AuthorizeREST.java | 416 | ✅ Principal |
| POST | `/authorize/login-otp` | `loginOtp` | app/src/main/java/br/gov/serpro/smartcert/rest/oauth/api/AuthorizeREST.java | 270 | ✅ Principal |
| POST | `/authorize/login-pin` | `loginPin` | app/src/main/java/br/gov/serpro/smartcert/rest/oauth/api/AuthorizeREST.java | 334 | ✅ Principal |
| POST | `/authorize/send-recover-mail/certificado/{idCertificado}` | `sendRecoverMail` | app/src/main/java/br/gov/serpro/smartcert/rest/oauth/api/AuthorizeREST.java | 580 | ✅ Principal |
| POST | `/dispositivos/cadastrar-com-credencial-pedido/pedido/{numeroReferencia}` | `cadastrarComCredencial` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 260 | ✅ Principal |
| POST | `/dispositivos/email/otp/enviar` | `enviarEmailOTP` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 178 | ✅ Principal |
| POST | `/dispositivos/otp/validar` | `validarOTP` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 248 | ✅ Principal |
| POST | `/dispositivos/sms/otp/enviar` | `solicitarConfirmacaoTelefoneCelular` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 189 | ✅ Principal |
| POST | `/dispositivos/{dispositivo}/aplicativos/assinatura/{id}` | `assinarParaAplicativo` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoParaAPIAplicativosREST.java | 103 | ✅ Principal |
| POST | `/dispositivos/{dispositivo}/aplicativos/assinatura/{id}` | `recusarAssinaturaParaAplicativo` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoParaAPIAplicativosREST.java | 117 | ✅ Principal |
| POST | `/dispositivos/{dispositivo}/aplicativos/assinatura/{id}/access-token` | `assinarParaAplicativoAccessToken` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoParaAPIAplicativosREST.java | 89 | ✅ Principal |
| POST | `/dispositivos/{dispositivo}/aplicativos/autenticacao/{id}` | `autenticarParaAplicativo` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoParaAPIAplicativosREST.java | 60 | ✅ Principal |
| POST | `/dispositivos/{dispositivo}/aplicativos/autenticacao/{id}` | `recusarAutenticarParaAplicativo` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoParaAPIAplicativosREST.java | 75 | ✅ Principal |
| POST | `/dispositivos/{dispositivo}/aplicativos/autenticacao/{id}/access-token` | `autenticarParaAplicativoAccessToken` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoParaAPIAplicativosREST.java | 45 | ✅ Principal |
| POST | `/dispositivos/{dispositivo}/assinar` | `assinarDocumento` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 661 | ✅ Principal |
| POST | `/dispositivos/{dispositivo}/assinar/access-token` | `assinarDocumentoAccessToken` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 673 | ✅ Principal |
| POST | `/dispositivos/{dispositivo}/assinar/pdf` | `assinarPdf` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 685 | ✅ Principal |
| POST | `/dispositivos/{dispositivo}/assinar/pdf/access-token` | `assinarPdfAccessToken` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 697 | ✅ Principal |
| POST | `/dispositivos/{dispositivo}/certificados` | `emitirCertificadoComSenhaCodigo` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 411 | ✅ Principal |
| POST | `/dispositivos/{dispositivo}/certificados/pre-emissao` | `preEmissao` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 309 | ✅ Principal |
| POST | `/dispositivos/{dispositivo}/certificados/{certificadoId}/email-recuperacao` | `solicitarVinculoContatoEmail` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 436 | ✅ Principal |
| POST | `/dispositivos/{dispositivo}/certificados/{certificadoId}/email-recuperacao/access-token` | `solicitarVinculoContatoEmailAccessToken` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 458 | ✅ Principal |
| POST | `/dispositivos/{dispositivo}/certificados/{certificado}` | `desvincularCertificado` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 585 | ✅ Principal |
| POST | `/dispositivos/{dispositivo}/certificados/{certificado}/dispositivos/{dispositivo_delete}` | `desvincularCertificadoDeOutroDispositivo` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 596 | ✅ Principal |
| POST | `/dispositivos/{dispositivo}/certificados/{certificado}/dispositivos/{dispositivo_delete}/access-token` | `desvincularCertificadoDeOutroDispositivoAccessToken` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 609 | ✅ Principal |
| POST | `/dispositivos/{dispositivo}/certificados/{idCertificado}/enviar-email-recuperacao` | `solicitarEmailRedefinicaoPin` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 500 | ✅ Principal |
| POST | `/dispositivos/{dispositivo}/chave/instalacao/{idInstalacao}` | `gerarChaveInstalacao` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 650 | ✅ Principal |
| POST | `/dispositivos/{dispositivo}/checagem-pin` | `checagemPin` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 939 | ✅ Principal |
| POST | `/dispositivos/{dispositivo}/drivers/assinatura/{id}` | `responderSolicitacaoAssinatura` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoParaDriverREST.java | 44 | ✅ Principal |
| POST | `/dispositivos/{dispositivo}/drivers/assinatura/{id}/access-token` | `responderSolicitacaoAssinaturaAccessToken` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoParaDriverREST.java | 58 | ✅ Principal |
| POST | `/dispositivos/{dispositivo}/maquinas` | `autorizarMaquinaParaDispositivo` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 564 | ✅ Principal |
| POST | `/dispositivos/{dispositivo}/maquinas/{maquina}` | `desautorizarMaquinaParaDispositivo` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 622 | ✅ Principal |
| POST | `/dispositivos/{dispositivo}/pedido/{numeroReferencia}/instalar-certificado` | `emitirCertificadoComCredencialInstalacao` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 375 | ✅ Principal |
| POST | `/dispositivos/{dispositivo}/pedido/{numeroReferencia}/pre-instalacao-certificado` | `preEmissaoCredencialInstalacao` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 328 | ✅ Principal |
| POST | `/dispositivos/{dispositivo}/pedido/{numeroReferencia}/validar/biometria/instalacao` | `validarBiometriaParaInstalar` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 229 | ✅ Principal |
| POST | `/dispositivos/{dispositivo}/sessao-assinatura/{idAutorizacao}` | `revogarSessaoAssinatura` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 1005 | ✅ Principal |
| POST | `/dispositivos/{dispositivo}/sessao-assinatura/{idAutorizacao}/access-token` | `revogarSessaoAssinaturaAccessToken` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 1019 | ✅ Principal |
| POST | `/dispositivos/{dispositivo}/v2/pedido/{numeroReferencia}/validar/biometria/instalacao` | `validarBiometriasFaciaisParaInstalar` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 200 | ✅ Principal |
| POST | `/drivers/assinatura` | `enviarDesafioParaAssinatura` | app/src/main/java/br/gov/serpro/smartcert/rest/DriverREST.java | 101 | ✅ Principal |
| POST | `/drivers/maquina` | `criarMaquina` | app/src/main/java/br/gov/serpro/smartcert/rest/DriverREST.java | 62 | ✅ Principal |
| POST | `/v2/drivers/assinatura` | `solicitarAssinatura` | app/src/main/java/br/gov/serpro/smartcert/rest/DriverRESTV2.java | 32 | ✅ Principal |
| PUT | `/applications/{clientId}` | `updateOauthClientApplication` | app/src/main/java/br/gov/serpro/smartcert/rest/oauth2/V1ApplicationREST.java | 118 | ✅ Principal |
| PUT | `/dispositivos/{dispositivo}/atualizar-cadastro-legado` | `atualizarCadastroLegado` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 896 | ✅ Principal |
| PUT | `/dispositivos/{dispositivo}/atualizar-push-id` | `atualizarPushId` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 400 | ✅ Principal |
| PUT | `/dispositivos/{dispositivo}/renovar-atestado` | `renovarAtestado` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 861 | ✅ Principal |
| PUT | `/dispositivos/{dispositivo}/renovar-token` | `renovarToken` | app/src/main/java/br/gov/serpro/smartcert/rest/DispositivoREST.java | 886 | ✅ Principal |
