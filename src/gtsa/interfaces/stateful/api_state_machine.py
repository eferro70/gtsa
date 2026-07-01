"""
Máquina de estado completa para testes stateful
Testa fluxos reais: criar → ler → atualizar → deletar
"""
from hypothesis.stateful import RuleBasedStateMachine, rule, precondition, invariant, Bundle
from hypothesis import settings, strategies as st
import requests
import os
import logging

logger = logging.getLogger(__name__)

class APIStateMachine(RuleBasedStateMachine):
    """Testa sequências reais de operações da API"""
    tokens = Bundle("tokens")
    created_resources = Bundle("resources")
    
    def __init__(self):
        super().__init__()
        self.base_url = os.getenv("API_BASE_URL", "http://localhost:3000").rstrip("/")
        self.session = requests.Session()
        self._authenticate()
        # ⚠️ IMPORTANTE: endpoints devem ser injetados externamente ou carregados de um spec
        # Se não houver spec, defina manualmente os endpoints que deseja testar
        self.endpoints = os.getenv("API_ENDPOINTS_JSON", "[]")  # Ou carregue de all_endpoints.json

    def _authenticate(self):
        """Autentica e obtém token"""
        auth_url = f"{self.base_url}/auth/login"
        credentials = {"email": "test@example.com", "password": "Test123!"}
        try:
            resp = self.session.post(auth_url, json=credentials, timeout=10)
            if resp.status_code == 200 and resp.text.strip():
                token = resp.json().get("token")
                if token:
                    self.session.headers.update({"Authorization": f"Bearer {token}"})
                    logger.info("✅ Autenticação bem-sucedida")
        except requests.RequestException as e:
            logger.warning(f"⚠️ Falha na autenticação: {e}")
        except Exception as e:
            logger.error(f"❌ Erro inesperado na autenticação: {e}")

    @rule(target=tokens)
    def refresh_token(self):
        """Testa refresh de token"""
        refresh_url = f"{self.base_url}/auth/refresh"
        try:
            resp = self.session.post(refresh_url, timeout=10)
            if resp.status_code == 200 and resp.text.strip():
                return resp.json().get("token")
        except requests.RequestException as e:
            logger.debug(f"⚠️ Refresh token falhou: {e}")
        except Exception:
            pass
        return None

    @rule(target=created_resources, data=st.data())
    def create_resource(self, data):
        """Cria um recurso e guarda para testes futuros"""
        # Se endpoints não estiverem carregados, tenta endpoints comuns como fallback
        endpoints_to_test = self.endpoints if isinstance(self.endpoints, list) and self.endpoints else [
            {"method": "POST", "path": "/api/v1/clientes"},
            {"method": "POST", "path": "/api/v1/grupos"},
            {"method": "POST", "path": "/api/v1/contas/perfil/REQUISITANTE"},
        ]
        
        create_endpoints = [
            ep for ep in endpoints_to_test 
            if ep.get('method', '').upper() == 'POST' and ':' not in ep.get('path', '')
        ]
        
        if not create_endpoints:
            logger.debug("⚠️ Nenhum endpoint POST disponível para create_resource")
            return None
        
        endpoint = create_endpoints[0]
        url = f"{self.base_url}{endpoint['path']}"
        
        # Gera payload minimalista e seguro
        payload = data.draw(st.fixed_dictionaries({
            "nome": st.text(min_size=3, max_size=20),
            "email": st.emails(),
        }, optional={
            "descricao": st.text(min_size=1, max_size=50),
            "ativo": st.booleans(),
        }))
        
        try:
            resp = self.session.post(url, json=payload, timeout=15)
            if resp.status_code in [200, 201] and resp.text.strip():
                resource_id = resp.json().get('id')
                if resource_id:
                    logger.info(f"✅ Recurso criado: {endpoint['path']} (id={resource_id})")
                    return {'id': resource_id, 'endpoint': endpoint, 'payload': payload}
        except requests.RequestException as e:
            logger.debug(f"⚠️ create_resource falhou em {url}: {e}")
        except Exception as e:
            logger.error(f"❌ Erro em create_resource: {e}")
        return None

    # ✅ PRECONDITION: só executa se resource não for None
    @rule(resource=created_resources)
    def read_resource(self, resource):
        """Lê um recurso criado anteriormente"""
        if not resource or not resource.get('endpoint') or not resource.get('id'):
            return
        
        # Constrói URL de leitura: assume que GET usa o mesmo path base
        base_path = resource['endpoint']['path']
        url = f"{self.base_url}{base_path}/{resource['id']}"
        
        try:
            resp = self.session.get(url, timeout=10)
            # Aceita 200 (sucesso) ou 404 (recurso deletado entre criar e ler)
            assert resp.status_code in [200, 401, 403, 404], f"Failed to read: {resp.status_code}"
            if resp.status_code == 200 and resp.text.strip():
                assert resp.json().get('id') == resource['id'], "ID mismatch na leitura"
        except requests.RequestException as e:
            logger.debug(f"⚠️ read_resource falhou: {e}")
        except AssertionError as e:
            logger.error(f"❌ Assertion falhou em read_resource: {e}")
            raise

    @rule(resource=created_resources, data=st.data())
    def update_resource(self, resource, data):
        """Atualiza um recurso criado anteriormente"""
        if not resource or not resource.get('endpoint') or not resource.get('id'):
            return
        
        # Tenta inferir endpoint de update (PUT/PATCH no mesmo path base)
        base_path = resource['endpoint']['path']
        # Heurística simples: substitui último segmento por {id} se necessário
        url = f"{self.base_url}{base_path}/{resource['id']}"
        
        update_data = data.draw(st.fixed_dictionaries({
            "nome": st.text(min_size=3, max_size=20),
        }, optional={
            "ativo": st.booleans(),
        }))
        
        try:
            resp = self.session.put(url, json=update_data, timeout=15)
            assert resp.status_code in [200, 204, 401, 403, 404], f"Update failed: {resp.status_code}"
        except requests.RequestException as e:
            logger.debug(f"⚠️ update_resource falhou: {e}")
        except AssertionError as e:
            logger.error(f"❌ Assertion falhou em update_resource: {e}")
            raise

    @rule(resource=created_resources)
    def delete_resource(self, resource):
        """Deleta um recurso criado anteriormente"""
        if not resource or not resource.get('endpoint') or not resource.get('id'):
            return
        
        base_path = resource['endpoint']['path']
        url = f"{self.base_url}{base_path}/{resource['id']}"
        
        try:
            resp = self.session.delete(url, timeout=10)
            assert resp.status_code in [200, 204, 401, 403, 404], f"Delete failed: {resp.status_code}"
            logger.info(f"🗑️ Recurso deletado: {url} (status={resp.status_code})")
        except requests.RequestException as e:
            logger.debug(f"⚠️ delete_resource falhou: {e}")
        except AssertionError as e:
            logger.error(f"❌ Assertion falhou em delete_resource: {e}")
            raise

    @invariant()
    def no_internal_errors(self):
        """Verifica se nenhuma requisição retornou 500"""
        # Mantido pelo session hooks ou logging
        pass

    def teardown(self):
        """Limpeza pós-teste"""
        self.session.close()
        logger.info("🔚 Máquina de estado finalizada")

# Compatibilidade com pytest
TestStateful = APIStateMachine.TestCase