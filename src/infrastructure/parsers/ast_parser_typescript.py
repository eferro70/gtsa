# ast_parser_node.py
import re
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from tree_sitter import Language, Parser
import tree_sitter_typescript
from dataclasses import dataclass, asdict
from datetime import datetime

# Importar a classe base
from .base_parser import BaseParser, ApiEndpoint

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


class TypeScriptParser(BaseParser):
    """Parser específico para TypeScript/JavaScript"""
    
    def __init__(self):
        super().__init__("typescript")
        self.supported_extensions = {'.ts', '.tsx', '.js', '.jsx'}
        self.ignore_suffixes = {'.d.ts', '.spec.ts', '.test.ts', '.spec.js', '.test.js'}
        
        TS_LANGUAGE = Language(tree_sitter_typescript.language_typescript())
        self.parser = Parser(TS_LANGUAGE)
        self.language = TS_LANGUAGE
        print(f"✅ Parser configurado para TypeScript/JavaScript")

    def parse_code(self, code: str):
        """Parseia o código e retorna a árvore AST"""
        return self.parser.parse(code.encode("utf8"))

    def get_root_node(self, code: str):
        """Retorna o nó raiz da AST"""
        tree = self.parser.parse(code.encode("utf8"))
        return tree.root_node

    def _get_node_text(self, node) -> str:
        """Extrai o texto de um nó"""
        return node.text.decode("utf8")

    def _is_external_url(self, path: str) -> bool:
        """Verifica se o path é uma URL externa"""
        return path.startswith(('http://', 'https://', 'ftp://', 'ws://'))

    def _extract_handler_name(self, handler_node) -> str:
        """Extrai nome do handler (melhorado)"""
        if not handler_node:
            return "anonymous"
        
        # Para função nomeada
        if handler_node.type == 'function_expression':
            name_node = next((c for c in handler_node.children if c.type == 'identifier'), None)
            if name_node:
                return self._get_node_text(name_node)
        
        # Para arrow function anônima
        if handler_node.type == 'arrow_function':
            parent = handler_node.parent
            if parent and parent.type == 'variable_declarator':
                name_node = parent.child_by_field_name('name')
                if name_node:
                    return self._get_node_text(name_node)
            return "anonymous"
        
        # Para identificador simples (ex: controller.method)
        if handler_node.type == 'identifier':
            return self._get_node_text(handler_node)
        
        # Para member_expression (ex: UserController.deleteUser)
        if handler_node.type == 'member_expression':
            obj_node = handler_node.child_by_field_name('object')
            prop_node = handler_node.child_by_field_name('property')
            
            obj_name = self._get_node_text(obj_node) if obj_node else ""
            prop_name = self._get_node_text(prop_node) if prop_node else ""
            
            if obj_name and prop_name:
                # Tenta extrair melhor o nome (ex: "contaController.createByPerfil")
                if obj_name.endswith('Controller') or obj_name.endswith('Service'):
                    return f"{obj_name}.{prop_name}"
                return prop_name
            return prop_name if prop_name else "anonymous"
        
        # Para call_expression (ex: controller.method.bind(controller))
        if handler_node.type == 'call_expression':
            func_node = handler_node.child_by_field_name('function')
            if func_node:
                return self._extract_handler_name(func_node)
        
        return "anonymous"

    def _extract_route_metadata(self, code: str, node) -> Dict[str, Any]:
        """Extrai metadados da rota (linha, contexto, etc.)"""
        start_line = node.start_point[0] + 1  # 1-indexed
        end_line = node.end_point[0] + 1
        
        # Pega algumas linhas ao redor para contexto
        lines = code.split('\n')
        context_start = max(0, start_line - 3)
        context_end = min(len(lines), end_line + 2)
        context = '\n'.join(lines[context_start:context_end])
        
        return {
            'line_number': start_line,
            'context': context,
            'file_scope': self._detect_scope(lines, start_line)
        }
    
    def _detect_scope(self, lines: List[str], line_num: int) -> str:
        """Detecta escopo da rota (auth, public, admin)"""
        # Verifica linhas anteriores para middleware de autenticação
        for i in range(max(0, line_num - 10), line_num):
            line = lines[i].lower()
            if 'authenticate' in line or 'auth' in line:
                return 'authenticated'
            if 'public' in line:
                return 'public'
        return 'unknown'

    def _extract_function_params(self, handler_node):
        """Extrai parâmetros (melhorado)"""
        params = []
        params_node = None

        if handler_node.type in ('function_expression', 'function_declaration'):
            for child in handler_node.children:
                if child.type == 'formal_parameters':
                    params_node = child
                    break
        elif handler_node.type == 'arrow_function':
            for child in handler_node.children:
                if child.type in ('identifier', 'formal_parameters'):
                    if child.type == 'identifier':
                        return [{'name': self._get_node_text(child), 'type': 'unknown'}]
                    params_node = child
                    break

        if not params_node:
            return params

        for child in params_node.children:
            if child.type == 'identifier':
                params.append({'name': self._get_node_text(child), 'type': 'unknown'})
            elif child.type in ('required_parameter', 'optional_parameter'):
                name_node = next((c for c in child.children if c.type == 'identifier'), None)
                type_node = next((c for c in child.children if c.type == 'type_annotation'), None)
                param_name = self._get_node_text(name_node) if name_node else 'unknown'
                param_type = self._get_node_text(type_node).strip(':').strip() if type_node else 'unknown'
                params.append({'name': param_name, 'type': param_type})
            elif child.type == 'rest_pattern':
                name_node = next((c for c in child.children if c.type == 'identifier'), None)
                if name_node:
                    params.append({'name': f"...{self._get_node_text(name_node)}", 'type': 'array'})
        return params

    def extract_api_endpoints(self, code: str, file_path: str = "unknown") -> List[Dict]:
        """Extrai endpoints com metadados melhorados"""
        root_node = self.get_root_node(code)
        endpoints = []

        valid_methods = {'get', 'post', 'put', 'patch', 'delete', 'head', 'options', 'route', 'use'}
        
        def find_endpoints(node):
            if node.type == 'call_expression':
                func_node = node.child_by_field_name('function')
                if func_node and func_node.type == 'member_expression':
                    obj_node = func_node.child_by_field_name('object')
                    prop_node = func_node.child_by_field_name('property')
                    
                    if obj_node and prop_node:
                        method = self._get_node_text(prop_node).lower()
                        
                        if method in valid_methods:
                            args_node = node.child_by_field_name('arguments')
                            if args_node:
                                children = [c for c in args_node.children if c.type not in ['(', ')']]
                                if len(children) >= 2:
                                    path_node = children[0]
                                    handler_node = children[1]
                                    
                                    if path_node.type == 'string':
                                        path = self._get_node_text(path_node).strip('"').strip("'").strip('`')
                                        
                                        if not self._is_external_url(path):
                                            handler_name = self._extract_handler_name(handler_node)
                                            params = self._extract_function_params(handler_node) if handler_node.type in ('function_expression', 'arrow_function', 'function_declaration') else []
                                            metadata = self._extract_route_metadata(code, node)
                                            
                                            endpoints.append({
                                                'name': handler_name,
                                                'path': path,
                                                'method': method.upper() if method not in ('route', 'use') else method.upper(),
                                                'parameters': params,
                                                'file_path': file_path,
                                                'line_number': metadata['line_number'],
                                                'context': metadata['context']
                                            })
            
            for child in node.children:
                find_endpoints(child)
        
        find_endpoints(root_node)
        return endpoints

    def get_ast_summary(self, code: str) -> Dict[str, Any]:
        """Retorna um resumo da AST para o código"""
        root_node = self.get_root_node(code)
        return {
            "type": root_node.type,
            "children_count": len(root_node.children),
            "byte_range": [root_node.start_byte, root_node.end_byte],
            "position": {
                "start": {"line": root_node.start_point[0], "column": root_node.start_point[1]},
                "end": {"line": root_node.end_point[0], "column": root_node.end_point[1]},
            }
        }