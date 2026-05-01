#!/usr/bin/env python3
"""
step5_analyzer_unified.py
---------------------------
Script UNIFICADO para análise de segurança e enriquecimento de endpoints.

FUNCIONALIDADES:
1. Analisa riscos e detecta vulnerabilidades (OWASP API Top 10 2023 + SANS Top 25)
2. Enriquece com dados do OpenAPI/Swagger (summary, description)
3. Adiciona exemplos reais de requisição (de output/tests/dados/)
4. Adiciona roles de autorização (do arquivo de configuração do KrakenD)
5. Modo Híbrido: LLM (Ollama/Gatiator) + Heurística com fallback automático

SAÍDAS:
- src/application/pipeline/tests/enriched_endpoints.json (completo)
- output/final_security_report.md (relatório OWASP/SANS)

USO:
    # Apenas análise de segurança (mais rápido)
    python3 step5_analyzer_unified.py output/scan_*/all_endpoints.json --no-llm
    
    # Com enriquecimento OpenAPI
    python3 step5_analyzer_unified.py output/scan_*/all_endpoints.json --openapi docs/openapi.yaml
    
    # Completo (segurança + OpenAPI + exemplos + roles)
    python3 step5_analyzer_unified.py output/scan_*/all_endpoints.json --openapi docs/openapi.yaml --no-llm
"""

import json
import requests
import os
import time
import re
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from datetime import datetime

# Carrega variáveis do .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv não instalado. Variáveis do .env não serão carregadas automaticamente.")

# Tenta importar PyYAML para suporte a OpenAPI YAML
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    print("⚠️  PyYAML não instalado. Para arquivos OpenAPI YAML, instale: pip install pyyaml")


