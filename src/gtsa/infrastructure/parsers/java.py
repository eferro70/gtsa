import re
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from tree_sitter import Language, Parser
import tree_sitter_java
from dataclasses import dataclass, asdict
from .base import BaseParser, ApiEndpoint

@dataclass
class ApiEndpoint:
    """Representa um endpoint de API encontrado"""
    path: str
    method: str
    handler: str
    parameters: List[Dict[str, str]]
    file_path: str
    line_number: int
    auth_required: Optional[bool] = None
    pii_fields: List[str] = None

    def to_dict(self):
        return asdict(self)

# Anotações HTTP do Spring que mapeiam para métodos HTTP
SPRING_METHOD_ANNOTATIONS = {
    'GetMapping':     'GET',
    'PostMapping':    'POST',
    'PutMapping':     'PUT',
    'PatchMapping':   'PATCH',
    'DeleteMapping':  'DELETE',
    'RequestMapping': 'REQUEST',
}

# Anotações HTTP do Retrofit que mapeiam para métodos HTTP
RETROFIT_METHOD_ANNOTATIONS = {
    'GET':     'GET',
    'POST':    'POST',
    'PUT':     'PUT',
    'PATCH':   'PATCH',
    'DELETE':  'DELETE',
    'HEAD':    'HEAD',
    'OPTIONS': 'OPTIONS',
    'HTTP':    'REQUEST',
}

# Anotações HTTP do JAX-RS que mapeiam para métodos HTTP
JAXRS_METHOD_ANNOTATIONS = {
    'GET':     'GET',
    'POST':    'POST',
    'PUT':     'PUT',
    'DELETE':  'DELETE',
    'HEAD':    'HEAD',
    'OPTIONS': 'OPTIONS',
    'PATCH':   'PATCH',
}

# Dicionário unificado para suportar todos os frameworks
SUPPORTED_HTTP_ANNOTATIONS = {
    **SPRING_METHOD_ANNOTATIONS,
    **RETROFIT_METHOD_ANNOTATIONS,
    **JAXRS_METHOD_ANNOTATIONS
}

# Anotações de segurança comuns
SECURITY_ANNOTATIONS = {
    'PreAuthorize', 'PostAuthorize', 'Secured', 'RolesAllowed',
    'PermitAll', 'DenyAll', 'Authenticated',
}

# Anotações JAX-RS para parâmetros
JAXRS_PARAM_ANNOTATIONS = {
    'PathParam': 'path',
    'QueryParam': 'query',
    'HeaderParam': 'header',
    'FormParam': 'form',
    'BeanParam': 'bean',
    'MatrixParam': 'matrix',
    'CookieParam': 'cookie',
}

# Anotações Spring para parâmetros
SPRING_PARAM_ANNOTATIONS = {
    'PathVariable': 'path',
    'RequestParam': 'query',
    'RequestBody': 'body',
    'RequestHeader': 'header',
    'RequestPart': 'part',
    'ModelAttribute': 'model',
}

# Anotações Retrofit para parâmetros
RETROFIT_PARAM_ANNOTATIONS = {
    'Path': 'path',
    'Query': 'query',
    'Body': 'body',
    'Header': 'header',
    'Field': 'form',
    'Part': 'part',
    'QueryMap': 'query_map',
    'FieldMap': 'form_map',
    'HeaderMap': 'header_map',
}

# Unificar anotações de parâmetros
ALL_PARAM_ANNOTATIONS = {
    **JAXRS_PARAM_ANNOTATIONS,
    **SPRING_PARAM_ANNOTATIONS,
    **RETROFIT_PARAM_ANNOTATIONS
}


