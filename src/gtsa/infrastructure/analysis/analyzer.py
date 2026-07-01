#!/usr/bin/env python3
"""
step4_analyzer_and_enricher.py
---------------------------
Script UNIFICADO para análise de segurança e enriquecimento de endpoints.
FUNCIONALIDADES:
1. Analisa riscos e detecta vulnerabilidades (OWASP API Top 10 2023 + SANS Top 25)
2. Enriquece com dados do OpenAPI/Swagger (summary, description)
3. Adiciona exemplos reais de requisição (de output/tests/dados/)
4. Adiciona roles de autorização (do arquivo de configuração do KrakenD)
5. Detecta headers customizados de autenticação (OpenAPI + .env)
6. Modo Híbrido: LLM (Ollama/Gatiator) + Heurística com fallback automático
SAÍDAS:
- src/application/pipeline/tests/enriched_endpoints.json (completo)
- <output_dir>/final_security_report.md (relatório OWASP/SANS)
- <output_dir>/test_api_summary.md (resumo de mapeamento)
"""
import os
import sys
import json
import requests
import time
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import argparse
from ..config.settings import load_environment, add_env_arg, get_env_file_from_args

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    print("⚠️  PyYAML não instalado. Para arquivos OpenAPI YAML, instale: pip install pyyaml")