class VulnerabilityDatabase:
    """Gerencia o banco de vulnerabilidades OWASP API Top 10 2023 + SANS Top 25"""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path("config/vulnerability_mapping.json")
        self.mappings = self._load_mappings()
    
    def _load_mappings(self) -> Dict:
        """Carrega mapeamentos do arquivo JSON"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  Erro ao carregar {self.config_path}: {e}")
                return self._get_default_mappings()
        else:
            print(f"⚠️  Arquivo de mapeamento não encontrado: {self.config_path}")
            print("   Usando mapeamento padrão OWASP API Top 10 2023")
            return self._get_default_mappings()
    
    def _get_default_mappings(self) -> Dict:
        """Fallback com OWASP API Top 10 2023"""
        return {
            "version": "2.0",
            "standard": "OWASP API Security Top 10 2023",
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "vulnerabilities": {
                "bola": {
                    "name": "Broken Object Level Authorization",
                    "severity": "high",
                    "owasp": {"id": "API1:2023", "category": "Broken Object Level Authorization"},
                    "sans": {"cwe_id": "CWE-639", "category": "Porous Defenses", "rank": 3},
                    "remediation": "Implementar verificações de autorização para cada objeto acessado."
                },
                "bfla": {
                    "name": "Broken Function Level Authorization",
                    "severity": "high",
                    "owasp": {"id": "API5:2023", "category": "Broken Function Level Authorization"},
                    "sans": {"cwe_id": "CWE-285", "category": "Porous Defenses", "rank": 4},
                    "remediation": "Implementar RBAC consistente e validar permissões."
                },
                "injection": {
                    "name": "Injection",
                    "severity": "critical",
                    "owasp": {"id": "A03:2021", "category": "Injection"},
                    "sans": {"cwe_id": "CWE-89", "category": "Insecure Interaction", "rank": 1},
                    "remediation": "Usar prepared statements e validar todos os inputs."
                },
                "ssrf": {
                    "name": "Server-Side Request Forgery",
                    "severity": "high",
                    "owasp": {"id": "API7:2023", "category": "Server-Side Request Forgery"},
                    "sans": {"cwe_id": "CWE-918", "category": "Insecure Interaction Between Components", "rank": 8},
                    "remediation": "Validar URLs contra allowlist."
                },
                "broken_auth": {
                    "name": "Broken Authentication",
                    "severity": "high",
                    "owasp": {"id": "API2:2023", "category": "Broken Authentication"},
                    "sans": {"cwe_id": "CWE-287", "category": "Risky Resource Management", "rank": 2},
                    "remediation": "Implementar autenticação forte (JWT, OAuth2)."
                },
                "mass_assignment": {
                    "name": "Mass Assignment",
                    "severity": "medium",
                    "owasp": {"id": "API3:2023", "category": "Broken Object Property Level Authorization"},
                    "sans": {"cwe_id": "CWE-915", "category": "Porous Defenses", "rank": 5},
                    "remediation": "Usar DTOs e validar campos atualizáveis."
                },
                "security_misconfiguration": {
                    "name": "Security Misconfiguration",
                    "severity": "medium",
                    "owasp": {"id": "API8:2023", "category": "Security Misconfiguration"},
                    "sans": {"cwe_id": "CWE-16", "category": "Porous Defenses", "rank": 6},
                    "remediation": "Remover endpoints de debug/test em produção."
                },
                "rate_limiting_absence": {
                    "name": "Unrestricted Resource Consumption",
                    "severity": "medium",
                    "owasp": {"id": "API4:2023", "category": "Unrestricted Resource Consumption"},
                    "sans": {"cwe_id": "CWE-770", "category": "Risky Resource Management", "rank": 7},
                    "remediation": "Implementar rate limiting baseado em IP/usuário."
                },
                "xxe": {
                    "name": "XML External Entities (XXE)",
                    "severity": "high",
                    "owasp": {"id": "API8:2023", "category": "Security Misconfiguration"},
                    "sans": {"cwe_id": "CWE-611", "category": "Insecure Interaction Between Components", "rank": 9},
                    "remediation": "Desabilitar entidades externas em parsers XML."
                },
                "open_redirect": {
                    "name": "Open Redirect",
                    "severity": "medium",
                    "owasp": {"id": "API1:2023", "category": "Broken Object Level Authorization"},
                    "sans": {"cwe_id": "CWE-601", "category": "Insecure Interaction Between Components", "rank": 10},
                    "remediation": "Validar URLs contra allowlist."
                },
                "unsafe_consumption": {
                    "name": "Unsafe Consumption of APIs",
                    "severity": "high",
                    "owasp": {"id": "API10:2023", "category": "Unsafe Consumption of APIs"},
                    "sans": {"cwe_id": "CWE-346", "category": "Insecure Interaction Between Components", "rank": 16},
                    "remediation": "Validar dados recebidos de APIs de terceiros."
                }
            }
        }
    
    def get_vulnerability_info(self, vuln_name: str) -> Optional[Dict]:
        return self.mappings.get("vulnerabilities", {}).get(vuln_name)
    
    def get_owasp_summary(self, vulnerabilities: List[str]) -> List[Dict]:
        owasp_map = {}
        for vuln_name in vulnerabilities:
            vuln_info = self.get_vulnerability_info(vuln_name)
            if vuln_info and 'owasp' in vuln_info:
                owasp_id = vuln_info['owasp']['id']
                if owasp_id not in owasp_map:
                    owasp_map[owasp_id] = {
                        "id": owasp_id,
                        "category": vuln_info['owasp']['category'],
                        "vulnerabilities": [],
                        "severity": vuln_info.get('severity', 'medium')
                    }
                owasp_map[owasp_id]['vulnerabilities'].append(vuln_name)
        return list(owasp_map.values())
    
    def get_sans_summary(self, vulnerabilities: List[str]) -> List[Dict]:
        sans_map = {}
        for vuln_name in vulnerabilities:
            vuln_info = self.get_vulnerability_info(vuln_name)
            if vuln_info and 'sans' in vuln_info:
                cwe_id = vuln_info['sans']['cwe_id']
                if cwe_id not in sans_map:
                    sans_map[cwe_id] = {
                        "cwe_id": cwe_id,
                        "category": vuln_info['sans']['category'],
                        "rank": vuln_info['sans']['rank'],
                        "vulnerabilities": [],
                        "severity": vuln_info.get('severity', 'medium')
                    }
                sans_map[cwe_id]['vulnerabilities'].append(vuln_name)
        return sorted(sans_map.values(), key=lambda x: x['rank'])
    
    def enrich_vulnerabilities(self, vulnerabilities: List[str]) -> List[Dict]:
        enriched = []
        for vuln_name in vulnerabilities:
            vuln_info = self.get_vulnerability_info(vuln_name)
            if vuln_info:
                enriched.append({
                    "name": vuln_name,
                    "display_name": vuln_info.get('name', vuln_name),
                    "severity": vuln_info.get('severity', 'medium'),
                    "owasp": vuln_info.get('owasp'),
                    "sans": vuln_info.get('sans'),
                    "remediation": vuln_info.get('remediation', 'Revisar implementação de segurança.'),
                    "references": vuln_info.get('references', [])
                })
            else:
                enriched.append({"name": vuln_name, "display_name": vuln_name, "severity": "unknown"})
        return enriched


class AdvancedVulnerabilityDetector:
    """Detector heurístico de vulnerabilidades"""
    
    def __init__(self):
        self.vuln_db = VulnerabilityDatabase()
    
    def detect_vulnerabilities(self, endpoint: Dict, auth_required: bool = True) -> List[str]:
        path = endpoint.get('path', '').lower()
        method = endpoint.get('method', '').upper()
        vulnerabilities = []
        
        # Verifica UUID
        is_id_uuid = False
        params = endpoint.get('parameters', [])
        for param in params:
            if param.get('in') == 'path' and param.get('name', '').lower() == 'id':
                schema = param.get('schema', {})
                fmt = schema.get('format', '').lower()
                if fmt == 'uuid':
                    is_id_uuid = True
        
        # Regras de detecção
        if re.search(r':id\b|:user_id\b|:account_id\b|:document_id\b', path):
            vulnerabilities.append("bola")
        
        if re.search(r'/admin/|/internal/|/users/role|/permission|/privilege', path):
            vulnerabilities.append("bfla")
        
        if re.search(r':query\b|:filter\b|:search\b|:sort\b', path) and not is_id_uuid:
            vulnerabilities.append("injection")
        
        if re.search(r'url|uri|endpoint|fetch|load|proxy|webhook', path):
            vulnerabilities.append("ssrf")
        
        if not auth_required and method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            vulnerabilities.append("broken_auth")
        
        if re.search(r'/update|/patch|/edit|/modify', path) and method in ['PUT', 'PATCH', 'POST']:
            vulnerabilities.append("mass_assignment")
        
        if re.search(r'/debug|/test|/dev|/internal|/private', path):
            vulnerabilities.append("security_misconfiguration")
        
        if re.search(r'/login|/auth|/register|/reset-password|/otp', path) and method == 'POST':
            vulnerabilities.append("rate_limiting_absence")
        
        if re.search(r'/xml|/soap|/xsd|/wsdl|\.xml$', path) and method in ['POST', 'PUT']:
            vulnerabilities.append("xxe")
        
        if re.search(r'redirect|callback|return_to|next|goto|returnurl', path):
            vulnerabilities.append("open_redirect")
        
        if re.search(r'/webhook|/callback|/integrations|/third-party', path):
            vulnerabilities.append("unsafe_consumption")
        
        return list(dict.fromkeys(vulnerabilities))


class OpenAPIEnricher:
    """Enriquece endpoints com dados do OpenAPI/Swagger"""
    
    def __init__(self, openapi_file: Optional[Path] = None):
        self.openapi_file = openapi_file
        self.openapi_data = self._load_openapi() if openapi_file else None
        self.examples_dir = Path("output/tests/dados")
        self.krakend_roles = self._load_krakend_roles()
    
    def _load_openapi(self) -> Optional[Dict]:
        if not self.openapi_file or not self.openapi_file.exists():
            return None
        
        with open(self.openapi_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if self.openapi_file.suffix in ['.yaml', '.yml']:
            if YAML_AVAILABLE:
                return yaml.safe_load(content)
            else:
                print("⚠️  PyYAML não instalado. Ignorando arquivo YAML.")
                return None
        else:
            return json.loads(content)
    
    def _load_krakend_roles(self) -> Dict:
        """Carrega roles do arquivo de configuração do KrakenD"""
        krakend_roles = {}
        
        # Busca KRAKEND_CONF do .env
        env_path = Path(".env")
        krakend_conf = None
        endpoint_prefix = None
        
        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip().startswith("KRAKEND_CONF"):
                        krakend_conf = line.strip().split("=", 1)[-1]
                    if line.strip().startswith("ENDPOINT_PREFIX"):
                        endpoint_prefix = line.strip().split("=", 1)[-1]
        
        if krakend_conf and Path(krakend_conf).exists():
            try:
                with open(krakend_conf, 'r', encoding='utf-8') as f:
                    krakend_data = json.load(f)
                
                for ep in krakend_data.get("endpoints", []):
                    ep_path = ep.get("endpoint", "")
                    if endpoint_prefix:
                        ep_path = ep_path.replace("$ENDPOINT_PREFIX", endpoint_prefix)
                    ep_method = ep.get("method", "").upper()
                    
                    extra = ep.get("extra_config", {})
                    jose = extra.get("github.com/devopsfaith/krakend-jose/validator")
                    if jose and "roles" in jose:
                        krakend_roles[(ep_path, ep_method)] = jose["roles"]
            except Exception as e:
                print(f"⚠️  Erro ao ler roles do Krakend: {e}")
        
        return krakend_roles
    
    def _make_example_filename(self, method: str, path: str) -> str:
        """Gera nome de arquivo para exemplo baseado no método e path"""
        sanitized = path.lstrip("/")
        sanitized = re.sub(r"\{[^}/]+\}", "X", sanitized)
        sanitized = re.sub(r"[/\\\s]+", "_", sanitized)
        sanitized = re.sub(r"[^a-zA-Z0-9_\-]", "", sanitized)
        return f"{method.upper()}_{sanitized}.json"
    
    def _normalize_path(self, path: str) -> str:
        """Normaliza path para comparação (substitui variáveis por {X})"""
        return re.sub(r"\{[^}/]+\}", "{X}", path)
    
    def enrich_endpoint(self, endpoint: Dict) -> Dict:
        """Adiciona informações do OpenAPI a um endpoint"""
        path = endpoint.get('path', '')
        method = endpoint.get('method', '')
        
        # Busca no OpenAPI
        if self.openapi_data:
            paths = self.openapi_data.get('paths', {})
            method_lower = method.lower()
            
            if path in paths and method_lower in paths[path]:
                details = paths[path][method_lower]
                endpoint['summary'] = details.get('summary')
                endpoint['description'] = details.get('description')
        
        # Busca exemplo real
        example_filename = self._make_example_filename(method, path)
        example_path = self.examples_dir / example_filename
        if example_path.exists():
            try:
                with open(example_path, 'r', encoding='utf-8') as f:
                    endpoint['realistic_examples'] = {
                        "valid_request": json.load(f),
                        "valid_response": None
                    }
            except Exception:
                pass
        
        # Busca roles do Krakend
        roles = []
        norm_path = self._normalize_path(path)
        
        # Tenta match exato
        if (path, method) in self.krakend_roles:
            roles = self.krakend_roles[(path, method)]
        else:
            # Tenta match por path normalizado
            for (k_path, k_method), k_roles in self.krakend_roles.items():
                if k_method == method and self._normalize_path(k_path) == norm_path:
                    roles = k_roles
                    break
        
        endpoint['roles'] = roles
        
        return endpoint


class LocalLLMAnalyzer:
    """Analisador de segurança com LLM + Heurística"""
    
    def __init__(self, model: str = "codellama:7b", backend: str = "gatiator", llm_url: str = None):
        self.model = model
        self.backend = backend
        self.vuln_db = VulnerabilityDatabase()
        self.adv_detector = AdvancedVulnerabilityDetector()
        
        if llm_url:
            self.llm_url = llm_url
        elif backend == "gatiator":
            self.llm_url = os.getenv("LLM_BASE_URL", "http://localhost:1313/v1/chat/completions")
        elif backend == "ollama":
            self.llm_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1/chat/completions")
        else:
            raise ValueError(f"Backend LLM desconhecido: {backend}")
    
    def _get_pii_patterns(self):
        try:
            patterns_path = Path(__file__).parent.parent.parent / "pii_patterns.json"
            if patterns_path.exists():
                with open(patterns_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return ['cpf', 'cnpj', 'email', 'telefone', 'celular', 'nome', 'documento']
    
    def _infer_tags(self, endpoint: Dict) -> List[str]:
        path = endpoint.get('path', '').lower()
        method = endpoint.get('method', '').upper()
        tags = []
        if 'user' in path or 'usuario' in path or 'conta' in path:
            tags.append("user-management")
        if 'auth' in path or 'login' in path:
            tags.append("authentication")
        if 'documento' in path:
            tags.append("document-management")
        if 'fluxo' in path:
            tags.append("workflow")
        if method in ['POST', 'PUT', 'PATCH']:
            tags.append("write-operation")
        if method == 'GET':
            tags.append("read-operation")
        if method == 'DELETE':
            tags.append("delete-operation")
        return tags
    
    def _infer_purpose(self, endpoint: Dict) -> str:
        path = endpoint.get('path', '').lower()
        method = endpoint.get('method', '').upper()
        
        if 'user' in path or 'conta' in path:
            if method == 'GET':
                return "Consulta de usuários/contas"
            elif method == 'POST':
                return "Criação de usuários/contas"
            elif method == 'PUT':
                return "Atualização de usuários/contas"
            elif method == 'DELETE':
                return "Remoção de usuários/contas"
        
        if 'auth' in path or 'login' in path:
            return "Autenticação de usuários"
        
        if 'documento' in path:
            return "Gerenciamento de documentos"
        
        if 'fluxo' in path:
            return "Gerenciamento de fluxos de trabalho"
        
        return f"Operação {method} no recurso {path}"
    
    def _simple_heuristic_analysis(self, endpoint: Dict) -> Dict:
        """Análise heurística completa"""
        path = endpoint.get('path', '').lower()
        method = endpoint.get('method', '').upper()
        
        # Detecta PII
        pii_fields = []
        for pattern in self._get_pii_patterns():
            if pattern in path:
                pii_fields.append(pattern)
        
        # Detecta autenticação
        auth_required = True
        auth_type = "jwt"
        if 'public' in path or 'health' in path or 'metrics' in path or 'swagger' in path:
            auth_required = False
            auth_type = "none"
        elif 'login' in path or 'auth' in path:
            auth_type = "basic"
        
        # Detecta vulnerabilidades
        vulnerabilities = self.adv_detector.detect_vulnerabilities(endpoint, auth_required)
        
        # Calcula risco
        risk_level = "baixo"
        risk_reason = "Endpoint sem dados sensíveis aparentes"
        risk_score = 0.1
        
        if vulnerabilities:
            for vuln in vulnerabilities:
                vuln_info = self.vuln_db.get_vulnerability_info(vuln)
                if vuln_info:
                    severity = vuln_info.get('severity', 'medium')
                    if severity == 'critical':
                        risk_level = "alto"
                        risk_score = 0.95
                        risk_reason = f"Vulnerabilidade crítica: {vuln}"
                        break
                    elif severity == 'high' and risk_level != "alto":
                        risk_level = "alto"
                        risk_score = 0.85
                        risk_reason = f"Vulnerabilidade alta: {vuln}"
                    elif severity == 'medium' and risk_level == "baixo":
                        risk_level = "médio"
                        risk_score = 0.60
                        risk_reason = f"Vulnerabilidade média: {vuln}"
        elif pii_fields:
            risk_level = "alto"
            risk_score = 0.9
            risk_reason = f"Contém PII: {', '.join(pii_fields)}"
        elif method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            risk_level = "médio"
            risk_score = 0.5
            risk_reason = "Método que modifica dados"
        elif ':id' in path or ':perfil' in path:
            risk_level = "médio"
            risk_score = 0.5
            risk_reason = "Contém parâmetro de ID (possível BOLA)"
        
        return {
            "pii_fields": pii_fields,
            "auth_required": auth_required,
            "auth_type": auth_type,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "risk_reason": risk_reason,
            "vulnerabilities": vulnerabilities,
            "vulnerabilities_detailed": self.vuln_db.enrich_vulnerabilities(vulnerabilities),
            "owasp_summary": self.vuln_db.get_owasp_summary(vulnerabilities),
            "sans_summary": self.vuln_db.get_sans_summary(vulnerabilities),
            "business_purpose": self._infer_purpose(endpoint),
            "critical_resource": risk_level == "alto",
            "tags": self._infer_tags(endpoint)
        }
    
    def analyze_endpoint(self, endpoint: Dict, code_context: str = "", max_retries: int = 2) -> Dict:
        """Analisa endpoint com fallback para heurística"""
        for attempt in range(max_retries):
            try:
                result = self._call_llm(endpoint, code_context)
                if result and 'error' not in result:
                    # Normaliza vulnerabilidades
                    llm_vulns = result.get('vulnerabilities', [])
                    if isinstance(llm_vulns, list):
                        clean_vulns = []
                        valid_vulns = ['bola', 'bfla', 'injection', 'ssrf', 'broken_auth', 
                                      'mass_assignment', 'security_misconfiguration', 
                                      'rate_limiting_absence', 'xxe', 'open_redirect', 'unsafe_consumption']
                        for v in llm_vulns:
                            if isinstance(v, str):
                                vuln_clean = v.lower().strip().replace(' ', '_')
                                if vuln_clean in valid_vulns:
                                    clean_vulns.append(vuln_clean)
                        result['vulnerabilities'] = clean_vulns
                    else:
                        result['vulnerabilities'] = []
                    
                    # Enriquece com OWASP/SANS
                    result['vulnerabilities_detailed'] = self.vuln_db.enrich_vulnerabilities(result['vulnerabilities'])
                    result['owasp_summary'] = self.vuln_db.get_owasp_summary(result['vulnerabilities'])
                    result['sans_summary'] = self.vuln_db.get_sans_summary(result['vulnerabilities'])
                    
                    if 'risk_score' not in result:
                        result['risk_score'] = 0.9 if result.get('risk_level') == 'alto' else (0.5 if result.get('risk_level') == 'médio' else 0.1)
                    if 'tags' not in result:
                        result['tags'] = self._infer_tags(endpoint)
                    if 'business_purpose' not in result:
                        result['business_purpose'] = self._infer_purpose(endpoint)
                    
                    return result
            except Exception as e:
                print(f"   ⚠️  Tentativa {attempt + 1} falhou: {e}")
                time.sleep(1)
        
        print("   🔄 Usando análise heurística (fallback)")
        return self._simple_heuristic_analysis(endpoint)
    
    def _call_llm(self, endpoint: Dict, code_context: str = "") -> Dict:
        """Chama o backend LLM"""
        prompt = f"""Responda apenas com JSON. Endpoint: {endpoint.get('method', '')} {endpoint.get('path', '')}

