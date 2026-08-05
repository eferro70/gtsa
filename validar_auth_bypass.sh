#!/usr/bin/env bash
# Validação manual dos achados do Schemathesis (GTSA - Neosigner)
# Rodar contra o ambiente onde os testes foram executados (staging).
#
# Preencha as variáveis abaixo antes de rodar.
# BASE_URL: normalmente http://localhost se atrás do KrakenD local, ou a URL do gateway em staging.

BASE_URL="http://localhost"

# Token JWT válido (para comparação de baseline) — pegue um token real emitido pelo fluxo OAuth2/SerproID
VALID_TOKEN="COLE_UM_TOKEN_VALIDO_AQUI"

# Token propositalmente inválido/corrompido (o Schemathesis usa algo assim, mas com formato de JWT quebrado)
INVALID_TOKEN="eyJhbGciOiJIUzI1NiJ9.eyJmb28iOiJiYXIifQ.invalidsignature123"

echo "======================================================"
echo "1) GET /api/v1/getlink — auth ausente"
echo "======================================================"
curl -s -i -X GET \
  "${BASE_URL}/api/v1/getlink?email=emmanuel.ferro%40serpro.gov.br&idcliente=1ae08e30-d3d9-4230-be09-200663596bdf&idfluxo=4f85d55d-3cf0-4256-99f2-54bd1640b254" \
  | grep -Ei "^HTTP|^X-Krakend|^\{"
echo

echo "======================================================"
echo "2) GET /api/v1/getlink — auth INVÁLIDA (token quebrado)"
echo "======================================================"
curl -s -i -X GET \
  -H "Authorization: Bearer ${INVALID_TOKEN}" \
  "${BASE_URL}/api/v1/getlink?email=emmanuel.ferro%40serpro.gov.br&idcliente=1ae08e30-d3d9-4230-be09-200663596bdf&idfluxo=4f85d55d-3cf0-4256-99f2-54bd1640b254" \
  | grep -Ei "^HTTP|^X-Krakend|^\{"
echo

echo "======================================================"
echo "3) GET /api/v1/getlink — auth VÁLIDA (baseline, deve dar 200)"
echo "======================================================"
curl -s -i -X GET \
  -H "Authorization: Bearer ${VALID_TOKEN}" \
  "${BASE_URL}/api/v1/getlink?email=emmanuel.ferro%40serpro.gov.br&idcliente=1ae08e30-d3d9-4230-be09-200663596bdf&idfluxo=4f85d55d-3cf0-4256-99f2-54bd1640b254" \
  | grep -Ei "^HTTP|^X-Krakend|^\{"
echo

echo "======================================================"
echo "4) GET /api/v1/fluxos — auth INVÁLIDA"
echo "======================================================"
curl -s -i -X GET \
  -H "Authorization: Bearer ${INVALID_TOKEN}" \
  "${BASE_URL}/api/v1/fluxos" \
  | grep -Ei "^HTTP|^X-Krakend|^\{|^\["
echo

echo "======================================================"
echo "5) GET /api/v1/respostas-gerencial — auth INVÁLIDA"
echo "======================================================"
curl -s -i -X GET \
  -H "Authorization: Bearer ${INVALID_TOKEN}" \
  "${BASE_URL}/api/v1/respostas-gerencial?dataInicio=" \
  | grep -Ei "^HTTP|^X-Krakend|^\{"
echo

echo "======================================================"
echo "6) GET /api/v1/fluxos/{id}/interessados — auth INVÁLIDA"
echo "   (troque o id abaixo por um idFluxo real do seu ambiente)"
echo "======================================================"
ID_FLUXO="fac54101-d164-42d4-94d9-da993e3ad7cd"
curl -s -i -X GET \
  -H "Authorization: Bearer ${INVALID_TOKEN}" \
  "${BASE_URL}/api/v1/fluxos/${ID_FLUXO}/interessados" \
  | grep -Ei "^HTTP|^X-Krakend|^\[|^\{"
echo

echo "======================================================"
echo "6b) mesmo endpoint — sortDirection fora do enum (ASC/DESC)"
echo "    checar se a API valida o enum corretamente"
echo "======================================================"
curl -s -i -X GET \
  -H "Authorization: Bearer ${VALID_TOKEN}" \
  "${BASE_URL}/api/v1/fluxos/${ID_FLUXO}/interessados?sortDirection=INVALIDO" \
  | grep -Ei "^HTTP|^\{|^\["
echo

echo "======================================================"
echo "7) GET /api/v1/fluxos/arquivados?nome= — reproduzir o 500"
echo "======================================================"
curl -s -i -X GET \
  -H "Authorization: Bearer ${VALID_TOKEN}" \
  "${BASE_URL}/api/v1/fluxos/arquivados?nome=" \
  | grep -Ei "^HTTP|^\{"
echo

echo "======================================================"
echo "COMO INTERPRETAR:"
echo "- Se (1)/(2) retornarem 200 com corpo de dados reais -> auth bypass CONFIRMADO"
echo "  (o esperado é 401/403)."
echo "- Compare o header X-Krakend-Completed entre os testes 2 e 3:"
echo "  se vier 'false' no caso invalido mas a resposta ainda tiver corpo,"
echo "  é o mesmo padrao do disable_jwk_security ja visto na Neosigner."
echo "- (4) e (5): mesmo raciocinio para /fluxos e /respostas-gerencial."
echo "- (6): se retornar dados -> bypass. (6b): se retornar 200 em vez de"
echo "  400/422 -> falta de validacao de enum (baixo risco, mas vale corrigir)."
echo "- (7): confirma o 500 -> puxar stacktrace nos logs da aplicacao nesse horario."
echo "======================================================"