class VulnerabilityDatabase:
    """Gerencia o banco de vulnerabilidades OWASP API Top 10 2023 + SANS Top 25"""

    def __init__(self, config_path: Optional[Path] = None):
        default_path = Path(__file__).resolve().parents[4] / "config" / "vulnerability_mapping.json"
        self.config_path = config_path or default_path
        self.mappings = self._load_mappings()

    def _load_mappings(self) -> Dict:
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

    def _get_owasp_entry(self, vuln_info: Dict) -> Optional[Dict]:
        if not vuln_info:
            return None
        return vuln_info.get('owasp') or vuln_info.get('owasp_2023')

    def get_owasp_summary(self, vulnerabilities: List[str]) -> List[Dict]:
        owasp_map = {}
        for vuln_name in vulnerabilities:
            vuln_info = self.get_vulnerability_info(vuln_name)
            owasp = self._get_owasp_entry(vuln_info) if vuln_info else None
            if owasp:
                owasp_id = owasp['id']
                if owasp_id not in owasp_map:
                    owasp_map[owasp_id] = {
                        "id": owasp_id,
                        "category": owasp.get('category') or owasp.get('name', 'Unknown'),
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
                owasp = self._get_owasp_entry(vuln_info)
                enriched.append({
                    "name": vuln_name,
                    "display_name": vuln_info.get('name', vuln_name),
                    "severity": vuln_info.get('severity', 'medium'),
                    "owasp": owasp,
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
        context_raw = str(endpoint.get('context', ''))
        context = context_raw.lower()
        vulnerabilities = []
        is_id_uuid = False

        params = endpoint.get('parameters', [])
        for param in params:
            if param.get('in') == 'path' and param.get('name', '').lower() == 'id':
                schema = param.get('schema', {})
                fmt = schema.get('format', '').lower()
                if fmt == 'uuid':
                    is_id_uuid = True

        def _has_direct_id_access(p: str) -> bool:
            segments = p.strip('/').split('/')
            for i, seg in enumerate(segments):
                if re.match(r'^:(id|user_id|account_id|document_id)\b', seg):
                    if i == len(segments) - 1:
                        return True
                    next_seg = segments[i + 1]
                    if next_seg.startswith(':'):
                        return True
            return False

        def _handler_has_ownership_check(ctx: str) -> bool:
            handler_marker = '// --- handler:'
            if handler_marker not in ctx:
                return False
            handler_code = ctx[ctx.index(handler_marker):]
            return bool(re.search(
                r'\b(?:userId|user_id|ownerId|owner_id|'
                r'idCliente|idConta|idUsuario|codUsuario|'
                r'tenantId|tenant_id|accountId|account_id|'
                r'requesterId|requester_id|createdBy|created_by|'
                r'this\.id[A-Z]|this\.user)\b',
                handler_code,
            ))

        if _has_direct_id_access(path) and not _handler_has_ownership_check(context_raw):
            vulnerabilities.append("bola")

        if re.search(r'/admin/|/internal/|/users/role|/permission|/privilege', path):
            vulnerabilities.append("bfla")

        repo_marker = "// --- repository:"

        def _has_local_injection_evidence(ctx: str) -> bool:
            dynamic_sql_patterns = [
                r'order\s+by\s+[`\"\']?\$\{',
                r'order\s+by\s+["\']?\s*\+',
                r'where\s+.*[`\"\']?\$\{',
                r'where\s+.*["\']\s*\+',
                r'select\s+.*[`\"\']?\$\{',
                r'select\s+.*["\']\s*\+',
                r'sequelize\.literal\s*\(',
                r'\bliteral\s*\(',
            ]
            return any(re.search(pattern, ctx, re.IGNORECASE | re.DOTALL) for pattern in dynamic_sql_patterns)

        def _injection_mitigated(ep: Dict, ctx: str) -> bool:
            ALLOWLIST_RE = re.compile(
                r"\b(?:allowedSortFields|allowedFields|allowedColumns|validSortFields|"
                r"validFields|sortWhitelist|SORT_WHITELIST|allowedOrderBy|allowedSortColumns)\b"
                r"|\.includes\s*\(\s*\w*[Ss]ort|"
                r"\.includes\s*\(\s*\w*[Ff]ield"
            )
            DIRECTION_RE = re.compile(
                r"\b(?:sanitizeSortDirection|sanitizeDirection|validateSortDirection|"
                r"sanitizeOrder|validateOrder)\s*\("
                r"|(?:sortDirection|direction)\s*===?\s*[\"'](?:ASC|DESC)[\"']"
                r"|[\"](?:ASC|DESC)[\"]\s*:\s*[\"'](?:ASC|DESC)[\"']"
            )
            if repo_marker not in ctx:
                return False
            parts = ctx.split(repo_marker)
            repo_sections = parts[1:]
            if not repo_sections:
                return False
            SORT_USAGE_RE = re.compile(
                r"\bsort(?:Field|Direction|By)\b|"
                r"\bsortfield\b|\bsortdirection\b|"
                r"\border_by\b|\borderby\b",
                re.IGNORECASE,
            )
            for section in repo_sections:
                uncommented = re.sub(r"//[^\n]*", "", section)
                if SORT_USAGE_RE.search(uncommented):
                    if not (ALLOWLIST_RE.search(uncommented) and DIRECTION_RE.search(uncommented)):
                        return False
            return True

        mitigated = _injection_mitigated(endpoint, context_raw)
        has_repo_context = repo_marker in context_raw
        has_local_injection_evidence = _has_local_injection_evidence(context_raw)
        can_confirm_injection = has_repo_context or has_local_injection_evidence

        if re.search(r':query\b|:filter\b|:search\b|:sort\b', path) and not is_id_uuid:
            if can_confirm_injection and not mitigated:
                vulnerabilities.append("injection")

        if method == 'GET':
            has_query_block = ('in: query' in context) or ('req.query' in context)
            has_sort_filter_query = re.search(
                r'name:\s*(sort(direction|field)?|order(by)?|filter|search|q)\b|req\.query\.(sort|order|filter|search|q)',
                context,
            )
            if has_query_block and has_sort_filter_query and not is_id_uuid:
                if can_confirm_injection and not mitigated:
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
    def __init__(self, openapi_file=None, output_dir=None, env_file=None, data_dir=None):
        self.openapi_file = openapi_file
        if openapi_file:
            try:
                with open(openapi_file, 'r', encoding='utf-8') as f:
                    if str(openapi_file).endswith(('.yaml', '.yml')):
                        if YAML_AVAILABLE:
                            self.openapi_data = yaml.safe_load(f)
                        else:
                            print("⚠️  PyYAML não disponível para carregar YAML")
                            self.openapi_data = None
                    else:
                        self.openapi_data = json.load(f)
            except Exception as e:
                print(f"⚠️  Erro ao carregar OpenAPI: {e}")
                self.openapi_data = None
        else:
            self.openapi_data = None

        self.output_dir = output_dir or Path("output")
        self.examples_dir = Path(data_dir) if data_dir else self.output_dir / "tests/dados"
        self.env_file = env_file
        self.krakend_roles = self._load_krakend_roles()
        self.krakend_disable_jwk = self._load_krakend_disable_jwk()
        self.custom_auth_headers_env = self._load_custom_auth_headers_from_env()

    def _load_custom_auth_headers_from_env(self) -> Dict[str, Dict[str, str]]:
        """
        Carrega CUSTOM_AUTH_HEADERS do .env.
        Formato: "PUT /api/v1/login-sistema:x-chave-acesso-sistema=CHAVE_ACESSO_SISTEMA;..."
        Resultado: {"PUT /api/v1/login-sistema": {"x-chave-acesso-sistema": "CHAVE_ACESSO_SISTEMA"}}
        """
        result = {}
        raw = os.getenv("CUSTOM_AUTH_HEADERS", "").strip()
        if not raw:
            return result
        for item in raw.split(';'):
            item = item.strip()
            if not item or ':' not in item:
                continue
            endpoint_key, headers_str = item.split(':', 1)
            endpoint_key = endpoint_key.strip()
            headers = {}
            for header_pair in headers_str.split(','):
                header_pair = header_pair.strip()
                if '=' not in header_pair:
                    continue
                header_name, env_var = header_pair.split('=', 1)
                headers[header_name.strip()] = env_var.strip()
            if headers:
                result[endpoint_key] = headers
        if result:
            print(f"✅ Custom auth headers carregados do .env: {len(result)} endpoint(s)")
        return result

    def _detect_custom_auth_headers_from_openapi(self, details: Dict) -> Dict[str, str]:
        """
        Detecta headers customizados de autenticação nos parâmetros do OpenAPI.
        Considera custom qualquer header required com nome prefixado por 'x-' ou 'X-'.
        Retorna: {"header-name": "ENV_VAR_NAME"}
        """
        custom = {}
        if not details:
            return custom
        parameters = details.get('parameters', [])
        for param in parameters:
            if param.get('in') == 'header' and param.get('required', False):
                name = param.get('name', '')
                if name.lower().startswith('x-'):
                    env_var = name.upper().replace('-', '_')
                    custom[name] = env_var
        return custom

    def _load_krakend_roles(self) -> Dict:
        krakend_roles = {}
        krakend_conf = os.getenv("KRAKEND_CONF", "").strip()
        endpoint_prefix = os.getenv("ENDPOINT_PREFIX", "").strip()
        if not krakend_conf:
            print("⚠️  KRAKEND_CONF não definido — roles do KrakenD não serão carregados")
            return krakend_roles
        if not Path(krakend_conf).exists():
            print(f"⚠️  KRAKEND_CONF não encontrado: {krakend_conf}")
            return krakend_roles
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
            print(f"✅ KrakenD roles carregados: {len(krakend_roles)} endpoints")
        except Exception as e:
            print(f"⚠️  Erro ao ler roles do Krakend: {e}")
        return krakend_roles

    def _load_krakend_disable_jwk(self) -> Dict:
        disable_jwk = {}
        krakend_conf = os.getenv("KRAKEND_CONF", "").strip()
        endpoint_prefix = os.getenv("ENDPOINT_PREFIX", "").strip()
        if not krakend_conf or not Path(krakend_conf).exists():
            return disable_jwk
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
                if jose and jose.get("disable_jwk_security") is True:
                    disable_jwk[(ep_path, ep_method)] = True
        except Exception as e:
            print(f"⚠️  Erro ao ler disable_jwk_security do Krakend: {e}")
        return disable_jwk

    def _path_candidates(self, path: str) -> List[str]:
        candidates = [path]
        if path.startswith('/api/v1/'):
            candidates.append(path.replace('/api/v1/', '/api/', 1))
        elif path.startswith('/api/'):
            candidates.append(path.replace('/api/', '/api/v1/', 1))
        if path.startswith('/v1/'):
            candidates.append('/api' + path)
            candidates.append('/api' + path[3:])
        return list(dict.fromkeys(candidates))

    def _make_example_filename(self, method: str, path: str) -> str:
        sanitized = path.lstrip("/")
        sanitized = re.sub(r"\{[^}/]+\}", "X", sanitized)
        sanitized = re.sub(r"[/\\\s]+", "_", sanitized)
        sanitized = re.sub(r"[^a-zA-Z0-9_\-]", "", sanitized)
        return f"{method.upper()}_{sanitized}.json"

    def _normalize_path(self, path: str) -> str:
        normalized = re.sub(r"\{[^}/]+\}", "{X}", path)
        normalized = re.sub(r":[^/]+", "{X}", normalized)
        return normalized

    def _resolve_custom_auth_headers(self, method: str, path: str, details: Optional[Dict]) -> Dict[str, str]:
        """
        Resolve custom auth headers para um endpoint, combinando:
        1. Detecção automática dos parâmetros OpenAPI (headers required com x-*)
        2. Override manual do .env (CUSTOM_AUTH_HEADERS) — prioridade alta
        """
        custom = {}
        if details:
            auto_detected = self._detect_custom_auth_headers_from_openapi(details)
            custom.update(auto_detected)
        endpoint_key = f"{method.upper()} {path}"
        if endpoint_key in self.custom_auth_headers_env:
            custom.update(self.custom_auth_headers_env[endpoint_key])
        if not custom:
            for candidate in self._path_candidates(path):
                candidate_key = f"{method.upper()} {candidate}"
                if candidate_key in self.custom_auth_headers_env:
                    custom.update(self.custom_auth_headers_env[candidate_key])
                    break
        return custom

    def enrich_endpoint(self, endpoint: Dict) -> Dict:
        path = endpoint.get('path', '')
        method = endpoint.get('method', '')

        details = None
        if self.openapi_data:
            paths = self.openapi_data.get('paths', {})
            method_lower = method.lower()
            for candidate in self._path_candidates(path):
                norm_candidate = self._normalize_path(candidate)
                for spec_path, spec_methods in paths.items():
                    if self._normalize_path(spec_path) == norm_candidate and method_lower in spec_methods:
                        details = spec_methods[method_lower]
                        break
                if details:
                    break

        if details:
            endpoint['summary'] = details.get('summary')
            endpoint['description'] = details.get('description')
            endpoint['openapi_parameters'] = details.get('parameters', [])

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

        roles = []
        norm_path_candidates = [self._normalize_path(p) for p in self._path_candidates(path)]
        if (path, method) in self.krakend_roles:
            roles = self.krakend_roles[(path, method)]
        else:
            for (k_path, k_method), k_roles in self.krakend_roles.items():
                if k_method == method and self._normalize_path(k_path) in norm_path_candidates:
                    roles = k_roles
                    break
        endpoint['roles'] = roles

        disable_jwk = False
        if (path, method) in self.krakend_disable_jwk:
            disable_jwk = True
        else:
            for (k_path, k_method), is_disabled in self.krakend_disable_jwk.items():
                if is_disabled and k_method == method and self._normalize_path(k_path) in norm_path_candidates:
                    disable_jwk = True
                    break
        endpoint['gateway_disable_jwk_security'] = disable_jwk

        # NOVO: Custom auth headers
        custom_headers = self._resolve_custom_auth_headers(method, path, details)
        if custom_headers:
            endpoint['custom_auth_headers'] = custom_headers
            print(f"   🔑 Custom auth headers: {list(custom_headers.keys())}")

        return endpoint

    def _enrich_krakend_only(self, endpoint: Dict) -> Dict:
        path = endpoint.get('path', '')
        method = endpoint.get('method', '')
        norm_candidates = [self._normalize_path(p) for p in self._path_candidates(path)]

        roles = []
        if (path, method) in self.krakend_roles:
            roles = self.krakend_roles[(path, method)]
        else:
            for (k_path, k_method), k_roles in self.krakend_roles.items():
                if k_method == method and self._normalize_path(k_path) in norm_candidates:
                    roles = k_roles
                    break
        endpoint['roles'] = roles

        disable_jwk = False
        if (path, method) in self.krakend_disable_jwk:
            disable_jwk = True
        else:
            for (k_path, k_method), is_disabled in self.krakend_disable_jwk.items():
                if is_disabled and k_method == method and self._normalize_path(k_path) in norm_candidates:
                    disable_jwk = True
                    break
        endpoint['gateway_disable_jwk_security'] = disable_jwk

        # NOVO: Custom auth headers (sem OpenAPI)
        endpoint_key = f"{method.upper()} {path}"
        if endpoint_key in self.custom_auth_headers_env:
            endpoint['custom_auth_headers'] = self.custom_auth_headers_env[endpoint_key]

        return endpoint


    def _enrich_krakend_only(self, endpoint: Dict) -> Dict:
        path = endpoint.get('path', '')
        method = endpoint.get('method', '')
        norm_candidates = [self._normalize_path(p) for p in self._path_candidates(path)]

        roles = []
        if (path, method) in self.krakend_roles:
            roles = self.krakend_roles[(path, method)]
        else:
            for (k_path, k_method), k_roles in self.krakend_roles.items():
                if k_method == method and self._normalize_path(k_path) in norm_candidates:
                    roles = k_roles
                    break
        endpoint['roles'] = roles

        disable_jwk = False
        if (path, method) in self.krakend_disable_jwk:
            disable_jwk = True
        else:
            for (k_path, k_method), is_disabled in self.krakend_disable_jwk.items():
                if is_disabled and k_method == method and self._normalize_path(k_path) in norm_candidates:
                    disable_jwk = True
                    break
        endpoint['gateway_disable_jwk_security'] = disable_jwk

        # Custom auth headers (sem OpenAPI, apenas do .env)
        endpoint_key = f"{method.upper()} {path}"
        if endpoint_key in self.custom_auth_headers_env:
            endpoint['custom_auth_headers'] = self.custom_auth_headers_env[endpoint_key]

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
            patterns_path = Path(__file__).resolve().parents[4] / "config" / "pii_patterns.json"
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
        path = endpoint.get('path', '').lower()
        method = endpoint.get('method', '').upper()

        pii_fields = []
        for pattern in self._get_pii_patterns():
            if pattern in path:
                pii_fields.append(pattern)

        auth_required = True
        auth_type = "jwt"
        if 'public' in path or 'health' in path or 'metrics' in path or 'swagger' in path:
            auth_required = False
            auth_type = "none"
        elif 'login' in path or 'auth' in path:
            auth_type = "basic"

        vulnerabilities = self.adv_detector.detect_vulnerabilities(endpoint, auth_required)

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

    def _cross_validate_vulns(self, llm_vulns: List[str], endpoint: Dict) -> List[str]:
        path = endpoint.get('path', '').lower()
        context = str(endpoint.get('context', '')).lower()
        method = endpoint.get('method', '').upper()
        code_only = context
        if '*/' in context:
            code_only = context[context.rfind('*/') + 2:]

        def _bola_direct_access(p: str) -> bool:
            segs = p.strip('/').split('/')
            for idx, s in enumerate(segs):
                if re.match(r'^:(id|user_id|account_id|document_id)\b', s):
                    if idx == len(segs) - 1:
                        return True
                    if segs[idx + 1].startswith(':'):
                        return True
            return False

        evidence = {
            'bola': _bola_direct_access(path),
            'bfla': bool(re.search(r'/admin|/internal|/manage/', path)) or
                    bool(re.search(r'req\.user\.role|hasrole\(|checkpermission\(|isadmin\(', code_only)),
            'injection': bool(re.search(
                r'req\.query\.\w|req\.params\.\w.*(?:sql|query|find|where)|'
                r'knex\.|sequelize\.|typeorm\.|\.raw\(|query\(`|query\(\s*["\']', code_only)),
            'ssrf': bool(re.search(
                r'fetch\((?:req\.|.*req\b)|axios\.(?:get|post|put|patch|delete)\((?:req\.|.*req\b)|'
                r'http\.(?:get|post)\((?:req\.|.*req\b)|got\((?:req\.|.*req\b)', code_only)),
            'broken_auth': bool(re.search(r'public|health|metrics|swagger|no.?auth|unauthenticated', path)) and
                           method in ('POST', 'PUT', 'PATCH', 'DELETE'),
            'mass_assignment': bool(re.search(
                r'\.save\(req\.body|object\.assign\(.*req\.body|'
                r'update\(.*req\.body|\.create\(req\.body|\.\.\.(req\.body)', code_only)),
            'security_misconfiguration': bool(re.search(
                r'/debug|/test-|/dev-|/private|/internal/', path)),
            'rate_limiting_absence': bool(re.search(
                r'/login|/auth|/register|/otp|/reset.?password|/forgot', path)) and
                                     method in ('POST', 'PUT', 'PATCH'),
            'xxe': bool(re.search(
                r'xml2js|xmlparser|libxml|domparser|parsestring.*xml|\.xml\b', code_only)),
            'open_redirect': bool(re.search(
                r'res\.redirect\(req\.|res\.redirect\(.*query\.|res\.redirect\(.*param', code_only)),
            'unsafe_consumption': bool(re.search(r'/webhook|/callback', path)) or
                                  bool(re.search(
                                      r'fetch\(.*req\.|axios\.\w+\(.*req\.', code_only)),
        }
        kept, discarded = [], []
        for vuln in llm_vulns:
            if evidence.get(vuln, False):
                kept.append(vuln)
            else:
                discarded.append(vuln)
        if discarded:
            print(f"   🔍 LLM cross-validate: descartados sem evidência → {discarded}")
        return kept

    def analyze_endpoint(self, endpoint: Dict, code_context: str = "", max_retries: int = 2) -> Dict:
        for attempt in range(max_retries):
            try:
                result = self._call_llm(endpoint, code_context)
                if result and 'error' not in result:
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
                        clean_vulns = self._cross_validate_vulns(clean_vulns, endpoint)
                        result['vulnerabilities'] = clean_vulns
                    else:
                        result['vulnerabilities'] = []
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
        effective_context = code_context or endpoint.get('context', '')
        if effective_context:
            effective_context = effective_context[:1500]
        context_section = f"""
Código-fonte relevante (trecho real do arquivo):
{effective_context}""" if effective_context else ""

        prompt = f"""Responda apenas com JSON. Analise o endpoint abaixo com base no código-fonte fornecido.
Endpoint: {endpoint.get('method', '')} {endpoint.get('path', '')}
{context_section}
Instruções:
- Liste em "vulnerabilities" APENAS as vulnerabilidades confirmadas pelo código acima.
- Se o código não evidenciar a vulnerabilidade, NÃO a inclua.
- Se não houver código suficiente para análise, retorne "vulnerabilities": [].
Formato exato (responda SOMENTE este JSON):
{{"pii_fields":[],"auth_required":false,"auth_type":"jwt","risk_level":"baixo","risk_reason":"","vulnerabilities":[],"business_purpose":"","critical_resource":false}}
Valores válidos para vulnerabilities: bola, bfla, injection, ssrf, broken_auth, mass_assignment, security_misconfiguration, rate_limiting_absence, xxe, open_redirect, unsafe_consumption"""

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
    """Gera relatório Markdown com OWASP e SANS diretamente no local especificado"""
    total = len(endpoints)
    if total == 0:
        print("⚠️ Nenhum endpoint para gerar relatório")
        return

    high_risk = sum(1 for e in endpoints if e.get('risk_level') == 'alto')
    medium_risk = sum(1 for e in endpoints if e.get('risk_level') == 'médio')
    low_risk = sum(1 for e in endpoints if e.get('risk_level') == 'baixo')
    has_pii = sum(1 for e in endpoints if e.get('pii_fields'))

    owasp_map = {}
    sans_map = {}
    for e in endpoints:
        for vuln in e.get('vulnerabilities_detailed', []):
            if vuln.get('owasp'):
                owasp_id = vuln['owasp']['id']
                owasp_name = vuln['owasp'].get('category') or vuln['owasp'].get('name', 'Unknown')
                if owasp_id not in owasp_map:
                    owasp_map[owasp_id] = {'count': 0, 'name': owasp_name}
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
    for e in endpoints:
        if e.get('risk_level') == 'alto':
            if e.get('vulnerabilities'):
                vulns = ', '.join(e.get('vulnerabilities', []))
            elif e.get('risk_reason'):
                vulns = f"sem mapeamento explícito ({e.get('risk_reason')})"
            else:
                vulns = 'sem mapeamento explícito'
            report += f"| {e.get('method', '')} | `{e.get('path', '')}` | {vulns} |\n"
    if high_risk == 0:
        report += "| Nenhum endpoint de alto risco detectado | - | - |\n"

    report += f"\n---\n*Relatório gerado por step4_analyzer_and_enricher.py em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}*\n"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"📊 Relatório salvo em: {output_file}")


def generate_summary_markdown(endpoints: List[Dict], output_file: Path, full_data: Dict) -> None:
    """Gera resumo markdown do mapeamento de endpoints no local especificado"""
    metadata = full_data.get('metadata', {})
    total = len(endpoints)
    endpoints_with_data = sum(1 for e in endpoints if e.get('realistic_examples'))
    methods_count = {}
    for e in endpoints:
        method = e.get('method', 'unknown')
        methods_count[method] = methods_count.get(method, 0) + 1

    markdown = f"""# Mapeamento de Endpoints - API

## 📊 Resumo

| Métrica | Valor |
|---------|-------|
| **Total de endpoints** | {total} |
| **Com dados de exemplo** | {endpoints_with_data} |
| **Data da análise** | {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} |
| **Projeto** | {metadata.get('project_name', 'N/A')} |

## 📈 Distribuição por Método HTTP

| Método | Quantidade |
|--------|------------|
"""
    for method, count in sorted(methods_count.items()):
        markdown += f"| {method} | {count} |\n"

    markdown += """
## 📋 Lista de Endpoints

| Método | Path | Resumo | Exemplo |
|--------|------|--------|---------|
"""
    for e in endpoints:
        method = e.get('method', '')
        path = e.get('path', '')
        summary = e.get('summary', '') or e.get('description', '') or e.get('business_purpose', '')
        has_example = '✅' if e.get('realistic_examples') else '❌'
        markdown += f"| {method} | `{path}` | {summary[:80]} | {has_example} |\n"

    markdown += f"\n---\n*Gerado automaticamente por step4_analyzer_and_enricher.py em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}*\n"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(markdown)
    print(f"📝 Resumo salvo em: {output_file}")


def find_latest_scan_endpoints(base_dir: Union[str, Path]) -> Optional[str]:
    """Procura o all_endpoints.json do scan mais recente"""
    import glob
    base_dir = str(base_dir)
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
                              llm_url: str = None,
                              limit: int = None,
                              output_dir: Path = None,
                              data_dir: Path = None,
                              env_file: Optional[str] = None) -> Dict[str, Any]:
    """Função principal unificada"""
    pipeline_tests_dir = Path(output_dir) if output_dir else Path("output")
    pipeline_tests_dir.mkdir(parents=True, exist_ok=True)

    if endpoints_file:
        with open(endpoints_file, 'r', encoding='utf-8') as f:
            full_data = json.load(f)
        if isinstance(full_data, dict) and 'endpoints' in full_data:
            endpoints = full_data['endpoints']
        else:
            endpoints = full_data
        full_data = {'endpoints': endpoints}
    elif not endpoints:
        raise ValueError("Forneça endpoints_file ou endpoints")
    else:
        full_data = {'endpoints': endpoints}

    total_available = len(endpoints)
    if limit is not None:
        endpoints = endpoints[:limit]

    print(f"\n📁 Carregados {total_available} endpoints do scan" + (f" (limitado a {limit})" if limit is not None else ""))
    print(f"🤖 Modo: {'Híbrido (LLM + Heurística)' if use_llm else 'Heurística pura'}")
    if openapi_file:
        print(f"📄 Enriquecendo com OpenAPI: {openapi_file}")
    print(f"📁 Diretório de saída (.md): {output_dir}")
    print(f"📁 Diretório de salvamento (JSON): {pipeline_tests_dir}")

    analyzer_backend = backend if use_llm else "gatiator"
    analyzer = LocalLLMAnalyzer(model=model, backend=analyzer_backend, llm_url=llm_url)
    enricher = OpenAPIEnricher(
        Path(openapi_file) if openapi_file else None,
        output_dir=output_dir,
        data_dir=data_dir,
        env_file=env_file
    )

    start_time = time.time()
    enriched = []
    total = len(endpoints)

    for i, endpoint in enumerate(endpoints, 1):
        print(f"\n📊 {i}/{total}: {endpoint.get('method', '')} {endpoint.get('path', '')}")

        if openapi_file:
            endpoint = enricher.enrich_endpoint(endpoint)
        else:
            endpoint = enricher._enrich_krakend_only(endpoint)

        if use_llm:
            security_analysis = analyzer.analyze_endpoint(endpoint)
        else:
            security_analysis = analyzer._simple_heuristic_analysis(endpoint)

        enriched_endpoint = {**endpoint, **security_analysis}

        if enriched_endpoint.get('gateway_disable_jwk_security'):
            vulns = list(enriched_endpoint.get('vulnerabilities', []))
            changed = False
            for v in ('broken_auth', 'security_misconfiguration'):
                if v not in vulns:
                    vulns.append(v)
                    changed = True
            if changed:
                enriched_endpoint['vulnerabilities'] = vulns
                enriched_endpoint['vulnerabilities_detailed'] = analyzer.vuln_db.enrich_vulnerabilities(vulns)
                enriched_endpoint['owasp_summary'] = analyzer.vuln_db.get_owasp_summary(vulns)
                enriched_endpoint['sans_summary'] = analyzer.vuln_db.get_sans_summary(vulns)
                enriched_endpoint['risk_level'] = 'alto'
                enriched_endpoint['risk_score'] = max(float(enriched_endpoint.get('risk_score', 0.1)), 0.85)
                enriched_endpoint['risk_reason'] = 'Gateway com disable_jwk_security=true: bypass de validação JWT possível'

        if (
            enriched_endpoint.get('risk_level') == 'alto'
            and not enriched_endpoint.get('gateway_disable_jwk_security')
            and not enriched_endpoint.get('vulnerabilities')
            and not enriched_endpoint.get('pii_fields')
        ):
            method = str(enriched_endpoint.get('method', '')).upper()
            if method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
                enriched_endpoint['risk_level'] = 'médio'
                enriched_endpoint['risk_score'] = min(float(enriched_endpoint.get('risk_score', 0.9)), 0.5)
                enriched_endpoint['risk_reason'] = 'Risco adjusted por coerência: sem vulnerabilidades/PII explícitas (operação de escrita)'
            else:
                enriched_endpoint['risk_level'] = 'baixo'
                enriched_endpoint['risk_score'] = min(float(enriched_endpoint.get('risk_score', 0.9)), 0.1)
                enriched_endpoint['risk_reason'] = 'Risco ajustado por coerência: sem vulnerabilidades/PII explícitas'

        vulns_present = bool(enriched_endpoint.get('vulnerabilities'))
        if vulns_present and enriched_endpoint.get('risk_level') == 'baixo':
            detailed = enriched_endpoint.get('vulnerabilities_detailed', []) or []
            severities = {str(v.get('severity', '')).lower() for v in detailed if isinstance(v, dict)}
            if 'critical' in severities or 'high' in severities:
                enriched_endpoint['risk_level'] = 'alto'
                enriched_endpoint['risk_score'] = max(float(enriched_endpoint.get('risk_score', 0.1)), 0.85)
                enriched_endpoint['risk_reason'] = 'Risco elevado por coerência: vulnerabilidades de severidade alta/crítica detectadas'
            elif 'medium' in severities or not severities:
                enriched_endpoint['risk_level'] = 'médio'
                enriched_endpoint['risk_score'] = max(float(enriched_endpoint.get('risk_score', 0.1)), 0.5)
                enriched_endpoint['risk_reason'] = 'Risco ajustado por coerência: vulnerabilidades detectadas'

        enriched.append(enriched_endpoint)

        vuln_count = len(enriched_endpoint.get('vulnerabilities', []))
        owasp_count = len(enriched_endpoint.get('owasp_summary', []))
        print(f"   ✅ Vulns: {vuln_count} | Risco: {enriched_endpoint.get('risk_level', '?')} | OWASP: {owasp_count}")

    elapsed = time.time() - start_time

    json_output = pipeline_tests_dir / "enriched_endpoints.json"
    with open(json_output, 'w', encoding='utf-8') as f:
        json.dump(enriched, f, indent=2, ensure_ascii=False)

    report_file = output_dir / "final_security_report.md"
    generate_enhanced_report(enriched, report_file)

    summary_file = output_dir / "test_api_summary.md"
    generate_summary_markdown(enriched, summary_file, full_data)

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
    print(f"📝 Resumo salvo em: {summary_file}")

    return {"summary": stats, "endpoints": enriched, "high_risk_endpoints": [e for e in enriched if e.get('risk_level') == 'alto']}


def main():
    parser = argparse.ArgumentParser(
        description="Analisador UNIFICADO de segurança e enriquecimento de API",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("endpoints_file", nargs="?", help="Caminho para all_endpoints.json (opcional: busca automático)")
    parser.add_argument("--openapi", "-o", help="Arquivo OpenAPI/Swagger (JSON ou YAML) para enriquecimento")
    parser.add_argument("--llm-backend", choices=["gatiator", "ollama", "none"], default="none", help="Backend LLM")
    parser.add_argument("--llm-model", default="codellama:7b", help="Modelo LLM")
    parser.add_argument("--no-llm", action="store_true", help="Usa apenas heurística (recomendado para CI/CD)")
    parser.add_argument("--limit", "-n", type=int, default=None, metavar="N", help="Analisa apenas os primeiros N endpoints")
    parser.add_argument("--output-dir", "-d", default=None, help="Diretório para saída (subpasta da raiz)")
    add_env_arg(parser)
    parser.add_argument("--verbose", action="store_true", help="Exibe logs detalhados")

    args = parser.parse_args()
    load_environment(env_file=args.env_file, verbose=args.verbose)

    project_root = Path(__file__).resolve().parent.parent.parent.parent

    if args.output_dir:
        output_dir = (project_root / args.output_dir).resolve()
    else:
        env_output_dir = os.getenv("REPORTS_DIR", "output")
        output_dir = (project_root / env_output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.endpoints_file:
        endpoints_path = args.endpoints_file
    else:
        endpoints_path = find_latest_scan_endpoints(output_dir)
        if not endpoints_path:
            endpoints_path = find_latest_scan_endpoints(project_root / "output")
        if not endpoints_path:
            print(f"❌ Nenhum arquivo all_endpoints.json encontrado em {output_dir} ou na raiz.")
            print("💡 Execute primeiro o passo de escaneamento.")
            sys.exit(1)
        print(f"🔍 Usando scan mais recente: {endpoints_path}")

    use_llm = not args.no_llm and args.llm_backend != "none"

    if args.limit is not None:
        print(f"⚠️  Modo validação: analisando apenas os primeiros {args.limit} endpoints (--limit {args.limit})")

    results = analyze_project_endpoints(
        endpoints_file=endpoints_path,
        openapi_file=args.openapi,
        model=args.llm_model,
        use_llm=use_llm,
        backend=args.llm_backend if use_llm else "none",
        limit=args.limit,
        output_dir=output_dir,
        env_file=args.env_file
    )

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