class JavaSpringParser(BaseParser):
    """Parser específico para Java / Spring Boot, Retrofit e JAX-RS"""
    
    def __init__(self, debug: bool = False):
        super().__init__("java")
        self.supported_extensions = {'.java'}
        self.ignore_suffixes = {'Test.java', 'IT.java', 'Spec.java'}
        self.debug = debug

        JAVA_LANGUAGE = Language(tree_sitter_java.language())
        self.parser = Parser(JAVA_LANGUAGE)
        self.language = JAVA_LANGUAGE
        
        if self.debug:
            print("✅ Parser configurado para Java / Spring Boot, Retrofit e JAX-RS (modo debug ativado)")

    def _log(self, message: str):
        """Log de debug condicional"""
        if self.debug:
            print(f"🔍 {message}")

    def parse_code(self, code: str):
        return self.parser.parse(code.encode("utf8"))

    def get_root_node(self, code: str):
        tree = self.parser.parse(code.encode("utf8"))
        return tree.root_node

    def _get_node_text(self, node) -> str:
        return node.text.decode("utf8")

    def _is_external_url(self, path: str) -> bool:
        return path.startswith(('http://', 'https://', 'ftp://', 'ws://'))

    def _get_annotation_name(self, annotation_node) -> str:
        """Extrai o nome da anotação"""
        for child in annotation_node.children:
            if child.type == 'identifier':
                name = self._get_node_text(child)
                self._log(f"Anotação encontrada: {name}")
                return name
            elif child.type == 'scoped_identifier':
                full_name = self._get_node_text(child)
                if '.' in full_name:
                    name = full_name.split('.')[-1]
                    self._log(f"Anotação scoped encontrada: {full_name} -> {name}")
                    return name
                return full_name
            elif child.type == 'qualified_identifier':
                full_name = self._get_node_text(child)
                if '.' in full_name:
                    name = full_name.split('.')[-1]
                    self._log(f"Anotação qualified encontrada: {full_name} -> {name}")
                    return name
                return full_name
        return ""

    def _get_annotation_value(self, annotation_node, attr: str = "value") -> Optional[str]:
        """Extrai o valor de um atributo da anotação"""
        args_node = None
        for child in annotation_node.children:
            if child.type == 'annotation_argument_list':
                args_node = child
                break

        if args_node is None:
            return None

        raw = self._get_node_text(args_node).strip('()')
        
        # Se for apenas um valor sem nome de atributo (ex: @Path("/users"))
        if attr == "value" and not re.search(r'\b\w+\s*=', raw):
            m = re.search(r'"([^"]*)"', raw)
            if m:
                return m.group(1)
            m = re.search(r'^\s*([^{}\s,]+)\s*$', raw)
            if m:
                return m.group(1)
            return None

        # Busca atributo específico (ex: @Path(value = "/users"))
        pattern = rf'\b{re.escape(attr)}\s*=\s*(?:"([^"]*)"|\{{([^}}]*)\}}|(\S+?)(?:\s*[,)]|$))'
        m = re.search(pattern, raw)
        if not m:
            return None

        if m.group(1) is not None:
            return m.group(1)
        if m.group(2) is not None:
            return m.group(2).strip()
        return m.group(3).strip() if m.group(3) else None

    def _get_annotation_array_value(self, annotation_node, attr: str = "value") -> List[str]:
        """Extrai valores de array de uma anotação"""
        raw_val = self._get_annotation_value(annotation_node, attr)
        if not raw_val:
            return []
        
        if raw_val.startswith('{') and raw_val.endswith('}'):
            strings = re.findall(r'"([^"]*)"', raw_val)
            return strings if strings else [raw_val.strip('{}').strip()]
        
        strings = re.findall(r'"([^"]*)"', raw_val)
        return strings if strings else [raw_val]

    def _extract_http_method_from_annotation(self, annotation_node) -> Optional[str]:
        """Extrai método HTTP de anotações como @RequestMapping(method = RequestMethod.GET)"""
        raw = self._get_annotation_value(annotation_node, "method")
        if not raw:
            return None
        
        m = re.search(r'RequestMethod\.(\w+)', raw)
        if m:
            return m.group(1).upper()
        
        m = re.search(r'"?(\w+)"?', raw)
        return m.group(1).upper() if m else raw.upper()

    def _extract_class_annotations(self, root_node) -> Dict[str, Any]:
        """Extrai todas as anotações da classe/interface"""
        class_info = {
            'base_path': '',
            'security_annotations': [],
            'produces': '',
            'consumes': '',
            'is_controller': False,
        }
        
        for node in self._walk(root_node):
            if node.type in ('class_declaration', 'interface_declaration'):
                for child in node.children:
                    if child.type == 'modifiers':
                        for mod in child.children:
                            if mod.type == 'annotation':
                                ann_name = self._get_annotation_name(mod)
                                
                                # JAX-RS @Path
                                if ann_name == 'Path':
                                    path = self._get_annotation_value(mod, 'value')
                                    if path:
                                        class_info['base_path'] = path
                                        self._log(f"Base path da classe (JAX-RS): {path}")
                                
                                # Spring @RequestMapping
                                elif ann_name == 'RequestMapping':
                                    paths = self._get_annotation_array_value(mod, 'value')
                                    if paths:
                                        class_info['base_path'] = paths[0]
                                        self._log(f"Base path da classe (Spring): {paths[0]}")
                                
                                # Anotações de segurança
                                elif ann_name in SECURITY_ANNOTATIONS:
                                    class_info['security_annotations'].append(ann_name)
                                
                                # @Produces / @Consumes (JAX-RS)
                                elif ann_name == 'Produces':
                                    class_info['produces'] = self._get_annotation_value(mod, 'value') or ''
                                elif ann_name == 'Consumes':
                                    class_info['consumes'] = self._get_annotation_value(mod, 'value') or ''
                                
                                # Spring @RestController, @Controller
                                elif ann_name in ('RestController', 'Controller'):
                                    class_info['is_controller'] = True
                
                break
        
        return class_info

    def _join_paths(self, base: str, path: str) -> str:
        """Junta paths base e path do método corretamente"""
        if not base or base == '/':
            base = ''
        
        if not path:
            return f"/{base}" if base else "/"
        
        base = base.rstrip('/')
        path = path.lstrip('/')
        
        if base and path:
            return f"/{base}/{path}"
        elif base:
            return f"/{base}"
        else:
            return f"/{path}"

    def _extract_method_annotations(self, modifiers_node) -> Dict[str, Any]:
        """Extrai todas as anotações do método"""
        method_info = {
            'http_method': None,
            'path': None,
            'security_annotations': [],
            'produces': '',
            'consumes': '',
        }
        
        if not modifiers_node:
            return method_info
        
        all_annotations = []
        
        # PRIMEIRA PASSADA: Procura por anotações de método HTTP
        for mod in modifiers_node.children:
            if mod.type != 'annotation':
                continue
            
            ann_name = self._get_annotation_name(mod)
            all_annotations.append(ann_name)
            self._log(f"  📌 Anotação no método: {ann_name}")
            
            # JAX-RS: @GET, @POST, @PUT, @DELETE, etc.
            if ann_name in JAXRS_METHOD_ANNOTATIONS:
                method_info['http_method'] = JAXRS_METHOD_ANNOTATIONS[ann_name]
                self._log(f"  ✅ Método HTTP encontrado (JAX-RS): {ann_name}")
            
            # Spring: @RequestMapping com method
            elif ann_name == 'RequestMapping':
                http_method = self._extract_http_method_from_annotation(mod)
                if http_method:
                    method_info['http_method'] = http_method
                    self._log(f"  ✅ Método HTTP encontrado (RequestMapping): {http_method}")
                
                paths = self._get_annotation_array_value(mod, 'value')
                if paths and not method_info['path']:
                    method_info['path'] = paths[0]
                    self._log(f"  📍 Path do método (RequestMapping): {paths[0]}")
            
            # Spring específico
            elif ann_name in SPRING_METHOD_ANNOTATIONS:
                if not method_info['http_method']:
                    method_info['http_method'] = SPRING_METHOD_ANNOTATIONS[ann_name]
                    self._log(f"  ✅ Método HTTP encontrado (Spring): {ann_name}")
                
                paths = self._get_annotation_array_value(mod, 'value')
                if paths and not method_info['path']:
                    method_info['path'] = paths[0]
                    self._log(f"  📍 Path do método ({ann_name}): {paths[0]}")
            
            # Retrofit específico
            elif ann_name in RETROFIT_METHOD_ANNOTATIONS:
                if not method_info['http_method']:
                    method_info['http_method'] = RETROFIT_METHOD_ANNOTATIONS[ann_name]
                    self._log(f"  ✅ Método HTTP encontrado (Retrofit): {ann_name}")
                
                paths = self._get_annotation_array_value(mod, 'value')
                if paths and not method_info['path']:
                    method_info['path'] = paths[0]
                    self._log(f"  📍 Path do método ({ann_name}): {paths[0]}")
        
        # SEGUNDA PASSADA: Procura por @Path (JAX-RS) e outras anotações
        for mod in modifiers_node.children:
            if mod.type != 'annotation':
                continue
            
            ann_name = self._get_annotation_name(mod)
            
            # JAX-RS @Path (separado do método HTTP)
            if ann_name == 'Path':
                path = self._get_annotation_value(mod, 'value')
                if path and not method_info['path']:
                    method_info['path'] = path
                    self._log(f"  📍 Path do método (JAX-RS @Path): {path}")
            
            # Anotações de segurança
            elif ann_name in SECURITY_ANNOTATIONS:
                method_info['security_annotations'].append(ann_name)
            
            # JAX-RS @Produces / @Consumes
            elif ann_name == 'Produces':
                method_info['produces'] = self._get_annotation_value(mod, 'value') or ''
            elif ann_name == 'Consumes':
                method_info['consumes'] = self._get_annotation_value(mod, 'value') or ''
        
        return method_info

    def _infer_http_method_from_name(self, method_name: str) -> Optional[str]:
        """Infere o método HTTP baseado no nome do método (fallback para métodos sem anotações)"""
        if not method_name:
            return None
        
        method_lower = method_name.lower()
        
        # GET patterns - métodos que buscam/consultam dados
        get_patterns = ['get', 'find', 'list', 'consult', 'buscar', 'obter', 'ver', 'show', 'view', 'load', 
                        'timestamp', 'status', 'verificar', 'check', 'is', 'has', 'existe']
        if any(method_lower.startswith(prefix) or method_lower.endswith(prefix) for prefix in get_patterns):
            return 'GET'
        
        # POST patterns - métodos que criam/enviam/processam dados
        post_patterns = ['post', 'create', 'add', 'save', 'insert', 'cadastrar', 'solicitar', 'enviar', 
                         'send', 'submit', 'validar', 'pre', 'registrar', 'gerar', 'emitir', 'instalar',
                         'criar', 'novo', 'new', 'processar', 'executar', 'ativar']
        if any(method_lower.startswith(prefix) or method_lower.endswith(prefix) for prefix in post_patterns):
            return 'POST'
        
        # PUT patterns - métodos que atualizam/modificam dados
        put_patterns = ['put', 'update', 'edit', 'modify', 'change', 'atualizar', 'alterar', 'renovar',
                        'editar', 'modificar', 'ajustar']
        if any(method_lower.startswith(prefix) or method_lower.endswith(prefix) for prefix in put_patterns):
            return 'PUT'
        
        # DELETE patterns - métodos que removem/desativam dados
        delete_patterns = ['delete', 'remove', 'desativar', 'inativar', 'deletar', 'destroy', 'excluir',
                           'remover', 'cancelar']
        if any(method_lower.startswith(prefix) or method_lower.endswith(prefix) for prefix in delete_patterns):
            return 'DELETE'
        
        # PATCH patterns
        patch_patterns = ['patch', 'partial', 'parcial']
        if any(method_lower.startswith(prefix) for prefix in patch_patterns):
            return 'PATCH'
        
        # Regras especiais baseadas no contexto do nome
        # OTP operations são sempre POST
        if 'otp' in method_lower:
            return 'POST'
        
        # Pre-emissão e pré-instalação são POST
        if 'pre' in method_lower and ('certificado' in method_lower or 'instalacao' in method_lower or 'emissao' in method_lower):
            return 'POST'
        
        # Pedidos: consultar = GET, criar = POST
        if 'pedido' in method_lower:
            if any(p in method_lower for p in ['consultar', 'ver', 'listar', 'obter', 'get']):
                return 'GET'
            return 'POST'
        
        # Cadastro de dispositivo = POST
        if 'dispositivo' in method_lower and any(p in method_lower for p in ['cadastrar', 'criar', 'registrar']):
            return 'POST'
        
        # Assinatura: enviar desafio = POST, verificar status = GET
        if 'assinatura' in method_lower:
            if any(p in method_lower for p in ['enviar', 'solicitar', 'criar']):
                return 'POST'
            if any(p in method_lower for p in ['verificar', 'status', 'consultar']):
                return 'GET'
        
        # Certificados: listar = GET, criar/instalar = POST, remover = DELETE
        if 'certificado' in method_lower:
            if any(p in method_lower for p in ['listar', 'consultar', 'obter', 'get']):
                return 'GET'
            if any(p in method_lower for p in ['remover', 'deletar', 'excluir']):
                return 'DELETE'
            if any(p in method_lower for p in ['criar', 'cadastrar', 'instalar', 'emitir']):
                return 'POST'
        
        # Default: se não conseguiu inferir, assume POST (mais comum em APIs)
        self._log(f"  🔄 Método HTTP inferido como POST (default) para: {method_name}")
        return 'POST'

    def _is_public_method(self, node) -> bool:
        """Verifica se o método é público"""
        for child in node.children:
            if child.type == 'modifiers':
                text = self._get_node_text(child)
                if 'public' in text:
                    return True
        return False

    def _has_http_annotation(self, modifiers_node) -> bool:
        """Verifica se o método tem anotações HTTP explícitas"""
        if not modifiers_node:
            return False
        
        for mod in modifiers_node.children:
            if mod.type == 'annotation':
                ann_name = self._get_annotation_name(mod)
                if ann_name in SUPPORTED_HTTP_ANNOTATIONS:
                    return True
        return False

    def _has_path_annotation(self, modifiers_node) -> bool:
        """Verifica se o método tem anotação @Path"""
        if not modifiers_node:
            return False
        
        for mod in modifiers_node.children:
            if mod.type == 'annotation':
                ann_name = self._get_annotation_name(mod)
                if ann_name == 'Path':
                    return True
        return False

    def _is_auxiliary_method(self, method_name: str) -> bool:
        """Verifica se o método é auxiliar (validação, verificação, etc.)"""
        if not method_name:
            return True
        
        method_lower = method_name.lower()
        
        # Padrões de métodos auxiliares
        auxiliary_patterns = [
            'validar', 'validate', 'check', 'verificar', 'is', 'has', 'contains',
            'tratar', 'handle', 'process', 'build', 'criar', 'create', 'from',
            'set', 'equals', 'hashcode', 'tostring', 'montar', 'adicionar',
            'obter', 'get'
        ]
        
        # Se o método começa com algum padrão auxiliar
        if any(method_lower.startswith(p) for p in auxiliary_patterns):
            return True
        
        # Métodos muito curtos (provavelmente getters/setters)
        if len(method_name) < 4:
            return True
        
        return False

    def _is_rest_class(self, root_node) -> bool:
        """Verifica se a classe é uma classe REST"""
        rest_annotations = {
            'Path', 'RestController', 'Controller', 
            'RequestMapping', 'ApplicationPath'
        }
        
        for node in self._walk(root_node):
            if node.type in ('class_declaration', 'interface_declaration'):
                for child in node.children:
                    if child.type == 'modifiers':
                        for mod in child.children:
                            if mod.type == 'annotation':
                                ann_name = self._get_annotation_name(mod)
                                if ann_name in rest_annotations:
                                    return True
        return False

    def _extract_method_parameters(self, method_node) -> List[Dict[str, str]]:
        """Extrai parâmetros do método com suas anotações"""
        params = []

        formal_params = None
        for child in method_node.children:
            if child.type == 'formal_parameters':
                formal_params = child
                break

        if not formal_params:
            return params

        for child in formal_params.children:
            if child.type == 'formal_parameter':
                param_info = self._parse_formal_parameter(child)
                if param_info:
                    params.append(param_info)

        return params

    def _parse_formal_parameter(self, param_node) -> Optional[Dict[str, str]]:
        """Analisa um parâmetro formal e extrai suas anotações"""
        annotations = []
        param_type = 'unknown'
        param_name = 'unknown'
        source = 'unknown'

        for child in param_node.children:
            if child.type == 'modifiers':
                for mod in child.children:
                    if mod.type == 'annotation':
                        ann_name = self._get_annotation_name(mod)
                        annotations.append(ann_name)
                        
                        if ann_name in ALL_PARAM_ANNOTATIONS:
                            source = ALL_PARAM_ANNOTATIONS[ann_name]
                            self._log(f"Parâmetro com anotação {ann_name} -> source: {source}")
            
            elif child.type in ('type_identifier', 'generic_type',
                                'array_type', 'integral_type', 'floating_point_type',
                                'boolean_type', 'void_type'):
                param_type = self._get_node_text(child)
            
            elif child.type == 'identifier':
                param_name = self._get_node_text(child)

        # Ignora parâmetros de infraestrutura
        infra_types = {
            'HttpServletRequest', 'HttpServletResponse', 'HttpSession',
            'Model', 'ModelAndView', 'Principal', 'BindingResult',
            'UriInfo', 'SecurityContext', 'HttpHeaders', 'Request',
            'Response', 'ServletContext', 'PageContext', 'JspWriter'
        }
        
        if param_type in infra_types:
            self._log(f"Ignorando parâmetro de infraestrutura: {param_type} {param_name}")
            return None

        return {
            'name': param_name,
            'type': param_type,
            'source': source,
            'annotations': annotations,
        }

    def _extract_security_info(self, method_info: Dict, class_annotations: List[str]) -> Optional[bool]:
        """Determina se o endpoint requer autenticação"""
        if 'PermitAll' in class_annotations:
            return False
        
        security_anns = method_info.get('security_annotations', [])
        
        if 'PermitAll' in security_anns:
            return False
        if any(ann in ('PreAuthorize', 'PostAuthorize', 'Secured', 'RolesAllowed', 'DenyAll') 
               for ann in security_anns):
            return True
        
        if any(ann in ('PreAuthorize', 'Secured', 'RolesAllowed') for ann in class_annotations):
            return True
        
        return None

    def _extract_method_body(self, code: str, start_pos: int) -> Optional[str]:
        """Extrai o corpo do método a partir de uma posição inicial"""
        if start_pos >= len(code):
            return None
            
        brace_pos = code.find('{', start_pos)
        if brace_pos == -1:
            return None
            
        depth = 0
        for i in range(brace_pos, len(code)):
            if code[i] == '{':
                depth += 1
            elif code[i] == '}':
                depth -= 1
                if depth == 0:
                    return code[brace_pos:i+1]
        
        return None

    def _resolve_service_context(self, method_body: str, source_root: str) -> str:
        """Resolve contexto de serviços chamados pelo método"""
        if not source_root or not method_body:
            return ""

        extra = ""
        source_path = Path(source_root)

        service_calls = re.findall(
            r'(?:this\.)?([a-z][A-Za-z0-9_]*[Ss]ervice|[a-z][A-Za-z0-9_]*[Bb][Cc])\.([a-zA-Z][a-zA-Z0-9_]*)\s*\(',
            method_body,
        )

        seen_services: Set[str] = set()
        for svc_var, svc_method in service_calls[:2]:
            if svc_var in seen_services:
                continue
            seen_services.add(svc_var)

            class_name = svc_var[0].upper() + svc_var[1:]

            candidates = []
            try:
                for p in source_path.rglob(f"{class_name}.java"):
                    parts = p.parts
                    if any(s in parts for s in ('test', 'Test', '__tests__')):
                        continue
                    if p.stem.endswith(('Test', 'IT', 'Spec')):
                        continue
                    candidates.append(p)
            except Exception:
                continue

            if not candidates:
                continue

            svc_file = min(candidates, key=lambda p: len(p.parts))
            try:
                svc_code = svc_file.read_text(encoding='utf-8')
            except Exception:
                continue

            method_pattern = rf'(?:public|protected|private)\s+[\w<>\[\]]+\s+{re.escape(svc_method)}\s*\([^)]*\)\s*(?:throws\s+[\w,\s]+)?\s*\{{'
            m = re.search(method_pattern, svc_code)
            if not m:
                continue
                
            svc_body = self._extract_method_body(svc_code, m.start())
            if not svc_body:
                continue

            if len(svc_body) > 3000:
                svc_body = svc_body[:3000] + "\n// [truncado]"

            extra += f"\n// --- service: {class_name}.{svc_method} ---\n{svc_body}"

            repo_calls = re.findall(
                r'(?:this\.)?([a-z][A-Za-z0-9_]*(?:[Rr]epository|[Rr]epo))\.([a-zA-Z][a-zA-Z0-9_]*)\s*\(',
                svc_body,
            )

            seen_repos: Set[str] = set()
            for repo_var, repo_method in repo_calls[:3]:
                key = f"{repo_var}.{repo_method}"
                if key in seen_repos:
                    continue
                seen_repos.add(key)

                repo_class = repo_var[0].upper() + repo_var[1:]
                repo_candidates = []
                try:
                    for p in source_path.rglob(f"{repo_class}.java"):
                        if any(s in p.parts for s in ('test', 'Test')):
                            continue
                        repo_candidates.append(p)
                except Exception:
                    continue

                if not repo_candidates:
                    continue

                repo_file = min(repo_candidates, key=lambda p: len(p.parts))
                try:
                    repo_code = repo_file.read_text(encoding='utf-8')
                except Exception:
                    continue

                repo_pattern = rf'(?:public|protected|private|default)\s+[\w<>\[\]]+\s+{re.escape(repo_method)}\s*\([^)]*\)\s*(?:throws\s+[\w,\s]+)?\s*\{{'
                m_repo = re.search(repo_pattern, repo_code)
                if not m_repo:
                    continue
                    
                repo_body = self._extract_method_body(repo_code, m_repo.start())
                if not repo_body:
                    continue

                if len(repo_body) > 2000:
                    repo_body = repo_body[:2000] + "\n// [truncado]"

                extra += f"\n// --- repository: {repo_class}.{repo_method} ---\n{repo_body}"

        return extra

    def _extract_route_metadata(self, code: str, method_node, source_root: str = None) -> Dict[str, Any]:
        """Extrai metadados adicionais da rota"""
        start_line = method_node.start_point[0] + 1
        end_line = method_node.end_point[0] + 1

        lines = code.split('\n')
        context_start = max(0, start_line - 20)
        context_end = min(len(lines), end_line + 4)
        context = '\n'.join(lines[context_start:context_end])

        method_text = self._get_node_text(method_node)
        method_start = code.find(method_text)
        
        if method_start != -1:
            brace_pos = code.find('{', method_start)
            if brace_pos != -1:
                method_body = self._extract_method_body(code, brace_pos)
                if method_body and source_root:
                    svc_context = self._resolve_service_context(method_body, source_root)
                    if svc_context:
                        context += svc_context

        return {
            'line_number': start_line,
            'context': context,
            'file_scope': self._detect_scope(lines, start_line),
        }

    def _detect_scope(self, lines: List[str], line_num: int) -> str:
        """Detecta o escopo de segurança baseado no contexto"""
        window = lines[max(0, line_num - 15): line_num]
        combined = ' '.join(window).lower()
        
        if 'preauthorize' in combined or 'secured' in combined or 'rolesallowed' in combined:
            return 'authenticated'
        if 'permitall' in combined:
            return 'public'
        if 'hasrole' in combined and 'admin' in combined:
            return 'admin'
        if 'hasrole' in combined:
            return 'role_based'
        return 'unknown'

    def _walk(self, node):
        """Itera sobre todos os nós da AST"""
        yield node
        for child in node.children:
            yield from self._walk(child)

    def extract_api_endpoints(
        self,
        code: str,
        file_path: str = "unknown",
        source_root: str = None,
    ) -> List[Dict]:
        """
        Extrai endpoints de um arquivo Java (Spring Boot, Retrofit ou JAX-RS).
        """
        self._log(f"Analisando arquivo: {file_path}")
        
        root_node = self.get_root_node(code)
        endpoints = []

        # Verifica se é uma classe REST
        if not self._is_rest_class(root_node):
            self._log(f"  ⏭️ Classe não é REST, pulando...")
            return endpoints

        # Extrai informações da classe
        class_info = self._extract_class_annotations(root_node)
        class_base_path = class_info['base_path']
        class_security_annotations = class_info['security_annotations']
        
        self._log(f"Base path da classe: '{class_base_path}'")
        self._log(f"Anotações de segurança da classe: {class_security_annotations}")

        # Itera sobre métodos
        for node in self._walk(root_node):
            if node.type != 'method_declaration':
                continue

            # VERIFICA SE É PÚBLICO
            if not self._is_public_method(node):
                self._log(f"  ⏭️ Método não é público, pulando...")
                continue

            # Extrai nome do método
            method_name = 'unknown'
            for child in node.children:
                if child.type == 'identifier':
                    method_name = self._get_node_text(child)
                    break

            # Encontra modifiers (onde estão as anotações)
            modifiers_node = None
            for child in node.children:
                if child.type == 'modifiers':
                    modifiers_node = child
                    break

            if not modifiers_node:
                continue

            # Extrai anotações do método
            method_info = self._extract_method_annotations(modifiers_node)
            
            # VERIFICA SE TEM ANOTAÇÃO HTTP EXPLÍCITA OU @PATH
            has_http_ann = self._has_http_annotation(modifiers_node)
            has_path_ann = self._has_path_annotation(modifiers_node)
            
            # Se não tem anotação HTTP e não tem @Path, pode ser um método auxiliar
            if not has_http_ann and not has_path_ann:
                # Verifica se é um método auxiliar
                if self._is_auxiliary_method(method_name):
                    self._log(f"  ⏭️ Método auxiliar sem anotações: {method_name}, pulando...")
                    continue
            
            # Se não encontrou método HTTP, tenta inferir pelo nome (fallback)
            if not method_info['http_method']:
                # Só infere se tiver @Path explícito
                if has_path_ann:
                    inferred = self._infer_http_method_from_name(method_name)
                    if inferred:
                        method_info['http_method'] = inferred
                        self._log(f"  🔄 Método HTTP inferido pelo nome: {method_name} -> {inferred}")
                    else:
                        self._log(f"  ⚠️ Não foi possível inferir método HTTP para: {method_name}")
                else:
                    # Sem @Path e sem método HTTP, provavelmente não é endpoint
                    self._log(f"  ⏭️ Método sem @Path e sem HTTP: {method_name}, pulando...")
                    continue
            
            # Pula se não tiver método HTTP
            if not method_info['http_method']:
                continue

            # Pula URLs externas
            if method_info['path'] and self._is_external_url(method_info['path']):
                self._log(f"Pulando URL externa: {method_info['path']}")
                continue

            # Constrói path completo
            method_path = method_info['path'] or ''
            full_path = self._join_paths(class_base_path, method_path)
            
            # Pula paths vazios ou apenas "/"
            if full_path == '/' or full_path == '':
                self._log(f"  ⏭️ Path vazio para: {method_name}, pulando...")
                continue
            
            self._log(f"Endpoint encontrado: {method_info['http_method']} {full_path} (método: {method_name})")

            # Extrai parâmetros
            params = self._extract_method_parameters(node)
            
            # Extrai informações de segurança
            auth_required = self._extract_security_info(method_info, class_security_annotations)
            
            # Extrai metadados
            metadata = self._extract_route_metadata(code, node, source_root=source_root)

            # Cria objeto do endpoint
            endpoint = {
                'name': method_name,
                'path': full_path,
                'method': method_info['http_method'],
                'parameters': params,
                'file_path': file_path,
                'line_number': metadata['line_number'],
                'context': metadata['context'],
                'auth_required': auth_required,
                'scope': metadata['file_scope'],
                'produces': method_info.get('produces') or class_info.get('produces'),
                'consumes': method_info.get('consumes') or class_info.get('consumes'),
                'is_auxiliary': self._is_auxiliary_method(method_name),
                'has_http_annotation': has_http_ann,
                'has_path_annotation': has_path_ann,
            }
            
            endpoints.append(endpoint)

        self._log(f"Total de endpoints encontrados: {len(endpoints)}")
        return endpoints

    def get_ast_summary(self, code: str) -> Dict[str, Any]:
        """Retorna um sumário da AST para debug"""
        root_node = self.get_root_node(code)
        return {
            "type": root_node.type,
            "children_count": len(root_node.children),
            "byte_range": [root_node.start_byte, root_node.end_byte],
            "position": {
                "start": {"line": root_node.start_point[0], "column": root_node.start_point[1]},
                "end":   {"line": root_node.end_point[0], "column": root_node.end_point[1]},
            },
        }