Formato exato:
{{"pii_fields":[],"auth_required":false,"auth_type":"jwt","risk_level":"baixo","risk_reason":"","vulnerabilities":[],"business_purpose":"","critical_resource":false}}

Use vulnerabilities: bola, bfla, injection, ssrf, broken_auth, mass_assignment, security_misconfiguration, rate_limiting_absence, xxe, open_redirect, unsafe_consumption

Apenas o JSON."""
        
        payload = {"model": self.model, "messages": [{"role": "user", "content": prompt}]}
        headers = {"Content-Type": "application/json"}
        if self.backend == "gatiator":
            headers["Authorization"] = "Bearer qualquer"
        
        try:
            response = requests.post(self.llm_url, json=payload, headers=headers, timeout=30)
            if response.status_code != 200:
                return {"error": f"Status {response.status_code}"}
            
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(content[start:end])
            return {"error": "JSON não encontrado"}
        except Exception as e:
            return {"error": str(e)}


def generate_enhanced_report(endpoints: List[Dict], output_file: Path):
    """Gera relatório Markdown com OWASP e SANS"""
    total = len(endpoints)
    if total == 0:
        print("⚠️ Nenhum endpoint para gerar relatório")
        return
    
    high_risk = sum(1 for e in endpoints if e.get('risk_level') == 'alto')
    medium_risk = sum(1 for e in endpoints if e.get('risk_level') == 'médio')
    low_risk = sum(1 for e in endpoints if e.get('risk_level') == 'baixo')
    has_pii = sum(1 for e in endpoints if e.get('pii_fields'))
    
    # Coleta vulnerabilidades
    owasp_map = {}
    sans_map = {}
    for e in endpoints:
        for vuln in e.get('vulnerabilities_detailed', []):
            if vuln.get('owasp'):
                owasp_id = vuln['owasp']['id']
                if owasp_id not in owasp_map:
                    owasp_map[owasp_id] = {'count': 0, 'name': vuln['owasp']['category']}
                owasp_map[owasp_id]['count'] += 1
            if vuln.get('sans'):
                cwe_id = vuln['sans']['cwe_id']
                if cwe_id not in sans_map:
                    sans_map[cwe_id] = {'count': 0, 'rank': vuln['sans']['rank']}
                sans_map[cwe_id]['count'] += 1
    
    report = f"""# Relatório de Análise de Segurança de API

