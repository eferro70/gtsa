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

    def _resolve_controller_context(self, route_context: str, source_root: str) -> Optional[str]:
        """
        Segue a referência do controller delegado na rota e retorna o código do
        método handle/execute dele. Funciona com qualquer framework que use o
        padrão controller.execute(req, res) ou controller.handle(req, res).

        Algoritmo genérico (sem dependência de convenção do projeto):
          1. Extrai o nome da variável do controller a partir da expressão de
             delegação (ex: "await xyzController.execute(req, res)").
          2. Converte camelCase → PascalCase para inferir o nome da classe/arquivo
             (ex: xyzController → XyzController → XyzController.ts).
          3. Busca o arquivo correspondente abaixo do source_root.
          4. Extrai o corpo do primeiro método handle() ou execute() encontrado.
        """
        if not source_root:
            return None

        # 1. Extrair nome da variável do controller
        # Pega a ÚLTIMA ocorrência — o contexto inclui ±45 linhas que podem
        # conter rotas anteriores; a última expressão de delegação é a da rota atual.
        matches = re.findall(
            r'await\s+([a-z][A-Za-z0-9_]*)\.(?:execute|handle)\s*\(', route_context
        )
        if not matches:
            return None
        var_name = matches[-1]  # última ocorrência = rota atual

        # 2. Converter para PascalCase para obter o nome da classe/arquivo
        #    Regra: primeiro caractere maiúsculo, resto inalterado
        class_name = var_name[0].upper() + var_name[1:]  # ex: "BuscarFluxoController"

        # 3. Buscar o arquivo no projeto (busca recursiva, ignora node_modules/dist)
        source_path = Path(source_root)
        candidates = []
        try:
            for p in source_path.rglob(f"{class_name}.ts"):
                parts = p.parts
                if any(s in parts for s in ('node_modules', 'dist', '__tests__', 'spec')):
                    continue
                # Excluir arquivos de teste
                if p.stem.endswith(('.spec', '.test')):
                    continue
                candidates.append(p)
        except Exception:
            return None

        if not candidates:
            return None

        # Preferir o arquivo mais raso (menor número de segmentos de path)
        ctrl_file = min(candidates, key=lambda p: len(p.parts))

        # 4. Extrair corpo do método handle ou execute
        try:
            ctrl_code = ctrl_file.read_text(encoding='utf-8')
        except Exception:
            return None

        # Regex genérica: captura o corpo do primeiro handle/execute async
        method_match = re.search(
            r'async\s+(?:handle|execute)\s*\([^)]*\)[^{]*\{',
            ctrl_code,
        )
        if not method_match:
            return None

        # Extrair bloco balanceado de chaves a partir do '{'
        start = method_match.end() - 1  # posição do '{'
        depth = 0
        end = start
        for i, ch in enumerate(ctrl_code[start:], start):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break

        body = ctrl_code[start:end]
        deep_chain = self._resolve_deep_chain(ctrl_code, body, source_root)
        return f"\n// --- handler: {class_name}.handle ---\n{body}{deep_chain}"

    def _extract_method_body(self, code: str, method_regex: str) -> Optional[str]:
        """Extrai o corpo de um método usando contagem de chaves."""
        m = re.search(method_regex, code)
        if not m:
            return None
        start = m.end() - 1
        depth = 0
        end = start
        for i, ch in enumerate(code[start:], start):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        return code[start:end]

    def _resolve_deep_chain(self, ctrl_code: str, handle_body: str, source_root: str) -> str:
        """
        Segue a cadeia: handle() → useCase.execute() → repository.method()
        Retorna contexto adicional com os corpos de execute() e do método do repositório.
        Limitado a 1 use case e 3 métodos de repositório para evitar excesso de contexto.
        """
        if not source_root:
            return ""
        extra = ""
        source_path = Path(source_root)

        # 1. Encontrar chamadas `await this.PROP.execute(...)` no handle body
        use_case_calls = re.findall(
            r'await\s+this\.([a-zA-Z][a-zA-Z0-9_]*)\.execute\s*\(',
            handle_body,
        )
        if not use_case_calls:
            return extra

        for prop_name in use_case_calls[:1]:  # apenas o primeiro use case
            # 2. Encontrar o tipo da propriedade na declaração da classe do controller
            type_match = re.search(
                rf'\b{re.escape(prop_name)}\s*:\s*([A-Z][A-Za-z0-9_]*)',
                ctrl_code,
            )
            if not type_match:
                continue
            uc_class = type_match.group(1)

            # 3. Localizar o arquivo do use case
            uc_candidates = []
            try:
                for p in source_path.rglob(f"{uc_class}.ts"):
                    parts = p.parts
                    if any(s in parts for s in ('node_modules', 'dist', '__tests__', 'spec')):
                        continue
                    if p.stem.endswith(('.spec', '.test')):
                        continue
                    uc_candidates.append(p)
            except Exception:
                continue
            if not uc_candidates:
                continue

            uc_file = min(uc_candidates, key=lambda p: len(p.parts))
            try:
                uc_code = uc_file.read_text(encoding='utf-8')
            except Exception:
                continue

            # 4. Extrair corpo do execute()
            execute_body = self._extract_method_body(
                uc_code,
                r'async\s+execute\s*\([^)]*\)[^{]*\{',
            )
            if not execute_body:
                continue
            extra += f"\n// --- use-case: {uc_class}.execute ---\n{execute_body}"

            # 5. Encontrar chamadas de repositório em execute():
            #    `await this.REPO.METHOD(...)` ou `await REPO.METHOD(...)`
            repo_calls = re.findall(
                r'await\s+(?:this\.[a-z][a-zA-Z0-9_]*\.)?'
                r'([a-z][a-zA-Z0-9_]*(?:listar|buscar|criar|atualizar|'
                r'deletar|list|find|create|update|delete|get)[A-Za-z0-9_]*)\s*\(',
                execute_body,
            )
            # também padrão inverso: this.rep.listar...
            repo_calls += re.findall(
                r'await\s+(?:this\.[a-z][a-zA-Z0-9_]*)\.'
                r'((?:listar|buscar|criar|atualizar|list|find|create|update|get)[A-Za-z0-9_]*)\s*\(',
                execute_body,
            )
            seen = set()
            for method_name in repo_calls:
                if method_name in seen:
                    continue
                seen.add(method_name)
                if len(seen) > 3:
                    break

                # 6. Buscar o método em arquivos de repositório
                for repo_path in source_path.rglob('*Repositori*.ts'):
                    if any(s in repo_path.parts for s in ('node_modules', 'dist', '__tests__')):
                        continue
                    try:
                        repo_code = repo_path.read_text(encoding='utf-8')
                    except Exception:
                        continue

                    repo_body = self._extract_method_body(
                        repo_code,
                        rf'async\s+{re.escape(method_name)}\s*\([^)]*\)[^{{]*\{{',
                    )
                    if not repo_body:
                        continue

                    # Limitar tamanho para não inflar contexto
                    if len(repo_body) > 3000:
                        repo_body = repo_body[:3000] + "\n// [truncado]"

                    extra += f"\n// --- repository: {repo_path.stem}.{method_name} ---\n{repo_body}"
                    break  # próximo método

        return extra

    def _extract_route_metadata(self, code: str, node, source_root: str = None) -> Dict[str, Any]:
        """Extrai metadados da rota (linha, contexto, etc.)"""
        start_line = node.start_point[0] + 1  # 1-indexed
        end_line = node.end_point[0] + 1
        
        # Pega uma janela maior para incluir blocos Swagger imediatamente acima da rota
        lines = code.split('\n')
        context_start = max(0, start_line - 45)
        context_end = min(len(lines), end_line + 4)
        context = '\n'.join(lines[context_start:context_end])

        # Tenta seguir a referência do controller para enriquecer o contexto
        handler_context = self._resolve_controller_context(context, source_root)
        if handler_context:
            context = context + handler_context

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

    def extract_api_endpoints(self, code: str, file_path: str = "unknown", source_root: str = None) -> List[Dict]:
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
                                            metadata = self._extract_route_metadata(code, node, source_root=source_root)
                                            
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