## 📊 Resumo

| Métrica | Valor |
|---------|-------|
| **Total de endpoints** | {total} |
| **Alto risco** | {high_risk} ({high_risk/total*100:.1f}%) |
| **Médio risco** | {medium_risk} ({medium_risk/total*100:.1f}%) |
| **Baixo risco** | {low_risk} ({low_risk/total*100:.1f}%) |
| **Com dados PII** | {has_pii} ({has_pii/total*100:.1f}%) |

## 🛡️ OWASP API Top 10 2023

| ID | Categoria | Endpoints afetados |
|----|-----------|-------------------|
"""
    for owasp_id, info in sorted(owasp_map.items()):
        report += f"| {owasp_id} | {info['name']} | {info['count']} |\n"
    
    if not owasp_map:
        report += "| Nenhuma vulnerabilidade OWASP detectada | - | 0 |\n"
    
    report += "\n## 📊 SANS Top 25\n\n| Rank | CWE | Endpoints afetados |\n|------|-----|-------------------|\n"
    for cwe_id, info in sorted(sans_map.items(), key=lambda x: x[1]['rank']):
        report += f"| {info['rank']} | {cwe_id} | {info['count']} |\n"
    
    if not sans_map:
        report += "| Nenhuma vulnerabilidade SANS detectada | - | 0 |\n"
    
    report += "\n## 🔴 Endpoints de Alto Risco\n\n| Método | Path | Vulnerabilidades |\n|--------|------|------------------|\n"
    high_risk_count = 0
    for e in endpoints:
        if e.get('risk_level') == 'alto':
            vulns = ', '.join(e.get('vulnerabilities', [])) if e.get('vulnerabilities') else '-'
            report += f"| {e.get('method', '')} | `{e.get('path', '')}` | {vulns} |\n"
            high_risk_count += 1
            if high_risk_count >= 20:
                report += f"| ... | *mais {high_risk - 20} endpoints* | ... |\n"
                break
    
    if high_risk == 0:
        report += "| Nenhum endpoint de alto risco detectado | - | - |\n"
    
    report += f"\n---\n*Relatório gerado por step5_analyzer_unified.py em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}*\n"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"📊 Relatório salvo em: {output_file}")


def find_latest_scan_endpoints(base_dir: str = "output") -> Optional[str]:
    """Procura o all_endpoints.json do scan mais recente"""
    import glob
    if not os.path.isdir(base_dir):
        return None
    scan_dirs = glob.glob(os.path.join(base_dir, "scan_*"))
    if not scan_dirs:
        return None
    scan_dirs.sort(key=lambda x: os.path.basename(x), reverse=True)
    for scan_dir in scan_dirs:
        endpoints_file = os.path.join(scan_dir, "all_endpoints.json")
        if os.path.isfile(endpoints_file):
            return endpoints_file
    return None


def analyze_project_endpoints(endpoints_file: Union[str, Path] = None,
                             endpoints: List[Dict] = None,
                             openapi_file: Union[str, Path] = None,
                             model: str = "codellama:7b",
                             use_llm: bool = True,
                             backend: str = "gatiator",
                             llm_url: str = None) -> Dict[str, Any]:
    """Função principal unificada"""
    # Carrega endpoints do scan
    if endpoints_file:
        with open(endpoints_file, 'r', encoding='utf-8') as f:
            endpoints = json.load(f)
    elif not endpoints:
        raise ValueError("Forneça endpoints_file ou endpoints")
    
    print(f"\n📁 Carregados {len(endpoints)} endpoints do scan")
    print(f"🤖 Modo: {'Híbrido (LLM + Heurística)' if use_llm else 'Heurística pura'}")
    
    if openapi_file:
        print(f"📄 Enriquecendo com OpenAPI: {openapi_file}")
    
    # Inicializa componentes
    analyzer = LocalLLMAnalyzer(model=model, backend=backend, llm_url=llm_url)
    enricher = OpenAPIEnricher(Path(openapi_file) if openapi_file else None)
    
    # Analisa e enriquece cada endpoint
    start_time = time.time()
    enriched = []
    total = len(endpoints)
    
    for i, endpoint in enumerate(endpoints, 1):
        print(f"\n📊 {i}/{total}: {endpoint.get('method', '')} {endpoint.get('path', '')}")
        
        # Análise de segurança
        if use_llm:
            security_analysis = analyzer.analyze_endpoint(endpoint)
        else:
            security_analysis = analyzer._simple_heuristic_analysis(endpoint)
        
        # Enriquece com dados do OpenAPI
        enriched_endpoint = {**endpoint, **security_analysis}
        if openapi_file:
            enriched_endpoint = enricher.enrich_endpoint(enriched_endpoint)
        
        enriched.append(enriched_endpoint)
        
        vuln_count = len(security_analysis.get('vulnerabilities', []))
        owasp_count = len(security_analysis.get('owasp_summary', []))
        print(f"   ✅ Vulns: {vuln_count} | Risco: {security_analysis.get('risk_level', '?')} | OWASP: {owasp_count}")
    
    elapsed = time.time() - start_time
    
    # Salva resultados
    tests_dir = Path("src/application/pipeline/tests")
    output_dir = Path("output")
    tests_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    json_output = tests_dir / "enriched_endpoints.json"
    with open(json_output, 'w', encoding='utf-8') as f:
        json.dump(enriched, f, indent=2, ensure_ascii=False)
    
    report_file = output_dir / "final_security_report.md"
    generate_enhanced_report(enriched, report_file)
    
    stats = {
        "total": len(enriched),
        "high_risk": sum(1 for e in enriched if e.get('risk_level') == 'alto'),
        "medium_risk": sum(1 for e in enriched if e.get('risk_level') == 'médio'),
        "low_risk": sum(1 for e in enriched if e.get('risk_level') == 'baixo'),
        "use_llm": use_llm,
        "has_openapi": bool(openapi_file),
        "analysis_time_seconds": elapsed
    }
    
    print(f"\n⏱️ Tempo de análise: {elapsed:.2f} segundos")
    print(f"💾 JSON salvo em: {json_output}")
    print(f"📊 Relatório salvo em: {report_file}")
    
    return {"summary": stats, "endpoints": enriched, "high_risk_endpoints": [e for e in enriched if e.get('risk_level') == 'alto']}


def main():
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Analisador UNIFICADO de segurança e enriquecimento de API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXEMPLOS:
  # Apenas análise de segurança (mais rápido)
  python3 step5_analyzer_unified.py output/scan_*/all_endpoints.json --no-llm
  
  # Com enriquecimento OpenAPI
  python3 step5_analyzer_unified.py output/scan_*/all_endpoints.json --openapi docs/openapi.yaml --no-llm
  
  # Modo completo (LLM + OpenAPI)
  python3 step5_analyzer_unified.py output/scan_*/all_endpoints.json --openapi docs/openapi.yaml --llm-backend ollama
"""
    )
    
    parser.add_argument("endpoints_file", nargs="?", help="Caminho para all_endpoints.json (opcional: busca automático)")
    parser.add_argument("--openapi", "-o", help="Arquivo OpenAPI/Swagger (JSON ou YAML) para enriquecimento")
    parser.add_argument("--llm-backend", choices=["gatiator", "ollama", "none"], default="none", help="Backend LLM")
    parser.add_argument("--llm-model", default="codellama:7b", help="Modelo LLM")
    parser.add_argument("--no-llm", action="store_true", help="Usa apenas heurística (recomendado para CI/CD)")
    
    args = parser.parse_args()
    
    # Encontra arquivo de endpoints
    if args.endpoints_file:
        endpoints_path = args.endpoints_file
    else:
        endpoints_path = find_latest_scan_endpoints()
        if not endpoints_path:
            print("❌ Nenhum arquivo all_endpoints.json encontrado em output/scan_*/")
            print("💡 Execute primeiro: python3 step4_scanner.py /caminho/do/projeto")
            sys.exit(1)
        print(f"🔍 Usando scan mais recente: {endpoints_path}")
    
    use_llm = not args.no_llm and args.llm_backend != "none"
    
    results = analyze_project_endpoints(
        endpoints_file=endpoints_path,
        openapi_file=args.openapi,
        model=args.llm_model,
        use_llm=use_llm,
        backend=args.llm_backend if use_llm else "none"
    )
    
    # Resumo final
    print("\n" + "="*60)
    print("📈 RESUMO FINAL DA ANÁLISE")
    print("="*60)
    print(f"Total de endpoints analisados    : {results['summary']['total']}")
    print(f"Endpoints de ALTO risco          : {results['summary']['high_risk']}")
    print(f"Endpoints de MÉDIO risco         : {results['summary']['medium_risk']}")
    print(f"Endpoints de BAIXO risco         : {results['summary']['low_risk']}")
    
    if results['summary']['high_risk'] > 0:
        print("\n⚠️  ATENÇÃO! Revise os endpoints de alto risco no relatório.")
    
    print("="*60)


if __name__ == "__main__":
    main()